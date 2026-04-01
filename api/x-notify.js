/**
 * Words of Plainness — X/Twitter New Post Notifier
 *
 * Vercel Serverless Function
 * Fetches the Atom RSS feed, finds the newest post,
 * and posts a tweet via X API v2 with OAuth 1.0a signing.
 *
 * Trigger: POST /api/x-notify
 * Auth: Bearer token matching NOTIFY_SECRET env var
 *
 * Environment variables required:
 *   NOTIFY_SECRET — shared secret for endpoint authentication
 *   X_API_KEY — OAuth consumer key
 *   X_API_SECRET — OAuth consumer secret
 *   X_ACCESS_TOKEN — OAuth access token
 *   X_ACCESS_SECRET — OAuth access token secret
 */

const crypto = require('crypto');

module.exports = async (req, res) => {
  // Only accept POST
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // Verify auth token
  const authHeader = req.headers.authorization || '';
  const token = authHeader.replace('Bearer ', '');
  if (!token || token !== process.env.NOTIFY_SECRET) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  const apiKey = process.env.X_API_KEY;
  const apiSecret = process.env.X_API_SECRET;
  const accessToken = process.env.X_ACCESS_TOKEN;
  const accessSecret = process.env.X_ACCESS_SECRET;
  if (!apiKey || !apiSecret || !accessToken || !accessSecret) {
    return res.status(500).json({ error: 'X API credentials not configured' });
  }

  try {
    // Fetch the live RSS feed
    const feedUrl = 'https://www.wordsofplainness.org/posts/feed.xml';
    const feedResponse = await fetch(feedUrl);
    if (!feedResponse.ok) {
      return res.status(502).json({ error: 'Failed to fetch RSS feed', status: feedResponse.status });
    }
    const feedXml = await feedResponse.text();

    // Parse the newest entry from Atom feed
    const entry = parseNewestEntry(feedXml);
    if (!entry) {
      return res.status(404).json({ error: 'No entries found in feed' });
    }

    // Compose tweet text based on post type
    const tweetText = composeTweet(entry);

    // Post tweet via X API v2
    const tweetUrl = 'https://api.x.com/2/tweets';
    const oauthHeader = buildOAuthHeader(
      'POST', tweetUrl, apiKey, apiSecret, accessToken, accessSecret
    );

    const xResponse = await fetch(tweetUrl, {
      method: 'POST',
      headers: {
        'Authorization': oauthHeader,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ text: tweetText })
    });

    if (!xResponse.ok) {
      const errText = await xResponse.text();
      return res.status(502).json({
        error: 'X API request failed',
        status: xResponse.status,
        detail: errText
      });
    }

    const xResult = await xResponse.json();

    return res.status(200).json({
      success: true,
      post: entry.title,
      url: entry.url,
      tweetId: xResult.data?.id,
      message: 'Published to X/Twitter'
    });

  } catch (err) {
    return res.status(500).json({ error: 'Internal error', detail: err.message });
  }
};

/**
 * Compose tweet text from an RSS entry.
 * - Thought type (summary < 200 chars): full summary + signature
 * - Article type: title + excerpt + URL
 * Total must stay under 280 chars.
 */
function composeTweet(entry) {
  const signature = '\n\n\u2014 Brother Aaron';

  if (entry.summary && entry.summary.length < 200) {
    // Thought type — post full summary with signature
    const tweet = entry.summary + signature;
    if (tweet.length <= 280) return tweet;
  }

  // Article type — title + excerpt + URL
  const url = entry.url || '';
  const prefix = entry.title + '\n\n';
  const suffix = '\n\n' + url;
  const availableForSummary = 280 - prefix.length - suffix.length - 3; // 3 for "..."

  if (availableForSummary > 0 && entry.summary) {
    const maxLen = Math.min(180, availableForSummary);
    const excerpt = entry.summary.substring(0, maxLen) + '...';
    return prefix + excerpt + suffix;
  }

  // Fallback: just title + URL
  return entry.title + '\n\n' + url;
}

/**
 * Build OAuth 1.0a Authorization header for X API v2.
 */
function buildOAuthHeader(method, url, consumerKey, consumerSecret, tokenKey, tokenSecret) {
  const oauthParams = {
    oauth_consumer_key: consumerKey,
    oauth_nonce: crypto.randomBytes(16).toString('hex'),
    oauth_signature_method: 'HMAC-SHA1',
    oauth_timestamp: Math.floor(Date.now() / 1000).toString(),
    oauth_token: tokenKey,
    oauth_version: '1.0'
  };

  // Build signature base string
  const paramString = Object.keys(oauthParams)
    .sort()
    .map(k => percentEncode(k) + '=' + percentEncode(oauthParams[k]))
    .join('&');

  const signatureBaseString = [
    method.toUpperCase(),
    percentEncode(url),
    percentEncode(paramString)
  ].join('&');

  // Create signing key and sign
  const signingKey = percentEncode(consumerSecret) + '&' + percentEncode(tokenSecret);
  const signature = crypto
    .createHmac('sha1', signingKey)
    .update(signatureBaseString)
    .digest('base64');

  oauthParams.oauth_signature = signature;

  // Build Authorization header
  const headerString = Object.keys(oauthParams)
    .sort()
    .map(k => percentEncode(k) + '="' + percentEncode(oauthParams[k]) + '"')
    .join(', ');

  return 'OAuth ' + headerString;
}

/**
 * Percent-encode a string per RFC 3986.
 */
function percentEncode(str) {
  return encodeURIComponent(str)
    .replace(/!/g, '%21')
    .replace(/\*/g, '%2A')
    .replace(/'/g, '%27')
    .replace(/\(/g, '%28')
    .replace(/\)/g, '%29');
}

/**
 * Decode common HTML/XML entities in RSS content.
 */
function decodeEntities(str) {
  if (!str) return str;
  return str
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&#39;/g, "'")
    .replace(/&#x27;/g, "'")
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'");
}

/**
 * Parse the newest <entry> from an Atom feed XML string.
 * Uses simple string parsing — no external dependencies.
 */
function parseNewestEntry(xml) {
  const entryMatch = xml.match(/<entry>([\s\S]*?)<\/entry>/);
  if (!entryMatch) return null;

  const entry = entryMatch[1];

  const title = extractTag(entry, 'title');
  const summary = extractTag(entry, 'summary');
  const published = extractTag(entry, 'published');
  const author = extractNestedTag(entry, 'author', 'name');

  // Extract link href
  const linkMatch = entry.match(/<link\s+href="([^"]+)"/);
  const url = linkMatch ? linkMatch[1] : null;

  return {
    title: decodeEntities(title),
    url,
    summary: decodeEntities(summary),
    published,
    author: decodeEntities(author)
  };
}

function extractTag(xml, tag) {
  const match = xml.match(new RegExp(`<${tag}>([\\s\\S]*?)<\\/${tag}>`));
  return match ? match[1].trim() : null;
}

function extractNestedTag(xml, parent, child) {
  const parentMatch = xml.match(new RegExp(`<${parent}>([\\s\\S]*?)<\\/${parent}>`));
  if (!parentMatch) return null;
  return extractTag(parentMatch[1], child);
}
