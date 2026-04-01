/**
 * Words of Plainness — Discord New Post Notifier
 *
 * Vercel Serverless Function
 * Fetches the Atom RSS feed, finds the newest post,
 * and creates a forum thread in #blog-discussions via Discord webhook.
 *
 * Trigger: POST /api/discord-notify
 * Auth: Bearer token matching NOTIFY_SECRET env var
 *
 * Environment variables required:
 *   DISCORD_WEBHOOK_URL — Discord webhook URL for #blog-discussions forum
 *   NOTIFY_SECRET — shared secret for endpoint authentication
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

  const webhookUrl = process.env.DISCORD_WEBHOOK_URL;
  if (!webhookUrl) {
    return res.status(500).json({ error: 'DISCORD_WEBHOOK_URL not configured' });
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

    // Build Discord webhook payload for forum thread creation
    const embed = {
      title: entry.title,
      url: entry.url,
      description: entry.summary || 'A new post has been published on Words of Plainness.',
      color: 0xC4943A,  // WoP gold
      author: {
        name: entry.author || 'Brother Aaron'
      },
      footer: {
        text: 'Words of Plainness'
      },
      timestamp: entry.published || new Date().toISOString()
    };

    const discordPayload = {
      thread_name: entry.title,
      username: 'Words of Plainness',
      embeds: [embed],
      content: `**New Post Published** — Read the full post and share your thoughts:\n${entry.url}`
    };

    // Send to Discord webhook
    const discordResponse = await fetch(webhookUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(discordPayload)
    });

    if (!discordResponse.ok) {
      const errText = await discordResponse.text();
      return res.status(502).json({
        error: 'Discord webhook failed',
        status: discordResponse.status,
        detail: errText
      });
    }

    return res.status(200).json({
      success: true,
      post: entry.title,
      url: entry.url,
      message: 'Discord forum thread created'
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
