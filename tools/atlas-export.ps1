<#
.SYNOPSIS
    Words of Plainness — Monthly Atlas Export
    Generates snapshot reports from the three operational YAML files.

.DESCRIPTION
    Reads chapter-status.yaml, infrastructure.yaml, and operational-state.yaml
    from the Eleventy repo. Produces:
      - Markdown summary report
      - Self-contained styled HTML report (printable)
      - Raw YAML copies
    Outputs to a timestamped folder in the Google Drive backup path.
    Enforces 6-month retention (deletes exports older than 180 days).

.NOTES
    Requires: powershell-yaml module (Install-Module -Name powershell-yaml -Scope CurrentUser)
    Schedule: Monthly via Windows Task Scheduler
    Author: Aaron Powner Publishing / SCRIBE
    Created: April 2026
#>

param(
    [string]$RepoPath = "C:\Users\aaron\Documents\words-of-plainness",
    [string]$BackupRoot = "H:\My Drive\Professional\Aaron Powner Publishing\backups\atlas",
    [int]$RetentionMonths = 6
)

# ── PREFLIGHT ─────────────────────────────────────────────────────

# Ensure powershell-yaml is available
if (-not (Get-Module -ListAvailable -Name powershell-yaml)) {
    Write-Error "Required module 'powershell-yaml' not found. Install with: Install-Module -Name powershell-yaml -Scope CurrentUser"
    exit 1
}
Import-Module powershell-yaml -ErrorAction Stop

$dataDir = Join-Path $RepoPath "src\_data"
$yamlFiles = @(
    @{ Name = "chapter-status.yaml";    Path = Join-Path $dataDir "chapter-status.yaml" },
    @{ Name = "infrastructure.yaml";    Path = Join-Path $dataDir "infrastructure.yaml" },
    @{ Name = "operational-state.yaml"; Path = Join-Path $dataDir "operational-state.yaml" }
)

# Verify all YAML files exist
foreach ($f in $yamlFiles) {
    if (-not (Test-Path $f.Path)) {
        Write-Error "YAML file not found: $($f.Path)"
        exit 1
    }
}

# Verify backup root exists (or create it)
if (-not (Test-Path $BackupRoot)) {
    New-Item -ItemType Directory -Path $BackupRoot -Force | Out-Null
    Write-Host "Created backup root: $BackupRoot"
}

# ── PARSE YAML ────────────────────────────────────────────────────

$now = Get-Date
$monthTag = $now.ToString("yyyy-MM")
$fullTimestamp = $now.ToString("yyyy-MM-dd HH:mm")

Write-Host "`n═══════════════════════════════════════════════════"
Write-Host "  Words of Plainness — Atlas Export"
Write-Host "  $fullTimestamp"
Write-Host "═══════════════════════════════════════════════════`n"

# Parse each YAML file
$chapterStatus = Get-Content $yamlFiles[0].Path -Raw | ConvertFrom-Yaml
$infrastructure = Get-Content $yamlFiles[1].Path -Raw | ConvertFrom-Yaml
$operationalState = Get-Content $yamlFiles[2].Path -Raw | ConvertFrom-Yaml

# ── EXTRACT CHAPTER DATA ──────────────────────────────────────────

function Get-ChapterList {
    param($volumeData, [int]$volumeNum)

    $chapters = @()
    # Iterate over movement keys (movement_1, movement_2, etc.)
    foreach ($key in $volumeData.Keys) {
        if ($key -match '^movement_\d+$' -or $key -eq 'conclusion') {
            $movement = $volumeData[$key]
            if ($movement.chapters) {
                foreach ($ch in $movement.chapters) {
                    $ch | Add-Member -NotePropertyName "volume" -NotePropertyValue $volumeNum -Force -ErrorAction SilentlyContinue
                    $ch | Add-Member -NotePropertyName "movement_title" -NotePropertyValue ($movement.title) -Force -ErrorAction SilentlyContinue
                    $chapters += $ch
                }
            }
        }
    }
    return $chapters
}

