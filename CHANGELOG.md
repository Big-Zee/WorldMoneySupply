# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Newest entries appear at the top.

## [Unreleased]

## [2026-08-08]

### Changed
- Exclude `.claude/settings.local.json` from git (personal local permissions) while keeping `.claude/settings.json` committable for project-level Claude Code config

## [2026-04-23]

### Added
- Architecture diagrams to README

## [2026-04-22]

### Added
- Incremental US-only scraper (`scraper_us.py`) designed for Azure Function Timer Trigger — fetches only new data from last known date
- Scraper health audit log (`job_logger.py`) writing to `output/job_status.json` and optionally to Azure Table Storage

## [2026-04-16]

### Added
- `CLAUDE.md` with full architecture reference and command documentation
- BOJ series discovery utility (`BOJDiscoverSeries.py`) with CSV output
- Japan M2 data sourced from Bank of Japan API (`BOJDownloadSeries.py`) — removed from FRED scraper

### Changed
- README updated to document BOJ data source for Japan
- Git operations note moved into local `CLAUDE.md`

## [2026-04-15]

### Added
- Index mode toggle for normalising all series to a common base date
- Stats summary table below the chart
- Acceleration chart (MoM change-of-change)
- 12-month moving average (MA12) toggle
- Range buttons (1Y / 3Y / 5Y / All)
- Synchronised dataZoom slider across charts
- Per-country CSV output so partial scraper runs no longer clobber other countries' data

### Changed
- README updated for per-country CSV schema and ECB data source documentation

## [2026-04-08]

### Changed
- Expanded from US-only to multi-country M2 monitor (10 countries via FRED/ECB)
- Added YoY % change chart alongside raw M2 values

## [2026-03-26]

### Added
- FastAPI web UI (`app.py`) serving an ECharts dashboard at `localhost:8000`
- Project scaffolding: `requirements.txt`, `templates/index.html`, `.env.example`

## [2026-03-21]

### Added
- Initial `README.md`
