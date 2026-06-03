# WoP Admin Dashboard — Specification v1.0

**Target system:** Django backend on PythonAnywhere (`/home/apowner/wop-api/`)
**Deployment:** Two-pass build via Claude Code + PythonAnywhere Files/Consoles API
**Author:** Aaron Powner Publishing · Words of Plainness Ministry
**Status:** Approved for build — Pass 1 ready to execute

---

## 1 · Purpose

Give Brother Aaron an at-a-glance ministry health dashboard inside the existing Django admin at `apowner.pythonanywhere.com/admin/`. Two functions:

1. **Cumulative ministry totals** for goal-setting, monthly reporting, and team communication.
2. **Weekly tallies** for short-term operational decision-making — where to put attention this week.

Plus a non-negotiable third function: **abuse reports must never be silently neglected.** A separate banner with urgency-tiered styling sits above everything else on the admin index, redundant with the SMS/email channels defined in Community Safety & Moderation Protocol v1.0 §3.

---

## 2 · Architecture — Two Tiers

### Tier 1 · Admin Index Page (`/admin/`)

Where Aaron lands when he logs into Django admin. Contains, in vertical order:

1. **Abuse Report Banner** — full-width, urgency-styled, always visible.
2. **Six Stat Cards** — grid layout, 3 columns on desktop, stacking on narrow screens.
3. **Original Django admin app/model navigation** — preserved exactly as today, below the cards.

The cards and banner are injected by overriding the `index` method of the default `AdminSite` and pointing `index_template` to a custom template that extends Django's stock `admin/index.html`. No model registrations change. No new admin site class. Non-invasive.

### Tier 2 · Analytics Dashboard (`/admin/dashboard/`)

A separate staff-only view linked from the admin index (button below the stat cards: "Open Analytics Dashboard →"). Renders Chart.js visualizations of engagement events, pause responses, card commitments, and reading progress.

Pass 1 ships a static last-30-days view. Pass 2 adds filters (date range, chapter multi-select, event type).

---

## 3 · Stat Card Spec

Six cards on the admin index, in this order:

| # | Card | Cumulative Total Source | Weekly Tally Source |
|---|------|-------------------------|---------------------|
| 1 | **Ministry Users** | `User.objects.count()` | `User.objects.filter(date_joined__gte=week_ago).count()` |
| 2 | **Email Verifications** | Verified users to date | Verifications completed in last 7 days |
| 3 | **Contact Submissions** | `ContactSubmission.objects.count()` | Last 7 days |
| 4 | **Content Suggestions** | Suggestion model count | Last 7 days |
| 5 | **Newsletter Subscribers** | `Subscriber.objects.filter(active=True).count()` | Net new in last 7 days |
| 6 | **Submission Moderation Queue** | Items currently awaiting review | New items entered queue in last 7 days |

Each card displays:

- **Card label** (small, gold-primary `#C4943A`, uppercase Cinzel-style)
- **Cumulative total** (large display number, cream `#E8DCC4`)
- **Secondary line** below the total: "+12 this week" (green if positive movement, neutral cream if zero, no negative styling — a drop in subscribers reads as a number, not a problem to solve in the UI)
- **8-week sparkline** (tiny chart at the bottom of the card, ~40px tall, showing the last 8 weekly totals as a trend line)

Card 6 (Submission Moderation Queue) is functional — the cumulative total is the *current open queue size*, not lifetime submissions. Weekly tally is *new items entered queue*. This card always visibly invites action when non-zero.

### Color tokens (match site brand)

```
--gold-primary:  #C4943A
--gold-light:    #D4A84A
--cream:         #E8DCC4
--cream-dim:     #B8A888
--rich-brown:    #1E1208
--deep-brown:    #2A1D14
--burgundy:      #6B3D3D   (used only for abuse banner alert states)
--alert-red:     #C44A3A   (CRITICAL state only)
--alert-amber:   #C49A3A   (HIGH/STANDARD review states)
--ok-green:      #6AB187   (queue empty / quiet state)
```

---