$vol1Chapters = Get-ChapterList -volumeData $chapterStatus.volume_1 -volumeNum 1
$vol2Chapters = Get-ChapterList -volumeData $chapterStatus.volume_2 -volumeNum 2
$allChapters = $vol1Chapters + $vol2Chapters

$deployedChapters = @($allChapters | Where-Object { $_.status -eq "deployed" })
$placeholderChapters = @($allChapters | Where-Object { $_.status -eq "placeholder" })

$vol1Deployed = @($deployedChapters | Where-Object { $_.volume -eq 1 }).Count
$vol2Deployed = @($deployedChapters | Where-Object { $_.volume -eq 2 }).Count

Write-Host "  Chapters: $($allChapters.Count) total ($($deployedChapters.Count) deployed, $($placeholderChapters.Count) placeholder)"

# ── EXTRACT INFRASTRUCTURE DATA ───────────────────────────────────

$services = $infrastructure.services
$pipelines = $infrastructure.pipelines

# Group by failure_impact
$impactGroups = @{
    "CRITICAL" = @()
    "HIGH"     = @()
    "MEDIUM"   = @()
    "LOW"      = @()
}

foreach ($svc in $services) {
    $impact = if ($svc.failure_impact -match "^(CRITICAL|HIGH|MEDIUM|LOW)") { $Matches[1] } else { "LOW" }
    $impactGroups[$impact] += $svc.name
}

# Staleness check (90-day threshold)
$staleThreshold = $now.AddDays(-90)
$staleServices = @()
$currentServices = @()

foreach ($svc in $services) {
    if ($svc.last_verified) {
        try {
            $verified = [DateTime]::Parse($svc.last_verified)
            if ($verified -lt $staleThreshold) {
                $staleServices += @{ Name = $svc.name; LastVerified = $svc.last_verified; DaysAgo = [math]::Round(($now - $verified).TotalDays) }
            } else {
                $currentServices += @{ Name = $svc.name; LastVerified = $svc.last_verified }
            }
        } catch {
            $staleServices += @{ Name = $svc.name; LastVerified = "(parse error)"; DaysAgo = "?" }
        }
    }
}

Write-Host "  Infrastructure: $($services.Count) services, $($pipelines.Count) pipelines"
Write-Host "  Staleness: $($staleServices.Count) stale, $($currentServices.Count) current"

# ── EXTRACT OPERATIONAL STATE ─────────────────────────────────────

$currentPhase = $operationalState.current_phase
$workstreams = $operationalState.workstreams
$blockedItems = $operationalState.blocked_items
$governance = $operationalState.governance_documents
$nextPriorities = $operationalState.next_priorities

# ── GENERATE MARKDOWN REPORT ─────────────────────────────────────

$md = @"
# Words of Plainness — Operational Atlas Export
**Generated:** $fullTimestamp
**Source:** src/_data/ in words-of-plainness repo

---

## Chapter Status Summary

- **Volume 1:** $($chapterStatus.volume_1.total_chapters) chapters ($vol1Deployed deployed, $($chapterStatus.volume_1.total_chapters - $vol1Deployed) placeholder)
- **Volume 2:** $($chapterStatus.volume_2.total_chapters) chapters ($vol2Deployed deployed, $($chapterStatus.volume_2.total_chapters - $vol2Deployed) placeholder)
- **Total:** $($allChapters.Count) chapters

### Deployed Chapters

| Vol | # | Title | Audio | Citations | R·J·W | PDF | Slides | Discord |
|-----|---|-------|-------|-----------|-------|-----|--------|---------|
"@

