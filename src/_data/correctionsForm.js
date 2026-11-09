/* Build-time settings for the hidden /corrections/ page (CODE-AOID2-110).
   Reads two environment variables by name and nothing else. The Turnstile site key is public by design
   (it is printed in the page for Cloudflare's widget); no secret and no address is read here.
   The server (api/corrections.js) decides every submission at run time, whatever this file says. */
module.exports = {
  siteKey: process.env.TURNSTILE_SITE_KEY || '',
  enabled: process.env.CORRECTIONS_ENABLED === 'true',
};
