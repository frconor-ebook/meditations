# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Jekyll-based website for Fr. Conor Donnelly Meditations, deployed to GitHub Pages at `https://frconor-ebook.github.io/meditations/`. The site displays a collection of meditation texts that are processed from DocX files downloaded from Dropbox.

## Common Commands

### Full Pipeline (Download, Process, Build, Deploy)
```bash
./frcmed_full_pipeline.sh
```

### Build and Deploy Only
```bash
./frcmed_full_pipeline.sh --include-step build,deploy
```

### Local Development Server
```bash
bundle exec jekyll serve
# Visit http://127.0.0.1:4000/meditations/
```

### Build Only (No Deploy)
```bash
./frcmed_full_pipeline.sh --skip-step deploy
```

### Custom Commit Message
```bash
./frcmed_full_pipeline.sh --include-step build,deploy -m "Your commit message"
```

## Architecture

### Content Pipeline

The pipeline transforms source DocX files into a Jekyll website:

1. **Download** (`download_from_dropbox.py`): Fetches DocX files from Dropbox using OAuth with refresh token
2. **Convert** (`preprocessing_scripts/convert_all_to_md_with_progress_parallel.sh`): Converts DocX to Markdown using pandoc
3. **Standardize** (`preprocessing_scripts/standardize_filename.py`): Normalizes filenames (lowercase, removes diacritics, replaces spaces with hyphens)
4. **Process** (`process_markdown.py`):
   - Converts Markdown files to Jekyll posts in `_posts/`
   - Generates `data/meditations.json` (full index) and `data/search_index.json` (lightweight search)
   - Extracts title from first heading, creates URL slugs
5. **Build**: Jekyll builds to `docs/` directory
6. **Deploy**: Git commit and push to GitHub

### Directory Structure

- `_posts/`: Generated Jekyll posts (auto-generated, do not edit directly)
- `_layouts/`: Jekyll layouts (`homily.html` for meditation posts, extends `default.html`)
- `_includes/`: Shared components (header, footer, search, share-links)
- `data/`: JSON index files for search functionality
- `docs/`: Jekyll build output (GitHub Pages serves from here)
- `preprocessing_scripts/`: Python/shell scripts for content processing
- `assets/`: CSS and JavaScript files

### Key Configuration

- Jekyll config: `_config.yml`
- Base URL: `/meditations` (important for all asset paths)
- Permalink structure: `/homilies/:title/`
- Build destination: `./docs`

### URL Shortening (Optional)

Scripts in `preprocessing_scripts/` for creating short URLs via TinyURL API:
- `process_and_shorten.py`: Main orchestrator
- `create_long_urls.py`: Generates URLs from meditation slugs
- `shorten_urls.py`: Creates short URLs using TinyURL and Groq APIs

## Environment Variables

Required in `.env` for Dropbox integration:
- `DROPBOX_REFRESH_TOKEN`: Long-lived token for Dropbox API access