foreach ($ch in $deployedChapters) {
    $audioMark = if ($ch.audio -and $ch.audio.narration) { "NR" } else { "" }
    if ($ch.audio -and $ch.audio.overview) { $audioMark += "+PO" }
    if ($ch.audio -and $ch.audio.read_aloud) { $audioMark += "+RA" }
    if ($audioMark) { $audioMark = "✓ $audioMark" } else { $audioMark = "—" }

    $citeMark = if ($ch.citations) { "✓" } else { "—" }
    $rjwMark = if ($ch.rjw_pauses) { "✓ ($($ch.rjw_pauses))" } else { "—" }
    $pdfMark = if ($ch.resources -and $ch.resources.pdf) { "✓" } else { "—" }
    $slidesMark = if ($ch.resources -and $ch.resources.slides) { "✓ ($($ch.resources.slides_count))" } else { "—" }
    $discordMark = if ($ch.discord_channel_id) { "✓" } else { "—" }

    $md += "| $($ch.volume) | $($ch.number) | $($ch.title) | $audioMark | $citeMark | $rjwMark | $pdfMark | $slidesMark | $discordMark |`n"
}

$md += @"

### Placeholder Chapters

| Vol | # | Title | Movement | Format |
|-----|---|-------|----------|--------|
"@

foreach ($ch in $placeholderChapters) {
    $mvt = if ($ch.movement_title) { $ch.movement_title } else { "—" }
    $fmt = if ($ch.format) { $ch.format } else { "—" }
    $md += "| $($ch.volume) | $($ch.number) | $($ch.title) | $mvt | $fmt |`n"
}

$md += @"

---

## Infrastructure Health

### Services by Failure Impact

"@

foreach ($level in @("CRITICAL", "HIGH", "MEDIUM", "LOW")) {
    $names = $impactGroups[$level] -join ", "
    if ($names) {
        $md += "**${level}:** $names`n`n"
    }
}

$md += @"
### Staleness Report

| Service | Last Verified | Status |
|---------|--------------|--------|
"@

foreach ($svc in ($currentServices | Sort-Object { $_.Name })) {
    $md += "| $($svc.Name) | $($svc.LastVerified) | 🟢 Current |`n"
}
foreach ($svc in ($staleServices | Sort-Object { $_.Name })) {
    $emoji = if ($svc.DaysAgo -gt 180) { "🔴" } else { "🟡" }
    $md += "| $($svc.Name) | $($svc.LastVerified) | $emoji $($svc.DaysAgo) days ago |`n"
}

$md += @"

### Pipeline Status

| Pipeline | Status | Last Verified |
|----------|--------|--------------|
"@

foreach ($p in $pipelines) {
    $statusEmoji = switch ($p.status) { "operational" { "🟢" }; "degraded" { "🟡" }; "broken" { "🔴" }; default { "⚪" } }
    $md += "| $($p.name) | $statusEmoji $($p.status) | $($p.last_verified) |`n"
}

$md += @"

---

## Operational State

**Current Phase:** $($currentPhase.name)
$($currentPhase.description)

### Development Phases

| Phase | Name | Status |
|-------|------|--------|
"@

foreach ($phase in $currentPhase.development_phases) {
    $statusEmoji = switch ($phase.status) { "complete" { "✅" }; "in-progress" { "🔨" }; "not-started" { "⬜" }; default { "⬜" } }
    $md += "| $($phase.phase) | $($phase.name) | $statusEmoji $($phase.status) |`n"
}

$md += @"

### Active Workstreams

"@

foreach ($ws in $workstreams) {
    $statusTag = switch ($ws.status) { "in-progress" { "🔨" }; "pending" { "⏳" }; "not-started" { "⬜" }; "partially-complete" { "🔨" }; default { "⬜" } }
    $md += "- **$($ws.name)** $statusTag — $($ws.description)`n"
    if ($ws.next_action) { $md += "  - Next: $($ws.next_action)`n" }
    if ($ws.blocked_by) { $md += "  - ⚠ Blocked by: $($ws.blocked_by)`n" }
}

if ($blockedItems) {
    $md += "`n### Blocked Items`n`n"
    foreach ($item in $blockedItems) {
        $md += "- **$($item.item)** — $($item.reason)`n"
    }
}

if ($governance) {
    $md += "`n### Governance Documents`n`n"
    $md += "| Document | Location | Last Updated |`n"
    $md += "|----------|----------|-------------|`n"
    foreach ($doc in $governance) {
        $md += "| $($doc.title) | $($doc.location) | $($doc.last_updated) |`n"
    }
}

