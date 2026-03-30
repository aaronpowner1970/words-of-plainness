# Engagement Event Tracking — Build Handoff
## Words of Plainness · Aaron Powner Publishing
## Prepared: March 27, 2026

---

## Purpose

This document is the complete handoff package for building the WoP engagement
event tracking system. It covers architecture decisions, all code to write,
exact integration points in existing files, and the Django backend changes
needed on PythonAnywhere.

Carry this document into the next session. The build requires two parts:

- **Part A — Frontend:** New file `src/js/engagement.js` + small additions to
  three existing JS files
- **Part B — Backend:** New Django model, view, and URL on PythonAnywhere

Both parts are independent. Part A can be built and deployed without Part B —
it will queue events in localStorage until the backend is ready.

---

## What Gets Tracked

| Event type | When it fires | Key data |
|---|---|---|
| `audio_play` | User presses play on chapter narration | chapter_slug, section_id |
| `audio_complete` | Audio reaches natural end | chapter_slug, section_id, duration_seconds |
| `download` | Click on PDF, slides, infographic download link | chapter_slug, resource_type, filename |
| `modal_open` | Resource modal opens (slides, infographic, testimony, overview) | chapter_slug, modal_type |
| `rjw_open` | R·J·W modal opens | chapter_slug, pause_id, tab |
| `rjw_save` | User saves a R·J·W response | chapter_slug, pause_id, tab |
| `bookmark` | Bookmark toggled ON | chapter_slug |
| `complete` | Mark Complete toggled ON | chapter_slug |
| `page_view` | Chapter page load | chapter_slug, is_authenticated |

Anonymous events are stored in localStorage and flushed to the backend on
login — same pattern as the existing reflection migration in `api.js`.

---

## Part A — Frontend: `src/js/engagement.js`

Create this file at `src/js/engagement.js`. It is self-contained and has no
external dependencies beyond `window.API` (already loaded globally).

```javascript
/**
 * WORDS OF PLAINNESS — Engagement Event Tracking
 * ================================================
 *
 * Tracks reader engagement events (audio plays, downloads, R·J·W usage,
 * bookmarks, completions) for ministry analytics.
 *
 * Architecture:
 * - Always queues events to localStorage (works for anonymous users)
 * - If authenticated: POSTs to Django immediately, clears queue
 * - On login: flushes anonymous queue to backend (same pattern as reflections)
 * - Batch POST endpoint accepts array of events
 */

const Engagement = {

    STORAGE_KEY: 'wop-engagement-queue',
    API_ENDPOINT: '/events/',

    // ─── CORE TRACK METHOD ───────────────────────────────────────

    /**
     * Track an engagement event.
     * @param {string} eventType  - one of the event types listed in handoff doc
     * @param {object} data       - event-specific payload (chapter_slug required)
     */
    track(eventType, data = {}) {
        const event = {
            event_type: eventType,
            chapter_slug: data.chapter_slug || this._currentChapter(),
            metadata: { ...data },
            client_ts: new Date().toISOString()
        };
        // Remove chapter_slug from metadata (it's a top-level field)
        delete event.metadata.chapter_slug;

        if (window.API?.isAuthenticated()) {
            this._post([event]);
        } else {
            this._enqueue(event);
        }
    },

    // ─── QUEUE MANAGEMENT ────────────────────────────────────────

    _enqueue(event) {
        try {
            const queue = this._loadQueue();
            queue.push(event);
            // Cap queue at 100 events to avoid localStorage bloat
            const trimmed = queue.slice(-100);
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(trimmed));
        } catch (e) { /* localStorage unavailable — silent */ }
    },

    _loadQueue() {
        try {
            return JSON.parse(localStorage.getItem(this.STORAGE_KEY) || '[]');
        } catch (e) {
            return [];
        }
    },

    _clearQueue() {
        try {
            localStorage.removeItem(this.STORAGE_KEY);
        } catch (e) { /* silent */ }
    },

    // ─── FLUSH ON LOGIN ──────────────────────────────────────────

    /**
     * Called after successful login/register (wire into api.js setAuth).
     * Flushes any queued anonymous events to the backend.
     */
    async flushQueue() {
        const queue = this._loadQueue();
        if (queue.length === 0) return;
        try {
            await this._post(queue);
            this._clearQueue();
        } catch (e) {
            console.warn('Engagement queue flush failed:', e);
        }
    },

    // ─── POST TO BACKEND ─────────────────────────────────────────

    async _post(events) {
        if (!window.API?.baseUrl) return;
        try {
            await window.API.request(this.API_ENDPOINT, {
                method: 'POST',
                body: JSON.stringify({ events })
            });
        } catch (e) {
            // If post fails, re-enqueue events for next attempt
            events.forEach(ev => this._enqueue(ev));
        }
    },

    // ─── HELPERS ─────────────────────────────────────────────────

    _currentChapter() {
        // Read chapter slug from ChapterManager config if available
        return window.ChapterManager?.config?.id || '';
    },

    // ─── AUTO-WIRE PAGE VIEW ──────────────────────────────────────

    /**
     * Call once on chapter page load. Tracks page_view and wires
     * to the login event for queue flushing.
     */
    initChapterPage() {
        // Track page view
        this.track('page_view', {
            is_authenticated: window.API?.isAuthenticated() || false
        });

        // Wire queue flush to auth events
        document.addEventListener('wop:auth-login', () => {
            this.flushQueue();
        });
    }
};

window.Engagement = Engagement;
```

