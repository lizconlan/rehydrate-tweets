# AGENTS

This repository is partly a historical record of an older Twitter rehydration pipeline and partly an actively useful local archive viewer. Agents should treat the local viewer workflow as the default area for safe, practical improvements unless the task explicitly targets the old AWS or Localstack code.

## Current priority

The most maintainable part of the repo is the local archive viewer in `viewer/`.

The viewer already supports:

- Browsing a local archive of hydrated tweets
- Search, account filtering, date filtering, and pagination
- Imported subset data marked as `Imported`
- Detail views via `tweet.html`

Do not describe the viewer as hypothetical or not-yet-built. Prefer iterative improvements over rewrites.

## Key files

- `viewer/index.html`: archive list UI shell
- `viewer/tweet.html`: single-tweet detail entry point
- `viewer/app.js`: client-side state, filtering, pagination, routing, and rendering
- `viewer/styles.css`: shared styling for the viewer
- `viewer/build_viewer_data.py`: scans the repo for hydrated tweet JSON, normalises it, and writes browser-ready files into `viewer/downloads/`
- `viewer/import_archive_subset.py`: imports a curated subset from a larger archive into `viewer/downloads/managed/` and rebuilds the manifest
- `README.md`: current project status and the supported local commands
- `Makefile`: the canonical entry points for refreshing and launching the viewer

## Working rules

- Preserve the current product direction: a lightweight local tweet archive viewer with visual nods to Gmail and Google Reader.
- Prefer small, surgical changes that keep the existing HTML, CSS, and vanilla JavaScript structure understandable.
- Keep the viewer local-first. Do not introduce server dependencies unless the task explicitly calls for them.
- Treat `viewer/downloads/` as generated or imported data. Do not hand-edit archive data files unless the task is specifically about fixtures or repair.
- When changing viewer behavior, preserve existing query-parameter flows where possible, especially `account`, `tweet_id`, and `page`.
- Keep support for both cached and managed/imported tweets. The `source_kind === "managed"` path is user-visible in the UI.
- Be careful not to regress the inbox-style browsing flow: fast filtering, stable pagination, and direct linking matter more than adding new abstractions.

## Commands

Use these repo-level commands instead of inventing new workflows:

- `make refresh-viewer-data`: rebuild the viewer cache from hydrated tweet JSON already present in the repo
- `make launch-archive-viewer`: rebuild the cache and open the archive browser
- `make import-viewer-subset SOURCE=/path/to/archive-or-raw_data`: import a curated subset from a larger archive
- `make launch-tweet-viewer TWEET_ID=<id>`: launch the single-tweet viewer for a specific tweet when the old localstack-based data path is available

If you change the manifest shape or import/build logic, rerun `make refresh-viewer-data`.

## Data model notes

- The archive manifest lives at `viewer/downloads/index.json`.
- Individual tweet payloads are written as `viewer/downloads/<tweet_id>.json`.
- Managed imported data lives under `viewer/downloads/managed/`.
- Media and profile images may resolve from local downloaded assets or original URLs, so changes should preserve graceful fallback behavior.

## Editing guidance

- Prefer improving the existing code over introducing a framework.
- Match the repo's tone: pragmatic, local, and lightly documented rather than overly formal.
- Add comments only where they save real reader effort.
- If you touch copy, keep it accurate about the current state of the project. The viewer is real and working; the original AWS pipeline is historical and may not be runnable unchanged.

## Verification

There is very little formal test coverage here. For viewer-facing changes, do the most relevant lightweight verification available:

- Run `make refresh-viewer-data` for data pipeline changes
- Launch the viewer when practical for UI changes
- Check that search, filters, pagination, and tweet detail loading still work

When you cannot run a full verification step, say what you did verify and what remains unverified.