if ($nextPriorities) {
    $md += "`n### Next Priorities (Ordered)`n`n"
    $i = 1
    foreach ($p in $nextPriorities) {
        $md += "${i}. $p`n"
        $i++
    }
}

$md += @"

---

*Words of Plainness · Aaron Powner Publishing · Atlas Export $monthTag*
"@

# ── GENERATE HTML REPORT ──────────────────────────────────────────

$htmlContent = $md -replace '\|', '|'

$html = @"
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>WoP Atlas Export — $monthTag</title>
<style>
:root {
    --rich-brown: #1E1208;
    --deep-brown: #2A1D14;
    --gold: #C4943A;
    --gold-dim: #8A6628;
    --cream: #E8DCC4;
    --cream-dim: #B8A888;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    background: var(--rich-brown);
    color: var(--cream);
    font-family: 'Segoe UI', 'Crimson Pro', Georgia, serif;
    font-size: 15px;
    line-height: 1.6;
    max-width: 1000px;
    margin: 0 auto;
    padding: 40px 32px;
}
h1 {
    font-size: 28px;
    color: var(--gold);
    border-bottom: 2px solid var(--gold-dim);
    padding-bottom: 12px;
    margin-bottom: 8px;
}
h2 {
    font-size: 20px;
    color: var(--gold);
    margin-top: 32px;
    margin-bottom: 12px;
    border-bottom: 1px solid rgba(196,148,58,0.3);
    padding-bottom: 6px;
}
h3 {
    font-size: 16px;
    color: var(--cream);
    margin-top: 20px;
    margin-bottom: 8px;
}
p, li { margin-bottom: 8px; color: var(--cream); }
strong { color: var(--gold); }
hr { border: none; border-top: 1px solid rgba(196,148,58,0.2); margin: 24px 0; }
table {
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0 20px;
    font-size: 13px;
}
th {
    background: var(--deep-brown);
    color: var(--gold);
    text-align: left;
    padding: 8px 10px;
    border-bottom: 2px solid var(--gold-dim);
    font-weight: 600;
    white-space: nowrap;
}
td {
    padding: 6px 10px;
    border-bottom: 1px solid rgba(196,148,58,0.1);
    color: var(--cream-dim);
}
tr:hover td { background: rgba(196,148,58,0.04); }
ul, ol { padding-left: 24px; }
.meta {
    font-size: 13px;
    color: var(--cream-dim);
    margin-bottom: 20px;
}
.footer {
    text-align: center;
    font-size: 12px;
    color: var(--cream-dim);
    opacity: 0.5;
    margin-top: 40px;
    padding-top: 16px;
    border-top: 1px solid rgba(196,148,58,0.1);
}
@media print {
    body { background: white; color: #333; max-width: 100%; padding: 20px; }
    h1, h2, h3, strong { color: #333; }
    th { background: #f0f0f0; color: #333; }
    td { color: #555; }
    table { font-size: 11px; }
}
</style>
</head>
<body>
<div class="meta">Generated: $fullTimestamp &bull; Source: src/_data/ &bull; Words of Plainness</div>
"@

# Convert Markdown to HTML (simple conversion — handles tables, lists, headings)
$lines = $md -split "`n"
$inTable = $false
$tableHeaderDone = $false

foreach ($line in $lines) {
    $trimmed = $line.Trim()

    # Skip the YAML front matter line (title already in HTML header)
    if ($trimmed -match '^# Words of Plainness') {
        $html += "<h1>Operational Atlas Export</h1>`n"
        continue
    }
    if ($trimmed -match '^\*\*Generated:') {
        continue  # already in .meta div
    }

    # Headings
    if ($trimmed -match '^### (.+)') { $html += "<h3>$($Matches[1])</h3>`n"; continue }
    if ($trimmed -match '^## (.+)') { $html += "<h2>$($Matches[1])</h2>`n"; continue }

    # Horizontal rules
    if ($trimmed -eq '---') { $html += "<hr>`n"; continue }

    # Table rows
    if ($trimmed -match '^\|') {
        if (-not $inTable) {
            $html += "<table>`n"
            $inTable = $true
            $tableHeaderDone = $false
        }

        # Skip separator rows (|---|---|)
        if ($trimmed -match '^\|[\s\-\|]+\|$') {
            $tableHeaderDone = $true
            continue
        }

        $cells = ($trimmed -split '\|' | Where-Object { $_ -ne '' }) | ForEach-Object { $_.Trim() }
        if (-not $tableHeaderDone) {
            $html += "<thead><tr>"
            foreach ($cell in $cells) { $html += "<th>$cell</th>" }
            $html += "</tr></thead><tbody>`n"
        } else {
            $html += "<tr>"
            foreach ($cell in $cells) { $html += "<td>$cell</td>" }
            $html += "</tr>`n"
        }
        continue
    } elseif ($inTable) {
        $html += "</tbody></table>`n"
        $inTable = $false
        $tableHeaderDone = $false
    }

    # Bold text
    $trimmed = $trimmed -replace '\*\*(.+?)\*\*', '<strong>$1</strong>'

    # List items
    if ($trimmed -match '^- (.+)') {
        $html += "<li>$($trimmed.Substring(2))</li>`n"
        continue
    }
    if ($trimmed -match '^\d+\. (.+)') {
        $html += "<li>$($Matches[1])</li>`n"
        continue
    }

    # Paragraphs
    if ($trimmed -ne '' -and $trimmed -notmatch '^\*Words of Plainness') {
        $html += "<p>$trimmed</p>`n"
    }

    # Footer
    if ($trimmed -match '^\*Words of Plainness') {
        $html += "<div class='footer'>$($trimmed.Trim('*'))</div>`n"
    }
}

if ($inTable) {
    $html += "</tbody></table>`n"
}

$html += @"
</body>
</html>
"@

# ── WRITE OUTPUT FILES ────────────────────────────────────────────

$exportDir = Join-Path $BackupRoot "atlas-export-$monthTag"
if (-not (Test-Path $exportDir)) {
    New-Item -ItemType Directory -Path $exportDir -Force | Out-Null
}

# Markdown report
$mdPath = Join-Path $exportDir "WoP_Atlas_Export_$monthTag.md"
$md | Out-File -FilePath $mdPath -Encoding utf8
Write-Host "  ✓ Markdown report: $mdPath"

# HTML report
$htmlPath = Join-Path $exportDir "WoP_Atlas_Export_$monthTag.html"
$html | Out-File -FilePath $htmlPath -Encoding utf8
Write-Host "  ✓ HTML report: $htmlPath"

# Raw YAML copies
foreach ($f in $yamlFiles) {
    $destPath = Join-Path $exportDir $f.Name
    Copy-Item -Path $f.Path -Destination $destPath -Force
    Write-Host "  ✓ YAML copy: $destPath"
}

# ── RETENTION CLEANUP ─────────────────────────────────────────────

$retentionCutoff = $now.AddMonths(-$RetentionMonths)
$existingExports = Get-ChildItem -Path $BackupRoot -Directory -Filter "atlas-export-*"
$deleted = 0

foreach ($dir in $existingExports) {
    if ($dir.Name -match 'atlas-export-(\d{4}-\d{2})') {
        try {
            $exportDate = [DateTime]::ParseExact($Matches[1], "yyyy-MM", $null)
            if ($exportDate -lt $retentionCutoff) {
                Remove-Item -Path $dir.FullName -Recurse -Force
                Write-Host "  🗑 Removed old export: $($dir.Name)"
                $deleted++
            }
        } catch {
            Write-Warning "  Could not parse date from folder: $($dir.Name)"
        }
    }
}

# ── SUMMARY ───────────────────────────────────────────────────────

Write-Host "`n═══════════════════════════════════════════════════"
Write-Host "  Export complete: $exportDir"
Write-Host "  Files: MD report, HTML report, 3 YAML copies"
if ($deleted -gt 0) { Write-Host "  Retention: removed $deleted old export(s) (>$RetentionMonths months)" }
Write-Host "═══════════════════════════════════════════════════`n"