---

## Part A — Integration Points in Existing Files

### 1. `src/js/api.js` — fire queue flush on login

In the `setAuth()` method, after `this.updateUIForAuth()` and
`this.checkReflectionMigration()`, add one line:

```javascript
// Existing line:
this.checkReflectionMigration();

// ADD THIS:
if (window.Engagement) window.Engagement.flushQueue();
```

Also dispatch a custom event so other listeners can hook into login:

```javascript
// ADD after the flushQueue line:
document.dispatchEvent(new CustomEvent('wop:auth-login', { detail: { user: this.user } }));
```

### 2. `src/js/chapter.js` — audio play, audio complete, bookmark, complete

In `play()` method, after `document.dispatchEvent(new Event('wop:audio-play'))`:

```javascript
// ADD:
if (window.Engagement) {
    window.Engagement.track('audio_play', {
        section_id: window.AudioSync?.currentSectionId || null
    });
}
```

In `onAudioEnd()` method, at the end:

```javascript
// ADD:
if (window.Engagement) {
    window.Engagement.track('audio_complete', {
        section_id: window.AudioSync?.currentSectionId || null,
        duration_seconds: Math.round(this.audioPlayer?.duration || 0)
    });
}
```

In `toggleBookmark()`, inside the `if (nowBookmarked)` block, after setting
localStorage:

```javascript
// ADD:
if (window.Engagement) window.Engagement.track('bookmark', {});
```

In `toggleComplete()`, inside the `if (nowComplete)` block, after setting
localStorage:

```javascript
// ADD:
if (window.Engagement) window.Engagement.track('complete', {});
```

In `openModal()` method, before the closing brace:

```javascript
// ADD:
if (window.Engagement) {
    window.Engagement.track('modal_open', {
        modal_type: modalId.replace('Modal', '')
    });
}
```

### 3. `src/js/chapter.js` — R·J·W hooks

In the `RJW` IIFE, in the `openModal()` function, after
`document.body.style.overflow = 'hidden'`:

```javascript
// ADD:
if (window.Engagement) {
    window.Engagement.track('rjw_open', {
        pause_id: pauseId,
        tab: tabKey
    });
}
```

In the `saveResponse()` function, after `saveStored(...)`:

```javascript
// ADD:
if (window.Engagement) {
    window.Engagement.track('rjw_save', {
        pause_id: activePauseId,
        tab: tabKey
    });
}
```

### 4. Resource download links — HTML templates

For any `<a>` tag that triggers a PDF, slides, or infographic download,
add an onclick attribute:

```html
<!-- PDF download example -->
<a href="/assets/pdfs/chapter-09-study-guide.pdf"
   download
   onclick="if(window.Engagement) window.Engagement.track('download', {
       resource_type: 'pdf',
       filename: 'chapter-09-study-guide.pdf'
   })">
  Download Study Guide
</a>

<!-- Slides download example -->
<a href="/assets/slides/chapter-09/slides.pdf"
   download
   onclick="if(window.Engagement) window.Engagement.track('download', {
       resource_type: 'slides',
       filename: 'chapter-09-slides.pdf'
   })">
  Download Slides
</a>
```

