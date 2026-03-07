const fs = require('fs');
const path = require('path');

module.exports = function () {
  const dir = path.join(__dirname, 'concerts');
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir)
    .filter(function (f) { return f.endsWith('.json'); })
    .map(function (f) {
      return JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8'));
    });
};
