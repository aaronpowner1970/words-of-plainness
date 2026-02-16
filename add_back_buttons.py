import re

path = r'C:\Users\aaron\Documents\words-of-plainness\src\chapters\06-embrace-the-savior.njk'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')
output = []
current_path = None
current_movement = None
in_reflection = False

for line in lines:
    m = re.search(r'class="movement-section".*?data-path="(\w+)".*?data-movement="(\d+)"', line)
    if m:
        current_path = m.group(1)
        current_movement = int(m.group(2))
        in_reflection = False
    m2 = re.search(r'class="reflection-section".*?data-path="(\w+)"', line)
    if m2:
        current_path = m2.group(1)
        in_reflection = True
        current_movement = None

    output.append(line)

    if '<div class="movement-nav">' in line:
        if not in_reflection and current_movement and current_movement >= 2:
            prev = current_movement - 1
            output.append('            <button class="btn-back" onclick="goBackOnPath()">&larr; Back to Movement {}</button>'.format(prev))
        if in_reflection:
            output.append('            <button class="btn-back" onclick="goBackOnPath()">&larr; Back to Movement 5</button>')

result = '\n'.join(output)
with open(path, 'w', encoding='utf-8') as f:
    f.write(result)

count = result.count('btn-back')
print('Done. btn-back occurrences: {} (15 buttons + 2 CSS rules = 17)'.format(count))