## 4 · Abuse Report Banner

Sits above the stat card grid. Always visible. Three states driven by the abuse report queue:

### State A — Quiet (no open reports)
- Background: `var(--ok-green)` at 12% opacity, left border 3px solid `--ok-green`
- Icon: ✓
- Text: "No open abuse reports. Last reviewed: [N] hours/days ago."

### State B — Attention (1+ STANDARD or HIGH reports open)
- Background: `var(--alert-amber)` at 15% opacity, left border 3px solid `--alert-amber`
- Icon: ⚠
- Text: "[N] STANDARD reports awaiting review. Oldest: [N hours]."
- Includes inline link: "Review reports →" pointing to admin changelist for the abuse report model.

### State C — Critical (1+ CRITICAL reports open)
- Background: `var(--alert-red)` at 20% opacity, left border 3px solid `--alert-red`
- Icon: 🔴
- Text: "[N] CRITICAL report — IMMEDIATE ACTION REQUIRED. Submitted [N minutes/hours] ago."
- CSS animation: subtle pulse on the icon, 2-second cycle, infinite. Stops only when the queue is cleared.
- Includes inline link: "Review now →"

### Cumulative count line below banner
- Smaller text, regardless of state: "Total reports received to date: [N] · This year: [N]"
- This is the goal-tracking number. Banner state is the operational signal.

### Tier mapping (from Community Safety Protocol v1.0 §3)
- **CRITICAL** → State C
- **HIGH** → State C if any HIGH is more than 1 hour unreviewed; else State B
- **STANDARD** → State B
- **LOW** → State B (treated like STANDARD for banner purposes; only CRITICAL/HIGH urgency is visually distinguished)

---

## 5 · Analytics Dashboard Spec — Tier 2

Page at `/admin/dashboard/`. Behind `staff_member_required`. Same color palette as admin index. Loads Chart.js v4.4 from CDN (single `<script>` tag, no build step).

### Pass 1 sections (ship in first build)

**Section A — Engagement Events Over Time**
- Stacked line chart, last 30 days, daily buckets
- Series: `page_view`, `audio_play`, `audio_complete`, `modal_open`, `rjw_open`, `rjw_save`, `bookmark`, `complete`
- Each series gets a brand color from the gold/cream/burgundy/teal palette
- Y-axis: event count per day
- Tooltip: date, series name, count

**Section B — Pause Responses by Chapter and Tab**
- Grouped bar chart, last 30 days
- X-axis: chapter (chapter_slug, ordered by chapter number)
- Bars per chapter: Reflect (teal `#3A6363`), Journal (burgundy `#6B3D3D`), Witness (gold-dim `#8A6628`)
- Y-axis: number of pause responses saved

### Pass 2 sections (deferred — second build)

**Section C — Card Commitments by Tier per Chapter**
- Grouped bar chart, all-time
- X-axis: chapter (only card-chapters: 12, 13, 14, 16+)
- Bars per chapter: Tier 1, Tier 2, Tier 3 (or whatever tier vocabulary the model uses)
- Secondary chart: average confidence rating per card_id

**Section D — Reading Progress Funnel**
- Per-chapter funnel: started → 25% → 50% → 75% → 100%
- Visual: horizontal bar chart with descending lengths showing drop-off
- Useful for identifying chapters where readers stop

**Filters bar (top of page, Pass 2)**
- Date range: 7d / 30d / 90d / all-time / custom
- Chapter multi-select
- Event type multi-select (engagement section only)
- Authenticated vs. anonymous toggle (engagement section only)

---

## 6 · Pre-Flight Inspection (Critical First Step for Claude Code)

Before writing any code, the build session must inspect the actual model classes and field names in the existing Django backend. Spec assumes these likely model locations but Claude Code must verify:

| Concern | Likely Location | What to Confirm |
|---------|-----------------|-----------------|
| User | `django.contrib.auth.models.User` | Default Django user — confirmed |
| Email verification | `apps.accounts.models` or `apps.auth.models` (need to verify) | Model name, field for "verified" flag, timestamp field |
| Contact submission | `apps.contact.models.ContactSubmission` | Confirmed in session memory |
| Content suggestion | `apps.contact.models.Suggestion` (or similar) | Confirm class name |
| Newsletter subscriber | `apps.newsletter.models.Subscriber` | Confirmed in session memory; check `active` field |
| Engagement event | `apps.progress.models.EngagementEvent` | Confirmed |
| Pause response | `apps.progress.models.PausePointResponse` | Confirmed |
| Card commitment | `apps.progress.models.CardCommitmentResponse` | Confirmed |
| Reading progress | `apps.progress.models.ReadingProgress` | Confirmed |
| Abuse report | UNKNOWN — possibly `apps.safety.models.Report` or `apps.moderation.models.AbuseReport` | **Must inspect.** If model does not yet exist, build the dashboard with placeholder query that returns zero/quiet state, and add a TODO comment. Phase 0 abuse reporting infrastructure may not have shipped this model yet. |
| Submission moderation queue | UNKNOWN — possibly `ReflectionReport` (per RAG_RJW_System spec) or another model | **Must inspect.** Same fallback as abuse report. |

**Inspection command (Claude Code runs this first):**

```bash
cd /home/apowner/wop-api && grep -rn "class.*models.Model" apps/ --include="*.py" | head -50
```

Then read the relevant `models.py` files identified by the grep to confirm field names. The build proceeds with the actual schema, not assumptions.

---

## 7 · File Build Spec

### 7.1 New app: `apps/dashboard/`

```
apps/dashboard/
├── __init__.py
├── apps.py
├── urls.py
├── views.py
├── utils.py
├── templatetags/
│   ├── __init__.py
│   └── dashboard_extras.py
└── templates/
    ├── admin/
    │   └── index.html              ← extends Django admin index, adds banner + cards
    └── dashboard/
        └── analytics.html          ← Tier 2 dashboard page
```

### 7.2 `apps/dashboard/apps.py`

Standard Django app config. The `ready()` method monkey-patches the default admin site to use a custom index view that injects stat card context:

- `name = 'apps.dashboard'`
- `verbose_name = 'WoP Dashboard'`
- In `ready()`: import the custom index view from `views.py` and replace `admin.site.index = custom_index_view`. Also set `admin.site.index_template = 'admin/index.html'` (resolves to our override since `apps.dashboard` is listed before `django.contrib.admin` in INSTALLED_APPS).

### 7.3 `apps/dashboard/utils.py`

Pure functions. No Django views. Reusable from index view AND analytics view.

- `get_week_window()` — returns (this_week_start, last_week_start) as datetime objects, anchored to Monday 00:00 UTC
- `get_week_count(model_qs, ts_field='created_at')` — count of rows in the queryset where ts_field is in the current week
- `get_cumulative_count(model_qs)` — total count of rows in queryset
- `get_sparkline_data(model_qs, ts_field='created_at', weeks=8)` — returns list of 8 integers, each the count for one of the last 8 weeks, oldest first
- `get_abuse_banner_state(report_model)` — returns dict: `{state: 'quiet'|'attention'|'critical', message: str, count: int, oldest_age_minutes: int}`. If `report_model` is None (Phase 0 not shipped), returns `{state: 'quiet', message: 'Abuse reporting infrastructure pending Phase 0 deployment', count: 0}`.
- `get_engagement_chart_data(days=30)` — returns dict shaped for Chart.js: `{labels: [...], datasets: [{label: event_type, data: [...], backgroundColor: ...}, ...]}`
- `get_pause_chart_data(days=30)` — same shape, grouped by chapter and tab type

All time-window aggregations use `django.db.models.functions.TruncDay` and `TruncWeek` — works cleanly on the MySQL backend.

### 7.4 `apps/dashboard/views.py`

Two callables:

