/**
 * Words of Plainness — Post-Deploy Auto-Notification
 *
 * Vercel Serverless Function
 * Called by GitHub Action after each successful deployment that includes
 * a new post in src/posts/. Fetches the Atom feed, compares the newest
 * entry against a stored "last notified" marker in the Django backend,
 * and fires the distribution pipeline only if there is a genuinely new post.
 *
 * Trigger: POST /api/post-deploy-notify
 * Auth: Bearer token matching NOTIFY_SECRET env var
 *
 * Environment variables required:
 *   NOTIFY_SECRET — shared secret for endpoint authentication
 *   DJANGO_API_URL — base URL for Django API (e.g. https://apowner.pythonanywhere.com)
 *   DISCORD_WEBHOOK_URL — Discord webhook URL for #blog-discussions forum
 *   X_API_KEY — OAuth consumer key
 *   X_API_SECRET — OAuth consumer secret
 *   X_ACCESS_TOKEN — OAuth access token
 *   X_ACCESS_SECRET — OAuth access token secret
 *   FACEBOOK_PAGE_ID — Facebook Page ID
 *   FACEBOOK_PAGE_TOKEN — permanent Page Access Token
 */

const crypto = require('crypto');

module.exports = async (req, res) => {
  // Accept both POST (GitHub Action) and GET (manual browser test)
  if (req.method !== 'POST' && req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // Verify auth token (header or query param)
  const authHeader = req.headers.authorization || '';
  const token = authHeader.replace('Bearer ', '');
  const queryToken = req.query?.token;
  const authToken = token || queryToken;

  if (!authToken || authToken !== process.env.NOTIFY_SECRET) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  const djangoBase = process.env.DJANGO_API_URL || 'https://apowner.pythonanywhere.com';

  try {
    // ── Step 1: Fetch the live Atom feed ──────────────────────────────────
    const feedUrl = 'https://www.wordsofplainness.org/posts/feed.xml';
    const feedResponse = await fetch(feedUrl);
    if (!feedResponse.ok) {
      return res.status(502).json({ error: 'Failed to fetch RSS feed', status: feedResponse.status });
    }
    const feedXml = await feedResponse.text();

    const entry = parseNewestEntry(feedXml);
    if (!entry) {
      return res.status(200).json({ action: 'none', reason: 'No entries found in feed' });
    }

    // ── Step 2: Check the last-notified marker ────────────────────────────
    let lastNotifiedUrl = null;
    try {
      const markerResponse = await fetch(`${djangoBase}/api/v1/progress/last-notified/`);
      if (markerResponse.ok) {
        const markerData = await markerResponse.json();
        lastNotifiedUrl = markerData.post_url || null;
      }
    } catch (markerErr) {
      // If Django is unreachable, skip to avoid duplicates
      console.error('Failed to reach last-notified endpoint:', markerErr.message);
      return res.status(200).json({
        action: 'skipped',
        reason: 'Could not reach Django last-notified endpoint — skipping to avoid duplicates',
        error: markerErr.message
      });
    }

    // ── Step 3: Compare ───────────────────────────────────────────────────
    if (entry.url === lastNotifiedUrl) {
      return res.status(200).json({
        action: 'none',
        reason: 'Newest post already notified',
        post: entry.title,
        url: entry.url
      });
    }

    // ── Step 4: New post detected — fire notifications ────────────────────
    const [discordResult, xResult, facebookResult] = await Promise.allSettled([
      sendDiscord(entry),
      sendX(entry),
      sendFacebook(entry)
    ]);

    const results = {
      discord: unwrapResult(discordResult),
      x: unwrapResult(xResult),
      facebook: unwrapResult(facebookResult)
    };

    // ── Step 5: Update the last-notified marker ───────────────────────────
    try {
      await fetch(`${djangoBase}/api/v1/progress/last-notified/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${process.env.NOTIFY_SECRET}`
        },
        body: JSON.stringify({
          post_url: entry.url,
          post_title: entry.title
        })
      });
    } catch (updateErr) {
      console.error('Failed to update last-notified marker:', updateErr.message);
    }

    return res.status(200).json({
      action: 'notified',
      post: entry.title,
      url: entry.url,
      results
    });

  } catch (err) {
    return res.status(500).json({ error: 'Internal error', detail: err.message });
  }
};

// ─── Result unwrapper ─────────────────────────────────────────────────────────

function unwrapResult(settled) {
  if (settled.status === 'fulfilled') return settled.value;
  return { status: 'error', detail: settled.reason?.message || String(settled.reason) };
}

// ─── Discord ──────────────────────────────────────────────────────────────────

async function sendDiscord(entry) {
  const webhookUrl = process.env.DISCORD_WEBHOOK_URL;
  if (!webhookUrl) {
    return { status: 'skipped', detail: 'DISCORD_WEBHOOK_URL not configured' };
  }

  const embed = {
    title: entry.title,
    url: entry.url,
    description: entry.summary || 'A new post has been published on Words of Plainness.',
    color: 0xC4943A,
    author: { name: entry.author || 'Brother Aaron' },
    footer: { text: 'Words of Plainness' },
    timestamp: entry.published || new Date().toISOString()
  };

  const discordPayload = {
    thread_name: entry.title,
    username: 'Words of Plainness',
    embeds: [embed],
    content: `**New Post Published** — Read the full post and share your thoughts:\n${entry.url}`
  };

  const response = await fetch(webhookUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(discordPayload)
  });

  if (!response.ok) {
    const errText = await response.text();
    return { status: 'error', detail: `Discord ${response.status}: ${errText}` };
  }

  return { status: 'sent', detail: 'Forum thread created' };
}

