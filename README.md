# Words of Plainness - Ministry Website

**A Christ-Centered Ministry**  
*Where Seekers and Saints Find Common Ground*

## Overview

This is the static website for Words of Plainness, Brother Aaron Powner's Christ-centered ministry. The site is designed to welcome both spiritual seekers and existing disciples of various Christian traditions.

## Project Structure

```
words-of-plainness/
├── index.html              # Landing page with hero video section
├── css/
│   └── styles.css          # Main stylesheet with responsive design
├── js/
│   └── main.js             # Navigation, scroll effects, interactivity
├── pages/
│   ├── new-here.html       # Welcome page for new visitors
│   ├── about.html          # About Brother Aaron, philosophy, FAQ, glossary
│   ├── writings.html       # Searchable writings database (placeholder)
│   ├── discipleship.html   # Web apps and scripture tools
│   ├── connect.html        # Contact, newsletter, chat, prayer requests
│   └── channels.html       # YouTube, VR Chat, Music, RV Ministry
├── assets/
│   ├── images/
│   │   ├── library.png         # Hero background (Brother Aaron reading)
│   │   └── library-empty.png   # Interior pages background (empty room)
│   └── video/
│       ├── welcome.webm        # Primary video (VP9, 621KB)
│       └── welcome.mp4         # Fallback video (H.264, 6.3MB)
├── vercel.json             # Deployment configuration
└── README.md               # This file
```

## Features

- **Responsive Design**: Optimized for desktop, tablet, and mobile
- **Warm Library Aesthetic**: Consistent color palette extracted from the library image
- **Accessible**: Skip links, focus states, reduced motion support
- **Mobile-First Navigation**: Hamburger menu with full-screen overlay
- **Video-Ready**: Hero section supports 5-second welcome video (desktop only)

## Color Palette

```css
--gold-primary: #C4943A;    /* Lantern glow, accents */
--cream: #E8DCC4;           /* Primary text */
--brown-deep: #3D2B1F;      /* Backgrounds */
--brown-rich: #2A1D14;      /* Darker sections */
--burgundy: #6B3D3D;        /* Accent */
--teal-muted: #4A6B6B;      /* Accent */
```

## Typography

- **Headlines**: Crimson Pro (serif)
- **Body Text**: Source Sans Pro (sans-serif)

Both fonts are loaded from Google Fonts.

## Local Development

1. Clone or download this folder
2. Open `index.html` in a web browser
3. For live reload during development, use a local server:

```bash
# Python 3
python -m http.server 8000

# Node.js (if you have npx)
npx serve

# VS Code: Use the "Live Server" extension
```

## Deployment to Vercel

### Option 1: Drag and Drop
1. Go to [vercel.com](https://vercel.com)
2. Sign in with GitHub, GitLab, or email
3. Click "Add New Project"
4. Choose "Import Third-Party Git Repository" or drag the folder to upload

### Option 2: Vercel CLI
```bash
# Install Vercel CLI
npm install -g vercel

# Navigate to project folder
cd words-of-plainness

# Deploy
vercel

# Follow prompts to link to your account
```

### Option 3: GitHub Integration
1. Push this folder to a GitHub repository
2. Connect Vercel to your GitHub account
3. Import the repository
4. Vercel will auto-deploy on every push

## Video Configuration

Both video formats are included and configured:

- **WebM** (621KB): `assets/video/welcome.webm` — Primary, used by modern browsers
- **MP4** (6.3MB): `assets/video/welcome.mp4` — Fallback for older browsers

**Behavior:**
- Desktop: Video autoplays (muted) when page loads
- Mobile: Static image shown instead (saves bandwidth)
- Fallback: Shows `library.png` if video fails to load

Modern browsers (Chrome, Firefox, Edge, Safari 14.1+) will automatically choose the WebM version, loading only 621KB instead of 6.3MB—a 90% bandwidth savings for most visitors.

## Future Development: Django Integration

This static site is designed to be easily converted to Django templates:

1. **Templates**: Each HTML file can become a Django template
2. **Static Files**: CSS, JS, and images move to Django's static folder
3. **Database**: The writings search and user accounts will need Django models
4. **Forms**: Newsletter and contact forms need Django views/handlers

### Recommended Django Structure
```
words_of_plainness/
├── manage.py
├── config/
│   └── settings.py
├── core/
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   └── pages/
│   └── static/
│       ├── css/
│       ├── js/
│       └── images/
├── writings/
│   ├── models.py
│   └── views.py
├── discipleship/
│   └── (apps)
└── users/
    └── (authentication)
```

## Browser Support

- Chrome (last 2 versions)
- Firefox (last 2 versions)
- Safari (last 2 versions)
- Edge (last 2 versions)
- iOS Safari
- Chrome for Android

## Accessibility

- Semantic HTML structure
- Skip link for keyboard navigation
- Focus-visible states for all interactive elements
- Respects `prefers-reduced-motion`
- Color contrast meets WCAG AA standards

## License

Content © 2026 Brother Aaron Powner / Words of Plainness Ministry

---

*"For my soul delighteth in plainness; for after this manner doth the Lord God work among the children of men."* — 2 Nephi 31:3
