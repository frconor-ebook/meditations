# Top 10 Improvements — Pipeline & Website

Findings from a code review of `frcmed_full_pipeline.sh`, `process_markdown.py`,
`download_from_dropbox.py`, the Jekyll layouts/JS, and the git history.
Ranked by impact. (Reviewed 2026-07-06.)

---

## 1. Stop dating posts with `datetime.now()` — it's the root cause of the duplicate-post problem

`process_markdown.py:184` names every post `{today}-{slug}.md`. Reprocess the same
source file on a different day and you get a *second* post with a new date — which is
why the pipeline needs the `deduplicate` bash step and `future: true` in `_config.yml`.
Both are patches over the symptom.

**Fix:** dates are meaningless for this content, so drop `_posts` entirely and use a
Jekyll **collection** (`_meditations/` with `output: true`). Filenames become just
`{slug}.md`, URLs stay `/homilies/:slug/`, and the dedupe step, the date-sort hack,
and `future: true` all get deleted. ~1 hour of work, removes a whole failure class.

## 2. Remove the `site.time` cache-buster — every build rewrites all ~600 pages

`_layouts/default.html:72` loads `search.js?v={{ site.time | date: '%s' }}`. The build
timestamp changes on every run, so **every HTML file in `docs/` changes on every daily
build even when no content changed**. That's exactly what the "Automated daily update"
commits show: 600+ files, 2 lines each. This is the main driver of repo bloat (pack is
already **343 MiB**) and makes real content changes impossible to spot in diffs.

**Fix:** version by content, not by build time — e.g. hardcode `?v=3` and bump when
`search.js` actually changes, or inject a hash of the file. One-line change, and
no-op daily runs become genuinely empty commits (which then get skipped).

## 3. Stop shipping the 12 MB `meditations.json` — nothing uses it

`grep` shows no JS, include, or layout references `data/meditations.json`; search uses
only the 672 KB `search_index.json`. The 12 MB file is regenerated, committed, and
copied into `docs/` (so GitHub Pages serves it publicly) on every run — pure dead
weight in git history and a free bulk-download of the entire corpus.

**Fix:** stop writing it into the site (exclude from build + `.gitignore` it), or stop
generating it. Keep it as a local artifact only if the URL-shortener scripts need it.

## 4. Fix the word-concatenation bug in excerpts/search index

`process_markdown.py:209-211` builds the content with
`"".join([line.rstrip("\r\n") for line in content_lines])` — joining on the **empty
string**, so the last word of each source line is glued to the first word of the next
("...prayer**And** so..."). Every excerpt and every search-index entry is corrupted at
line boundaries, which silently breaks searches for phrases that span lines.

**Fix:** join with `"\n"` (or `" "`), then normalize whitespace. Regenerate the index
with `--force` afterward.

## 5. Upgrade search: full-text, ranked, with snippets

`assets/js/search.js` does a raw `includes()` substring match on title + the first
200 words only. Anything mentioned after word 200 of a meditation is unfindable; there
is no ranking, no typo tolerance, no result snippets, and results are plain title links.

**Fix:** drop in a tiny client-side engine — [MiniSearch](https://lucaong.github.io/minisearch/)
or Fuse.js (~10 KB) — over a fuller index (title + content, or title + a larger
excerpt). Add highlighted snippets and a result count. This is the single biggest
user-facing win for a 565-document reference site.

## 6. Move the pipeline to GitHub Actions and stop committing `docs/`

The whole build runs on a personal box via cron and force-pushes generated HTML to
`main`. If the box dies, updates stop; failures are silent; and git history is 90%
build output.

**Fix:** a scheduled GitHub Actions workflow that (a) downloads from Dropbox using a
repo secret, (b) runs convert/process, (c) builds Jekyll, and (d) publishes with
`actions/deploy-pages` — so `docs/` never touches git again. Only source markdown and
`_posts`/`_meditations` get committed. You get failure emails from Actions for free,
and the force-push problem (see #7) disappears entirely.

## 7. Make deploy safer: no `git add .`, no bare `--force`

`frcmed_full_pipeline.sh:631,655` does `git add .` then `git push --force origin main`.
Two risks: `git add .` will commit any stray file in the tree the moment `.gitignore`
misses it (the `.env` with Dropbox tokens is one typo away), and bare `--force`
overwrites anything on the remote, including a hotfix pushed from another machine.

**Fix:** add explicit paths (`git add _posts data docs assets _layouts ...`) and use
`git push --force-with-lease`. Two-line change. (Superseded by #6 if you adopt Actions.)

## 8. Add SEO basics: `jekyll-seo-tag`, sitemap, per-page descriptions

Pages have no meta description, no Open Graph/Twitter tags, no canonical URL, and
there's no `sitemap.xml` — for a content site whose whole purpose is being found and
shared, this is leaving traffic on the table. The excerpts needed for descriptions
already exist in the JSON index.

**Fix:** add `jekyll-seo-tag` + `jekyll-sitemap` to the Gemfile/config, emit
`description: {excerpt}` into each post's front matter in `process_markdown.py`, and
put `{% seo %}` in `default.html`. Shared links (WhatsApp etc. via your share buttons)
will then show real previews.

## 9. Organize the corpus: tags, A–Z jump nav, and per-meditation navigation

The homepage is a single alphabetical list of 565 titles, and a homily page is a dead
end (`_layouts/homily.html` is just title + content — no prev/next, no related items,
no reading time). The content has obvious natural facets: liturgical season, feast
days, saints, virtues, parables.

**Fix:** add a `tags:` field during processing (even a simple keyword→tag mapping on
titles gets you 80% there), render tag pages, add an A–Z jump bar on the index, and
give `homily.html` prev/next links, estimated reading time, and 3–5 "related
meditations" (shared tag). Turns a lookup table into something browsable.

## 10. Make the pipeline fail loudly: exit codes, validation, notifications

Several failures are currently invisible:
- `download_from_dropbox.py:401` — `sys.exit(0 if result else 0)` is **always 0**, so
  the pipeline can't distinguish "downloaded" from "failed".
- Broad `except Exception` blocks in the download/processing scripts print and continue.
- Post-deletion matching (`process_markdown.py:123`) uses substring containment
  (`base_name in post_file`), so deleting `faith.md` would also remove
  `life-of-faith.md`'s post.
- Nothing validates the build before deploy.

**Fix:** return real exit codes; make deletion matching exact
(`post_file.endswith(f"-{base_name}.md")` only); and add a pre-deploy sanity gate to
the pipeline — post count within expected range, both JSON files parse, no zero-byte
HTML in `docs/`. With #6, a failed gate becomes a failed Actions run that emails you.

---

### Suggested order of attack

Quick wins first: **#2, #3, #4, #7** are each under an hour and stop ongoing damage
(repo bloat, corrupt index, deploy risk). Then **#5** (search) for the biggest user
win, **#1** (collection) to simplify the pipeline, **#6 + #10** to make automation
trustworthy, and **#8 + #9** as the polish pass.
