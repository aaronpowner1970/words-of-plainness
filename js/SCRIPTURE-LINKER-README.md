# Scripture Hyperlink Generator

## Overview

The Scripture Hyperlink Generator automatically converts scripture references in your page content into clickable links pointing to [churchofjesuschrist.org](https://www.churchofjesuschrist.org/study/scriptures).

**Example:** The text "John 3:16" becomes a clickable link that opens the verse on the Church's scripture website.

## Supported Formats

| Format | Example | Result |
|--------|---------|--------|
| Single verse | `John 3:16` | Links to John 3:16 |
| Verse range | `Matthew 5:3-12` | Highlights verses 3-12 |
| Numbered books | `2 Nephi 25:26` | Links to 2 Nephi 25:26 |
| Abbreviations | `D&C 93:1` | Links to D&C 93:1 |
| | `1 Ne 3:7` | Links to 1 Nephi 3:7 |

## Supported Scripture Books

### Bible (Old & New Testament)
- All 66 books with common abbreviations
- Examples: Genesis/Gen, Matthew/Matt, Revelation/Rev

### Book of Mormon
- All books: 1 Nephi through Moroni
- Abbreviations: 1 Ne, 2 Ne, Hel, Morm, Moro, etc.

### Doctrine and Covenants
- `Doctrine and Covenants`, `D&C`, or `DC`

### Pearl of Great Price
- Moses, Abraham (Abr)
- Joseph Smith—Matthew (JS-M), Joseph Smith—History (JS-H)
- Articles of Faith (A of F)

## Installation

The scripture linker is already included on all Words of Plainness pages.

### Files
- `/js/scripture-linker.js` — Main script
- `/css/styles.css` — Contains `.scripture-link` styles

### Script Inclusion
```html
<script src="js/scripture-linker.js"></script>
```

## Usage

### Automatic Initialization
By default, the script automatically initializes when the DOM is ready and processes the entire `<body>`.

### Manual/Scoped Initialization
To process only specific content (recommended for chapter pages):

```html
<script>
    window.SCRIPTURE_LINKER_MANUAL = true; // Disable auto-init
</script>
<script src="js/scripture-linker.js"></script>
<script>
    ScriptureLinker.init('.chapter-content'); // Process only chapter content
</script>
```

### Processing Dynamic Content
If you add content dynamically after page load:

```javascript
const newElement = document.getElementById('new-content');
ScriptureLinker.process(newElement);
```

### Getting a URL Programmatically
```javascript
const url = ScriptureLinker.getUrl('John 3:16');
// Returns: https://www.churchofjesuschrist.org/study/scriptures/nt/john/3?lang=eng&id=p16#p16
```

## Coexistence with Audio Sync

The scripture linker is designed to work alongside the guided reading (audio sync) feature:

1. **Click Behavior:** Scripture links use `stopPropagation()` to prevent triggering the sentence click-to-seek handler
2. **Visual Styling:** Links adjust appearance when inside an active (highlighted) sentence
3. **Order of Operations:** Scripture linker processes content AFTER the audio system initializes

**Result:** Clicking a scripture reference opens the scripture; clicking elsewhere in the sentence seeks the audio.

## Styling

Scripture links use the `.scripture-link` class:

```css
.scripture-link {
    color: var(--gold-primary);
    text-decoration: none;
    border-bottom: 1px dotted var(--gold-primary);
}

.scripture-link:hover {
    border-bottom-style: solid;
}

/* Inside highlighted sentences */
.sentence.active .scripture-link {
    color: var(--cream);
}
```

## Generated URL Format

```
https://www.churchofjesuschrist.org/study/scriptures/{book_path}/{chapter}?lang=eng&id=p{verse}#p{verse}
```

For verse ranges:
```
...?lang=eng&id=p{start}-p{end}#p{start}
```

## Troubleshooting

### Links not appearing
- Ensure scripture-linker.js is loaded after the content
- Check browser console for errors
- Verify scripture format matches expected patterns

### Links inside `<code>` or `<pre>` tags
- The linker intentionally skips these elements to preserve code examples

### Custom book not recognized
- Add to `BOOK_MAP` in scripture-linker.js
- Use format: `'book name': 'url/path'`

## Browser Support

Works in all modern browsers (Chrome, Firefox, Safari, Edge).

## Credits

Developed for the Words of Plainness ministry.
