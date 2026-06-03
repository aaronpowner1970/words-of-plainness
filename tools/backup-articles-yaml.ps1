# backup-articles-yaml.ps1
#
# Snapshots the two source-of-truth files for the Articles of Interfaith
# Discipleship cluster:
#   1. articles_citations.yaml         (citation apparatus)
#   2. Articles_of_Interfaith_Discipleship.docx.md  (canonical Articles document)
#
# Snapshots are timestamped and include the source file size in the filename
# so directory listings show file growth over time at a glance.
#
# Destination: C:\Users\aaron\Documents\working-folder\wop-backup\citation-yaml-snapshots\
#
# Retention: Keep all snapshots forever. Files are small (~286 KB + ~17 KB
# at Session 13 baseline). Even hundreds of snapshots remain trivial on disk.
# To enable retention pruning later, see the commented block at the end.
#
# Usage: From PowerShell, run:
#   .\tools\backup-articles-yaml.ps1
#
# Established: Session 13 (May 1, 2026) -- Measure 2 of source-of-truth
# durability stabilization. See Architecture_Decision_Articles_Runtime.md
# for related Measure 1.

$ErrorActionPreference = "Stop"

# --- Source files ---
$ClusterFolder = "C:\Users\aaron\Documents\working-folder\Articles_of_Interfaith_Discipleship_Essay_Cluster"
$YamlSource    = Join-Path $ClusterFolder "articles_citations.yaml"
$ArticlesSource = Join-Path $ClusterFolder "Articles_of_Interfaith_Discipleship.docx.md"

# --- Snapshot destination ---
$SnapshotFolder = "C:\Users\aaron\Documents\working-folder\wop-backup\citation-yaml-snapshots"

# --- Verify source files exist ---
if (-not (Test-Path $YamlSource)) {
    Write-Error "Source YAML not found: $YamlSource"
    exit 1
}
if (-not (Test-Path $ArticlesSource)) {
    Write-Error "Source Articles document not found: $ArticlesSource"
    exit 1
}

# --- Ensure snapshot folder exists ---
if (-not (Test-Path $SnapshotFolder)) {
    New-Item -ItemType Directory -Path $SnapshotFolder -Force | Out-Null
    Write-Host "Created snapshot folder: $SnapshotFolder" -ForegroundColor Cyan
}

# --- Build timestamp ---
$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"

# --- Snapshot 1: articles_citations.yaml ---
$YamlSize = (Get-Item $YamlSource).Length
$YamlDestName = "articles_citations_${Timestamp}_${YamlSize}.yaml"
$YamlDest = Join-Path $SnapshotFolder $YamlDestName
Copy-Item -Path $YamlSource -Destination $YamlDest -Force
Write-Host "Snapshotted: $YamlDestName ($YamlSize bytes)" -ForegroundColor Green

# --- Snapshot 2: Articles_of_Interfaith_Discipleship.docx.md ---
$ArticlesSize = (Get-Item $ArticlesSource).Length
$ArticlesDestName = "Articles_of_Interfaith_Discipleship_${Timestamp}_${ArticlesSize}.docx.md"
$ArticlesDest = Join-Path $SnapshotFolder $ArticlesDestName
Copy-Item -Path $ArticlesSource -Destination $ArticlesDest -Force
Write-Host "Snapshotted: $ArticlesDestName ($ArticlesSize bytes)" -ForegroundColor Green

# --- Report total snapshots in folder ---
$TotalSnapshots = (Get-ChildItem $SnapshotFolder -File).Count
Write-Host ""
Write-Host "Snapshot folder now contains $TotalSnapshots files." -ForegroundColor Cyan
Write-Host "Location: $SnapshotFolder" -ForegroundColor Cyan

# --- Optional retention pruning (DISABLED by default) ---
# Uncomment to keep only the 30 most recent snapshots per file pattern.
# Adjust $RetainCount to suit.
#
# $RetainCount = 30
# Get-ChildItem $SnapshotFolder -Filter "articles_citations_*.yaml" |
#     Sort-Object LastWriteTime -Descending |
#     Select-Object -Skip $RetainCount |
#     Remove-Item -Force
# Get-ChildItem $SnapshotFolder -Filter "Articles_of_Interfaith_Discipleship_*.docx.md" |
#     Sort-Object LastWriteTime -Descending |
#     Select-Object -Skip $RetainCount |
#     Remove-Item -Force

exit 0