**`custom_admin_index(request, extra_context=None)`** — replaces `admin.site.index`. Wraps the original Django index view. Builds context dict with:
- `abuse_banner` (dict from `get_abuse_banner_state`)
- `stat_cards` (list of 6 dicts, each with: `label`, `total`, `weekly_count`, `sparkline_data`, `link_url`)
- `analytics_url` (reverse to `/admin/dashboard/`)

Calls the original `AdminSite.index()` method with the extra context, returning the rendered response.

**`analytics_dashboard(request)`** — Tier 2 view. Decorated with `@staff_member_required`. Builds context with:
- `engagement_chart` (JSON-serializable dict from `get_engagement_chart_data(30)`)
- `pause_chart` (JSON-serializable dict from `get_pause_chart_data(30)`)

Renders `dashboard/analytics.html`.

### 7.5 `apps/dashboard/urls.py`

```python
from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.analytics_dashboard, name='analytics'),
]
```

Mounted at `admin/dashboard/` from the project urls.

### 7.6 `apps/dashboard/templatetags/dashboard_extras.py`

Two filters:
- `format_count` — formats integers with thousands separators ("1,247")
- `humanize_age` — formats minutes/hours/days for the abuse banner ("18 hours ago", "22 minutes ago")

### 7.7 `apps/dashboard/templates/admin/index.html`

Extends Django's stock `admin/index.html`. Overrides the `content` block. Structure:

```
{% extends "admin/index.html" %}
{% load static dashboard_extras %}

{% block extrastyle %}
  {{ block.super }}
  <style>/* dashboard-specific CSS — banner, cards, sparklines */</style>
{% endblock %}

{% block content %}
  <!-- Abuse Report Banner -->
  <div class="wop-abuse-banner wop-abuse-{{ abuse_banner.state }}">...</div>

  <!-- Stat Card Grid -->
  <div class="wop-stat-grid">
    {% for card in stat_cards %}
      <div class="wop-stat-card">
        <div class="wop-stat-label">{{ card.label }}</div>
        <div class="wop-stat-total">{{ card.total|format_count }}</div>
        <div class="wop-stat-weekly">+{{ card.weekly_count }} this week</div>
        <svg class="wop-stat-sparkline" ...>{{ sparkline rendered as polyline }}</svg>
      </div>
    {% endfor %}
  </div>

  <!-- Analytics dashboard link -->
  <div class="wop-analytics-cta">
    <a href="{{ analytics_url }}">Open Analytics Dashboard →</a>
  </div>

  <!-- Original Django admin app/model navigation -->
  {{ block.super }}
{% endblock %}
```

Sparklines rendered server-side as inline SVG polylines — no client-side JS needed, scales correctly, no external library on the index page.

### 7.8 `apps/dashboard/templates/dashboard/analytics.html`

Standalone page. Uses Django admin's `base_site.html` for chrome consistency. Loads Chart.js from CDN. Renders two `<canvas>` elements — one per chart section. Each chart receives data via `{{ engagement_chart|json_script:"engagement-data" }}` and a small inline `<script>` reads the JSON and instantiates Chart.js.

Pass 2 will add a filter form at the top that submits via GET and re-renders with filtered context.

### 7.9 Settings change

`/home/apowner/wop-api/wop_api/settings.py` — `INSTALLED_APPS` modification:

The new app must come **before** `django.contrib.admin` so its template override takes precedence:

```python
INSTALLED_APPS = [
    'apps.dashboard',          # ← NEW: must be before django.contrib.admin
    'django.contrib.admin',
    'django.contrib.auth',
    # ... rest unchanged
]
```

### 7.10 Project URLs change

`/home/apowner/wop-api/wop_api/urls.py` — add include for dashboard:

```python
urlpatterns = [
    path('admin/dashboard/', include('apps.dashboard.urls')),  # ← NEW: before admin
    path('admin/', admin.site.urls),
    # ... rest unchanged
]
```

The dashboard route comes before `admin/` because Django matches URL patterns top-down.

---

## 8 · Pass 1 Build — Claude Code Prompt

Use this prompt verbatim in Claude Code. The session must run on the Words of Plainness repo with PythonAnywhere API access already configured.

---