### 5. `src/_includes/layouts/chapter.njk` (or equivalent) — init call

In the chapter layout, after the `ChapterManager.init(config)` call, add:

```javascript
if (window.Engagement) window.Engagement.initChapterPage();
```

### 6. `src/_includes/layouts/base.njk` — load script

Add the script tag with other core scripts (after `api.js`, before
`chapter.js`):

```html
<script src="/js/engagement.js"></script>
```

---

## Part B — Django Backend: PythonAnywhere

Access your Django project at:
`/home/apowner/` on PythonAnywhere (Files tab or Bash console)

Your Django project structure is at (confirm exact path in PythonAnywhere):
`/home/apowner/mysite/` or similar — look for `manage.py`

### Step 1 — Add model to `models.py`

Find your main `models.py` (likely in your main app directory). Add:

```python
class EngagementEvent(models.Model):
    """
    Tracks reader engagement events for ministry analytics.
    Supports both authenticated and anonymous (user=None) events.
    """
    EVENT_TYPES = [
        ('page_view',      'Page View'),
        ('audio_play',     'Audio Play'),
        ('audio_complete', 'Audio Complete'),
        ('download',       'Download'),
        ('modal_open',     'Modal Open'),
        ('rjw_open',       'R·J·W Open'),
        ('rjw_save',       'R·J·W Save'),
        ('bookmark',       'Bookmark'),
        ('complete',       'Mark Complete'),
    ]

    user         = models.ForeignKey(
                       settings.AUTH_USER_MODEL,
                       null=True, blank=True,
                       on_delete=models.SET_NULL,
                       related_name='engagement_events'
                   )
    event_type   = models.CharField(max_length=32, choices=EVENT_TYPES, db_index=True)
    chapter_slug = models.CharField(max_length=128, blank=True, db_index=True)
    metadata     = models.JSONField(default=dict, blank=True)
    client_ts    = models.DateTimeField(null=True, blank=True)  # timestamp from browser
    created_at   = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['event_type', 'chapter_slug']),
            models.Index(fields=['created_at', 'event_type']),
        ]

    def __str__(self):
        user_str = self.user.username if self.user else 'anonymous'
        return f'{self.event_type} | {self.chapter_slug} | {user_str}'
```

### Step 2 — Add view to `views.py`

```python
from django.utils.dateparse import parse_datetime
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

@api_view(['POST'])
@permission_classes([AllowAny])
def track_events(request):
    """
    Accepts a batch of engagement events from the frontend.
    Works for both authenticated and anonymous users.
    POST /events/
    Body: { "events": [ { event_type, chapter_slug, metadata, client_ts }, ... ] }
    """
    events_data = request.data.get('events', [])

    if not isinstance(events_data, list):
        return Response(
            {'error': 'events must be a list'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Cap batch size to prevent abuse
    MAX_BATCH = 50
    if len(events_data) > MAX_BATCH:
        return Response(
            {'error': f'Maximum {MAX_BATCH} events per request'},
            status=status.HTTP_400_BAD_REQUEST
        )

    VALID_EVENT_TYPES = {
        'page_view', 'audio_play', 'audio_complete', 'download',
        'modal_open', 'rjw_open', 'rjw_save', 'bookmark', 'complete'
    }

    to_create = []
    for ev in events_data:
        event_type = ev.get('event_type', '')
        if event_type not in VALID_EVENT_TYPES:
            continue  # Skip unknown types silently

        client_ts = None
        raw_ts = ev.get('client_ts')
        if raw_ts:
            try:
                client_ts = parse_datetime(raw_ts)
            except Exception:
                pass

        to_create.append(EngagementEvent(
            user=request.user if request.user.is_authenticated else None,
            event_type=event_type,
            chapter_slug=ev.get('chapter_slug', '')[:128],
            metadata=ev.get('metadata', {}),
            client_ts=client_ts,
        ))

    if to_create:
        EngagementEvent.objects.bulk_create(to_create)

    return Response({'stored': len(to_create)}, status=status.HTTP_201_CREATED)
```

Also add the import at the top of `views.py` if not already present:

```python
from .models import EngagementEvent
```

### Step 3 — Add URL to `urls.py`

In your main `urls.py` (the one with all your `/api/v1/` routes), add:

```python
path('events/', views.track_events, name='track_events'),
```

It should sit alongside your other endpoints, e.g.:

```python
urlpatterns = [
    path('accounts/login/',    views.login_view),
    path('reflections/mine/',  views.reflections_view),
    path('progress/<slug>/',   views.progress_view),
    path('events/',            views.track_events),   # ← ADD THIS
    # ... etc
]
```

### Step 4 — Run migration on PythonAnywhere

In the PythonAnywhere Bash console:

```bash
cd /home/apowner/mysite   # adjust to your actual path
python manage.py makemigrations
python manage.py migrate
```

Then reload your web app in the PythonAnywhere Web tab.

### Step 5 — Register in Django admin (optional but recommended)

In `admin.py`:

```python
from .models import EngagementEvent

@admin.register(EngagementEvent)
class EngagementEventAdmin(admin.ModelAdmin):
    list_display  = ('event_type', 'chapter_slug', 'user', 'created_at')
    list_filter   = ('event_type', 'chapter_slug', 'created_at')
    search_fields = ('chapter_slug', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'client_ts', 'metadata')
    date_hierarchy = 'created_at'
```

---

## Build Order for Next Session

```
1. Part B first (backend) — no risk to live site, no deploy needed until tested
   a. PythonAnywhere Files tab → edit models.py → add EngagementEvent
   b. Edit views.py → add track_events
   c. Edit urls.py → add path('events/', ...)
   d. Bash console → makemigrations && migrate
   e. Reload web app
   f. Test: curl -X POST https://apowner.pythonanywhere.com/api/v1/events/
            -H "Content-Type: application/json"
            -d '{"events":[{"event_type":"page_view","chapter_slug":"test","metadata":{}}]}'
      Expected: {"stored": 1}

2. Part A (frontend) — after backend confirmed working
   a. Create src/js/engagement.js (full file above)
   b. Edit src/js/api.js — add flushQueue() + wop:auth-login event in setAuth()
   c. Edit src/js/chapter.js — add 6 Engagement.track() calls at integration points
   d. Edit base.njk — add <script src="/js/engagement.js"></script>
   e. Edit chapter layout — add Engagement.initChapterPage() call
   f. Add onclick attributes to download links in chapter templates

3. Verify
   a. Open chapter page in incognito → check localStorage for wop-engagement-queue
      Expected: queue contains page_view event
   b. Press play on narration → queue should gain audio_play event
   c. Log in → queue should flush (check Django admin → Engagement Events)
   d. Check /admin/dashboard/ → EngagementEvent rows present

4. Cloudflare audit (separate, no code)
   a. Cloudflare Dashboard → Analytics & Logs → Web Analytics
      Confirm wordsofplainness.org data flowing (page views, top pages)
```

---

## CORS Note

Your Django backend on PythonAnywhere already accepts requests from
`wordsofplainness.org` (it serves your existing API calls). No CORS changes
needed — the `/events/` endpoint uses `AllowAny` permission, same as contact
and newsletter endpoints.

---

## Future: Admin Dashboard Query Examples

Once events are flowing, these Django ORM queries power a simple dashboard:

```python
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta

# Top chapters by audio plays (last 30 days)
EngagementEvent.objects.filter(
    event_type='audio_play',
    created_at__gte=timezone.now() - timedelta(days=30)
).values('chapter_slug').annotate(count=Count('id')).order_by('-count')

# R·J·W engagement rate by chapter
EngagementEvent.objects.filter(
    event_type='rjw_save'
).values('chapter_slug', 'metadata__tab').annotate(count=Count('id'))

# Downloads by resource type
EngagementEvent.objects.filter(
    event_type='download'
).values('metadata__resource_type', 'chapter_slug').annotate(count=Count('id'))
```

These can be added to your existing `/admin/dashboard/` view when ready.

---

## Session-Open Prompt for Next Session

Paste this at the start of the build session:

> "I'm building the WoP engagement event tracking system from the handoff doc
> at docs/Engagement_Tracking_Handoff.md. Interface: Claude Desktop, MCPs loaded.
> Start by reading that file, then read src/js/api.js and src/js/chapter.js
> to orient to the codebase. Then proceed with Part B (Django backend) first."

---

*Words of Plainness · Aaron Powner Publishing · March 2026*
