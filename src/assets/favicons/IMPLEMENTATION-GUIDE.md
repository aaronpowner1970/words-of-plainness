# Lantern Icon Implementation Guide

## Words of Plainness Favicon & Icon Assets

### File Inventory

| File | Size | Purpose |
|------|------|---------|
| `favicon.ico` | 16/32/48px | Browser tabs (legacy support) |
| `favicon-16x16.png` | 16×16 | Small browser tabs |
| `favicon-32x32.png` | 32×32 | Standard browser tabs |
| `favicon-48x48.png` | 48×48 | High-DPI browser tabs |
| `apple-touch-icon.png` | 180×180 | iOS home screen |
| `android-chrome-192x192.png` | 192×192 | Android home screen |
| `android-chrome-512x512.png` | 512×512 | Android splash screen |
| `lantern-icon-64.png` | 64×64 | Footer, small UI elements |
| `lantern-icon-128.png` | 128×128 | Section headers, modals |
| `lantern-icon-256.png` | 256×256 | Hero sections, large displays |
| `site.webmanifest` | — | PWA configuration |

---

## Installation

### Step 1: Copy Files to Your Repository

```
assets/
└── favicons/
    ├── favicon.ico
    ├── favicon-16x16.png
    ├── favicon-32x32.png
    ├── favicon-48x48.png
    ├── apple-touch-icon.png
    ├── android-chrome-192x192.png
    ├── android-chrome-512x512.png
    ├── lantern-icon-64.png
    ├── lantern-icon-128.png
    ├── lantern-icon-256.png
    └── site.webmanifest
```

### Step 2: Add to HTML `<head>`

Add these lines to every page's `<head>` section:

```html
<!-- Favicons -->
<link rel="icon" type="image/x-icon" href="/assets/favicons/favicon.ico">
<link rel="icon" type="image/png" sizes="16x16" href="/assets/favicons/favicon-16x16.png">
<link rel="icon" type="image/png" sizes="32x32" href="/assets/favicons/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="48x48" href="/assets/favicons/favicon-48x48.png">
<link rel="apple-touch-icon" sizes="180x180" href="/assets/favicons/apple-touch-icon.png">
<link rel="manifest" href="/assets/favicons/site.webmanifest">
<meta name="theme-color" content="#C4943A">
```

---

## Strategic Icon Placements

### 1. Footer Tagline (Replace Glowing Circle)

```html
<footer class="site-footer">
    <div class="footer-brand">
        <img src="/assets/favicons/lantern-icon-64.png" 
             alt="Lantern" 
             class="footer-lantern"
             width="48" 
             height="48">
        <p class="tagline"><em>Where Seekers and Saints Find Common Ground</em></p>
        <p class="author">Brother Aaron Powner</p>
    </div>
</footer>

<style>
.footer-lantern {
    display: block;
    margin: 0 auto 1rem;
    opacity: 0.9;
    filter: drop-shadow(0 0 10px rgba(196, 148, 58, 0.5));
}
</style>
```

### 2. Header Logo Enhancement

```html
<header class="site-header">
    <a href="/" class="logo-link">
        <img src="/assets/favicons/lantern-icon-64.png" 
             alt="" 
             class="header-lantern"
             width="32" 
             height="32">
        <span class="site-title">WORDS OF PLAINNESS</span>
    </a>
</header>

<style>
.logo-link {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    text-decoration: none;
}

.header-lantern {
    filter: drop-shadow(0 0 6px rgba(196, 148, 58, 0.4));
}
</style>
```

### 3. Audio Player (Glowing When Active)

```html
<button class="audio-play-btn" id="audioToggle">
    <img src="/assets/favicons/lantern-icon-64.png" 
         alt="Play" 
         class="audio-lantern"
         width="40" 
         height="40">
    <span>Read Aloud</span>
</button>

<style>
.audio-lantern {
    transition: filter 0.3s ease;
    filter: grayscale(50%) brightness(0.7);
}

.audio-play-btn.playing .audio-lantern {
    filter: grayscale(0%) brightness(1) drop-shadow(0 0 12px rgba(196, 148, 58, 0.8));
    animation: glow-pulse 2s ease-in-out infinite;
}

@keyframes glow-pulse {
    0%, 100% { filter: drop-shadow(0 0 8px rgba(196, 148, 58, 0.6)); }
    50% { filter: drop-shadow(0 0 16px rgba(196, 148, 58, 0.9)); }
}
</style>
```