**=== CLAUDE CODE PROMPT (Pass 1) ===**

```
You are building the Pass 1 of the WoP Admin Dashboard on the Django backend at PythonAnywhere (/home/apowner/wop-api/). Read the full spec first at C:\Users\aaron\Documents\words-of-plainness\docs\WoP_AdminDashboard_Spec_v1.md and follow it precisely.

STEP 1 — INSPECT EXISTING MODELS
Use the PythonAnywhere Files API to read these files and identify the exact model class names and field names:
- /home/apowner/wop-api/apps/contact/models.py
- /home/apowner/wop-api/apps/newsletter/models.py
- /home/apowner/wop-api/apps/progress/models.py
- Also run: grep -rn "class.*models.Model" /home/apowner/wop-api/apps/ --include="*.py"

Identify in particular:
1. The contact/suggestion model class names and fields
2. The Subscriber model "active" field name (could be is_active, active, status, etc.)
3. Whether an email verification model exists (and if so, where and what fields)
4. Whether an abuse report model exists (likely apps/safety/, apps/moderation/, or similar)
5. Whether a submission moderation queue model exists (per RAG_RJW spec it could be ReflectionReport)

Report all findings before proceeding. If a model doesn't exist (abuse report, submission moderation), build the corresponding stat card and banner with a placeholder query that returns zero and a TODO comment in utils.py.

STEP 2 — CREATE THE NEW APP
Create the directory structure described in spec section 7.1 on PythonAnywhere:
- /home/apowner/wop-api/apps/dashboard/__init__.py
- /home/apowner/wop-api/apps/dashboard/apps.py
- /home/apowner/wop-api/apps/dashboard/urls.py
- /home/apowner/wop-api/apps/dashboard/views.py
- /home/apowner/wop-api/apps/dashboard/utils.py
- /home/apowner/wop-api/apps/dashboard/templatetags/__init__.py
- /home/apowner/wop-api/apps/dashboard/templatetags/dashboard_extras.py
- /home/apowner/wop-api/apps/dashboard/templates/admin/index.html
- /home/apowner/wop-api/apps/dashboard/templates/dashboard/analytics.html

Implement each file according to spec sections 7.2 through 7.8. Use the actual model class names and field names you discovered in Step 1. The template HTML, CSS, and JavaScript must use the brand color tokens listed in spec section 3.

STEP 3 — UPDATE SETTINGS AND PROJECT URLS
- Add 'apps.dashboard' to INSTALLED_APPS in /home/apowner/wop-api/wop_api/settings.py — must come BEFORE 'django.contrib.admin'
- Add the dashboard URL include to /home/apowner/wop-api/wop_api/urls.py — must come BEFORE the admin/ include

STEP 4 — RELOAD WEBAPP
Use the PythonAnywhere API to reload the apowner.pythonanywhere.com webapp.

STEP 5 — VERIFY
Use curl to fetch https://apowner.pythonanywhere.com/admin/login/ and confirm 200 response. Then provide instructions for Aaron to log in and visually verify:
1. Admin index shows the abuse banner at the top
2. Six stat cards render below the banner with cumulative totals and weekly counts
3. Sparklines render as small SVG charts
4. The "Open Analytics Dashboard →" link appears below the cards
5. The original Django admin app/model navigation still appears below the cards
6. Clicking the analytics link loads /admin/dashboard/ with two charts

Report any errors you encounter. Do NOT modify any model files. Do NOT run migrations (no model changes are required for Pass 1). Do NOT touch any frontend (Eleventy) code.

After successful deployment, push any local repo changes (none expected, but check) directly to main. Do not create a PR.
```

**=== END CLAUDE CODE PROMPT ===**

---

## 9 · Verification Checklist (run after Pass 1 deploys)