// ─── X/Twitter ────────────────────────────────────────────────────────────────

async function sendX(entry) {
  const apiKey = process.env.X_API_KEY;
  const apiSecret = process.env.X_API_SECRET;
  const accessToken = process.env.X_ACCESS_TOKEN;
  const accessSecret = process.env.X_ACCESS_SECRET;
  if (!apiKey || !apiSecret || !accessToken || !accessSecret) {
    return { status: 'skipped', detail: 'X API credentials not configured' };
  }

  const tweetText = composeTweet(entry);
  const tweetUrl = 'https://api.twitter.com/2/tweets';
  const oauthHeader = buildOAuthHeader(
    'POST', tweetUrl, apiKey, apiSecret, accessToken, accessSecret
  );

  const response = await fetch(tweetUrl, {
    method: 'POST',
    headers: {
      'Authorization': oauthHeader,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ text: tweetText })
  });

  if (!response.ok) {
    const errText = await response.text();
    return { status: 'error', detail: `X API ${response.status}: ${errText}` };
  }

  const result = await response.json();
  return { status: 'sent', detail: `Tweet ID: ${result.data?.id}` };
}

function composeTweet(entry) {
  const signature = '\n\n\u2014 Brother Aaron';

  if (entry.summary && entry.summary.length < 200) {
    const tweet = entry.summary + signature;
    if (tweet.length <= 280) return tweet;
  }

  const url = entry.url || '';
  const prefix = entry.title + '\n\n';
  const suffix = '\n\n' + url;
  const availableForSummary = 280 - prefix.length - suffix.length - 3;

  if (availableForSummary > 0 && entry.summary) {
    const maxLen = Math.min(180, availableForSummary);
    const excerpt = entry.summary.substring(0, maxLen) + '...';
    return prefix + excerpt + suffix;
  }

  return entry.title + '\n\n' + url;
}

function buildOAuthHeader(method, url, consumerKey, consumerSecret, tokenKey, tokenSecret) {
  const oauthParams = {
    oauth_consumer_key: consumerKey,
    oauth_nonce: crypto.randomBytes(16).toString('hex'),
    oauth_signature_method: 'HMAC-SHA1',
    oauth_timestamp: Math.floor(Date.now() / 1000).toString(),
    oauth_token: tokenKey,
    oauth_version: '1.0'
  };

  const paramString = Object.keys(oauthParams)
    .sort()
    .map(k => percentEncode(k) + '=' + percentEncode(oauthParams[k]))
    .join('&');

  const signatureBaseString = [
    method.toUpperCase(),
    percentEncode(url),
    percentEncode(paramString)
  ].join('&');

  const signingKey = percentEncode(consumerSecret) + '&' + percentEncode(tokenSecret);
  const signature = crypto
    .createHmac('sha1', signingKey)
    .update(signatureBaseString)
    .digest('base64');

  oauthParams.oauth_signature = signature;

  const headerString = Object.keys(oauthParams)
    .sort()
    .map(k => percentEncode(k) + '="' + percentEncode(oauthParams[k]) + '"')
    .join(', ');

  return 'OAuth ' + headerString;
}

function percentEncode(str) {
  return encodeURIComponent(str)
    .replace(/!/g, '%21')
    .replace(/\*/g, '%2A')
    .replace(/'/g, '%27')
    .replace(/\(/g, '%28')
    .replace(/\)/g, '%29');
}

// ─── Facebook ─────────────────────────────────────────────────────────────────

async function sendFacebook(entry) {
  const pageId = process.env.FACEBOOK_PAGE_ID;
  const pageToken = process.env.FACEBOOK_PAGE_TOKEN;
  if (!pageId || !pageToken) {
    return { status: 'skipped', detail: 'FACEBOOK_PAGE_ID or FACEBOOK_PAGE_TOKEN not configured' };
  }

  const isThought = entry.summary && entry.summary.length < 280;

  let message;
  let fbBody;

  if (isThought) {
    message = `${entry.summary}\n\n— Brother Aaron\nwordsofplainness.org`;
    fbBody = { message, access_token: pageToken };
  } else {
    const excerpt = entry.summary
      ? entry.summary.substring(0, 200) + '...'
      : 'A new post has been published.';
    message = `${entry.title}\n\n${excerpt}\n\nRead more at Words of Plainness`;
    fbBody = { message, link: entry.url, access_token: pageToken };
  }

  const fbUrl = `https://graph.facebook.com/v19.0/${pageId}/feed`;
  const response = await fetch(fbUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(fbBody)
  });

  if (!response.ok) {
    const errText = await response.text();
    return { status: 'error', detail: `Facebook ${response.status}: ${errText}` };
  }

  const result = await response.json();
  return { status: 'sent', detail: `Post ID: ${result.id}` };
}

// ─── Shared RSS helpers ───────────────────────────────────────────────────────

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

function parseNewestEntry(xml) {
  const entryMatch = xml.match(/<entry>([\s\S]*?)<\/entry>/);
  if (!entryMatch) return null;

  const entry = entryMatch[1];

  const title = extractTag(entry, 'title');
  const summary = extractTag(entry, 'summary');
  const published = extractTag(entry, 'published');
  const author = extractNestedTag(entry, 'author', 'name');

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
