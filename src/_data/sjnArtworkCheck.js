/**
 * Runs the Seeking Jesus of Nazareth artwork guard on every Eleventy build,
 * including `npx @11ty/eleventy` and `eleventy --serve`, which skip npm's prebuild.
 * Throwing here stops the build. Rules: scripts/sjn-verify-artwork.js.
 */
const { verifyArtwork } = require("../../scripts/sjn-verify-artwork.js");

module.exports = function () {
  const { problems, approved } = verifyArtwork();
  if (problems.length) {
    throw new Error(`[sjn-verify-artwork] ${problems.length} problem(s):\n  - ${problems.join("\n  - ")}`);
  }
  return { approved };
};