- [ ] `apowner.pythonanywhere.com/admin/` loads without 500 error
- [ ] Abuse report banner appears at top with appropriate state
- [ ] Six stat cards render with correct labels and reasonable numbers
- [ ] Cumulative totals match what `manage.py shell` returns for each model count
- [ ] Weekly counts are non-negative integers
- [ ] Sparklines render as small SVG curves (no JS console errors)
- [ ] "Open Analytics Dashboard →" link works
- [ ] `/admin/dashboard/` loads with engagement line chart and pause response bar chart
- [ ] Charts populate with last-30-days data
- [ ] Original Django admin app navigation still works (click into Users, ContactSubmission, etc.)
- [ ] No Django warnings in error log on PythonAnywhere

---

## 10 · Known Gotchas & Standing Notes

### MySQL date functions
The backend migrated to MySQL on March 29, 2026. `TruncDay`, `TruncWeek`, `TruncMonth` from `django.db.models.functions` work natively. No timezone surprises if `USE_TZ = True` in settings (it is). All week boundaries anchored to Monday 00:00 UTC.

### Template override precedence
Django finds templates by walking `INSTALLED_APPS` order. `apps.dashboard` MUST come before `django.contrib.admin` for the index template override to load. Verify by checking that the index page actually shows the new content — if it shows the stock Django admin without the banner/cards, the app order is wrong.

### Performance at scale
At current event volumes (low thousands of EngagementEvent rows), aggregations are fast. If event volume grows past ~100k rows, add a database index on `EngagementEvent(created_at, event_type)` and consider materialized day-rollup tables. Not a concern today — flag for revisit if dashboard load time exceeds 2 seconds.

### Phase 0 abuse infrastructure
If the abuse report model doesn't yet exist when this build runs, the banner ships in "quiet" state with a TODO comment in `utils.py`. When Phase 0 ships and the abuse report model lands, the only change needed is updating `get_abuse_banner_state()` in `utils.py` to query the real model. No template change.

### Privacy posture
All stat aggregations are counts. No individual user records appear on the dashboard. Engagement chart aggregates by event_type and day, never by user_id. Even though only Aaron sees admin, this is the right default — keeps the dashboard safe to screenshot for ministry reports without scrubbing.

### Worktree pattern (recurring lesson)
Per standing technical lesson: after Claude Code reports completion, verify on disk before trusting. For PythonAnywhere changes specifically, verify by curl-fetching the live URL — the PythonAnywhere Files API is authoritative ground truth.

### Code block rule
No PowerShell or shell commands needed locally for Pass 1 — all changes happen on PythonAnywhere via Claude Code's API access. The only "executable" content in this spec is the Claude Code prompt in Section 8, which is wrapped correctly.

---

## 11 · Pass 2 Build (Deferred — Schedule Separately)

When ready to add filters and the remaining two sections:

- Filter form at top of `/admin/dashboard/` (date range, chapter multi-select, event type, auth/anon toggle)
- Section C: Card commitments by tier per chapter
- Section D: Reading progress funnel
- 30-day sparkline toggle on the index page stat cards (currently 8-week)

Estimated 2.5 hours. New spec doc (`WoP_AdminDashboard_Spec_v1.1.md`) will define the filter contract, query builder helpers, and any new index requirements.

---

## 12 · Future Enhancements (post-Pass 2, no commitment)

- **Email digest of weekly stats** — Saturday morning auto-email to host@brotheraaron.org with the same six numbers + a one-line "biggest movement this week" headline. Reuses `utils.py` aggregation functions; new `apps/dashboard/management/commands/send_weekly_digest.py`.
- **Cohort retention** — for registered users, what % return after 7/30/90 days. Single chart on dashboard.
- **R·J·W content engagement heatmap** — chapter × tab × pause-point grid, color intensity by save count. Identifies which pause-points are landing.
- **Card chapter comparison** — average commitment tier and confidence side-by-side across all card chapters.

These are notes for later sessions, not part of any committed scope.

---

*Specification v1.0 — Approved for Pass 1 build · April 28, 2026*
*Document location: `C:\Users\aaron\Documents\words-of-plainness\docs\WoP_AdminDashboard_Spec_v1.md`*
*Companion: Engagement_Tracking_Handoff.md (engagement event tracking system, March 2026)*
