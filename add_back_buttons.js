const fs = require('fs');

const path = 'C:\\Users\\aaron\\Documents\\words-of-plainness\\src\\chapters\\06-embrace-the-savior.njk';
const content = fs.readFileSync(path, 'utf8');
const lines = content.split('\n');
const output = [];

let currentPath = null;
let currentMovement = null;
let inReflection = false;

for (const line of lines) {
  const movMatch = line.match(/class="movement-section".*?data-path="(\w+)".*?data-movement="(\d+)"/);
  if (movMatch) {
    currentPath = movMatch[1];
    currentMovement = parseInt(movMatch[2]);
    inReflection = false;
  }
  const refMatch = line.match(/class="reflection-section".*?data-path="(\w+)"/);
  if (refMatch) {
    currentPath = refMatch[1];
    inReflection = true;
    currentMovement = null;
  }

  output.push(line);

  if (line.includes('<div class="movement-nav">')) {
    if (!inReflection && currentMovement && currentMovement >= 2) {
      const prev = currentMovement - 1;
      output.push(`            <button class="btn-back" onclick="goBackOnPath()">&larr; Back to Movement ${prev}</button>`);
    }
    if (inReflection) {
      output.push('            <button class="btn-back" onclick="goBackOnPath()">&larr; Back to Movement 5</button>');
    }
  }
}

const result = output.join('\n');
fs.writeFileSync(path, result, 'utf8');

const count = (result.match(/btn-back/g) || []).length;
console.log(`Done. btn-back occurrences: ${count} (15 buttons + 2 CSS rules = 17)`);
