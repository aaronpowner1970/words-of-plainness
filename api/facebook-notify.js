/**
 * Words of Plainness — Facebook New Post Notifier
 *
 * Vercel Serverless Function
 * Fetches the Atom RSS feed, finds the newest post,
 * and publishes it to the ministry Facebook Page via Graph API.
 *
 * Trigger: POST /api/facebook-notify
 * Auth: Bearer token matching NOTIFY_SECRET env var
 *
 * Environment variables required:
 *   NOTIFY_SECRET — shared secret for endpoint authentication
 *   FACEBOOK_PAGE_ID — Facebook Page ID
 *   FACEBOOK_PAGE_TOKEN — permanent Page Access Token
 */

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

  const pageId = process.env.FACEBOOK_PAGE_ID;
  const pageToken = process.env.FACEBOOK_PAGE_TOKEN;
  if (!pageId || !pageToken) {
    return res.status(500).json({ error: 'FACEBOOK_PAGE_ID or FACEBOOK_PAGE_TOKEN not configured' });
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

    // Determine post type and compose message
    const isThought = entry.summary && entry.summary.length < 280;

    let message;
    let fbBody;

    if (isThought) {
      // Short post — share full text
      message = `${entry.summary}\n\n— Brother Aaron\nwordsofplainness.org`;
      fbBody = {
        message,
        access_token: pageToken
      };
    } else {
      // Article — excerpt + link
      const excerpt = entry.summary
        ? entry.summary.substring(0, 200) + '...'
        : 'A new post has been published.';
      message = `${entry.title}\n\n${excerpt}\n\nRead more at Words of Plainness`;
      fbBody = {
        message,
        link: entry.url,
        access_token: pageToken
      };
    }

    // Post to Facebook Graph API
    const fbUrl = `https://graph.facebook.com/v19.0/${pageId}/feed`;
    const fbResponse = await fetch(fbUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(fbBody)
    });

    if (!fbResponse.ok) {
      const errText = await fbResponse.text();
      return res.status(502).json({
        error: 'Facebook API request failed',
        status: fbResponse.status,
        detail: errText
      });
    }

    const fbResult = await fbResponse.json();

    return res.status(200).json({
      success: true,
      post: entry.title,
      url: entry.url,
      facebookPostId: fbResult.id,
      message: 'Published to Facebook Page'
    });

  } catch (err) {
    return res.status(500).json({ error: 'Internal error', detail: err.message });
  }
};

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