### 4. Loading State

```html
<div class="loading-overlay" id="pageLoader">
    <img src="/assets/favicons/lantern-icon-128.png" 
         alt="Loading..." 
         class="loading-lantern">
    <p>Lighting the way...</p>
</div>

<style>
.loading-overlay {
    position: fixed;
    inset: 0;
    background: #2A1D14;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    z-index: 9999;
}

.loading-lantern {
    width: 80px;
    height: 80px;
    animation: lantern-flicker 1.5s ease-in-out infinite;
}

@keyframes lantern-flicker {
    0%, 100% { opacity: 0.7; transform: scale(1); }
    50% { opacity: 1; transform: scale(1.05); }
}
</style>
```

### 5. Section Dividers

```html
<div class="section-divider">
    <span class="divider-line"></span>
    <img src="/assets/favicons/lantern-icon-64.png" 
         alt="" 
         class="divider-lantern"
         width="24" 
         height="24">
    <span class="divider-line"></span>
</div>

<style>
.section-divider {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    margin: 3rem 0;
}

.divider-line {
    flex: 1;
    max-width: 100px;
    height: 1px;
    background: linear-gradient(90deg, transparent, #C4943A, transparent);
}

.divider-lantern {
    opacity: 0.6;
}
</style>
```

### 6. Bookmark Confirmation Toast

```html
<div class="toast" id="bookmarkToast">
    <img src="/assets/favicons/lantern-icon-64.png" 
         alt="" 
         width="24" 
         height="24">
    <span>Your place is saved</span>
</div>

<style>
.toast {
    position: fixed;
    bottom: 2rem;
    left: 50%;
    transform: translateX(-50%) translateY(100px);
    background: #3D2B1F;
    border: 1px solid #C4943A;
    padding: 0.75rem 1.5rem;
    border-radius: 8px;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    color: #E8DCC4;
    opacity: 0;
    transition: all 0.3s ease;
    z-index: 1000;
}

.toast.show {
    transform: translateX(-50%) translateY(0);
    opacity: 1;
}
</style>
```

### 7. 404 Error Page

```html
<main class="error-page">
    <img src="/assets/favicons/lantern-icon-256.png" 
         alt="Lost?" 
         class="error-lantern"
         width="120" 
         height="120">
    <h1>Page Not Found</h1>
    <p>The path you're looking for seems to have faded into shadow.</p>
    <a href="/" class="btn-primary">Return Home</a>
</main>

<style>
.error-page {
    min-height: 60vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 2rem;
}

.error-lantern {
    filter: grayscale(30%) brightness(0.6);
    margin-bottom: 2rem;
}
</style>
```

### 8. Chapter Table of Contents

```html
<nav class="toc-sidebar">
    <h3>
        <img src="/assets/favicons/lantern-icon-64.png" 
             alt="" 
             width="20" 
             height="20"
             style="vertical-align: middle; margin-right: 0.5rem;">
        Contents
    </h3>
    <ul>
        <li><a href="#section-1">Section One</a></li>
        <li><a href="#section-2">Section Two</a></li>
    </ul>
</nav>
```

---

## CSS Variables for Consistency

Add these to your main stylesheet:

```css
:root {
    /* Brand Colors */
    --gold-primary: #C4943A;
    --cream: #E8DCC4;
    --deep-brown: #3D2B1F;
    --rich-brown: #2A1D14;
    --burgundy: #6B3D3D;
    --teal-muted: #4A6B6B;
    
    /* Lantern Glow Effects */
    --lantern-glow-subtle: drop-shadow(0 0 6px rgba(196, 148, 58, 0.3));
    --lantern-glow-medium: drop-shadow(0 0 10px rgba(196, 148, 58, 0.5));
    --lantern-glow-strong: drop-shadow(0 0 16px rgba(196, 148, 58, 0.8));
}
```

---

## Discord Server Icon

The `android-chrome-512x512.png` file works perfectly as your Discord server icon.

Upload it via: Server Settings → Overview → Server Icon

---

*"Thy word is a lamp unto my feet, and a light unto my path."*
— Psalm 119:105
