# Top 10 Improvements — Pipeline & Website

Findings from a code review of `frcmed_full_pipeline.sh`, `process_markdown.py`,
`download_from_dropbox.py`, the Jekyll layouts/JS, and the git history.
Originally reviewed 2026-07-06; **status updated 2026-07-06** after implementation.

**Progress: 10 of 10 done.** All items implemented; one operator task remains
(Dropbox duplicate cleanup, noted at the bottom).

| # | Item | Status |
|---|------|--------|
| 1 | Replace dated `_posts` with a collection | ✅ Done |
| 2 | Remove `site.time` cache-buster | ✅ Done |
| 3 | Stop shipping the 12 MB `meditations.json` | ✅ Done |
| 4 | Fix excerpt word-concatenation bug | ✅ Done |
| 5 | Full-text ranked search with snippets | ✅ Done |
| 6 | GitHub Actions deploy, stop committing `docs/` | ✅ Done |
| 7 | Safer deploy (`git add` paths, `--force-with-lease`) | ✅ Done |
| 8 | SEO: seo-tag, sitemap, descriptions | ✅ Done |
| 9 | Corpus organization: tags, A–Z nav, related | ✅ Done |
| 10 | Fail loudly: exit codes, validation gate | ✅ Done |

---

## ✅ 1. Replace dated `_posts` with a `_meditations` collection

**Was:** `process_markdown.py` named every post `{today}-{slug}.md`, so reprocessing
created duplicates — patched over by a `deduplicate` bash step and `future: true`.

**Done** (`484d02f9`): rewrote the processor as a deterministic full rebuild into a
`_meditations/` collection (`output: true`, permalink `/homilies/:name/`). Filenames
are now `{slug}.md`. Deleted the dedupe step, `future: true`, and the manifest/merge
logic. URLs verified unchanged by diffing the built URL space. The old deletion-matching
used substring containment and never actually worked — which is how stale posts
accumulated; it's gone.

## ✅ 2. Remove the `site.time` cache-buster

**Was:** `search.js?v={{ site.time | date: '%s' }}` changed on every build, rewriting
every HTML page in `docs/` even with no content change — the main repo-bloat driver.

**Done** (`bee42faf`): pinned to a static `?v=N` string, bumped only when `search.js`
changes. No-op builds now produce empty diffs.

## ✅ 3. Stop shipping the 12 MB `meditations.json`

**Was:** regenerated, committed, and served publicly on every run; nothing on the site
used it (search uses only `search_index.json`).

**Done** (`bee42faf`): excluded from the Jekyll build and gitignored. Still generated
locally as an artifact for the URL-shortener scripts and incremental use.

## ✅ 4. Fix the word-concatenation bug in excerpts/search index

**Was:** `"".join(...)` over stripped lines glued the last word of each line to the
first word of the next ("...prayerAnd so..."). **434 of 566 excerpts** were corrupted.

**Done** (`bee42faf`): join with spaces and collapse whitespace; index regenerated.
Excerpts also now skip the shared opening boilerplate (byline, proofread marker, opening
prayers) so they start at real content — previously "Holy Spirit" matched every document
via the shared opening prayer.

## ✅ 5. Full-text, ranked search with snippets

**Was:** raw `includes()` substring match on title + first 200 words only; no ranking,
typos, or snippets.

**Done** (`168b62d5`): vendored [MiniSearch](https://lucaong.github.io/minisearch/)
(18 KB) with title boosting, prefix + fuzzy matching, AND semantics with OR fallback,
and stopword filtering. Results show highlighted snippets and a count. Index excerpts
extended to 400 words, minified (~1.3 MB raw / 0.46 MB gzipped), and lazy-loaded on first
search interaction instead of on every page view.

## ✅ 6. GitHub Actions deploy; stop committing `docs/`

**Was:** the whole build ran on a personal box and force-pushed generated HTML to `main`;
git history was ~90% build output.

**Done** (`d60dad91`, `5ce6d806`): `.github/workflows/deploy.yml` builds, runs a
validation gate, and deploys atomically via `actions/deploy-pages`. Pages source switched
to "GitHub Actions" (requires the `frconor-ebook` owner login — collaborator and workflow
tokens get 403). `docs/` is now gitignored; the pipeline commits **sources only**
(`_meditations/`, `data/`) and the push triggers CI. A content change is now a 1-file
commit instead of ~578. Actions emails on failure.

*Note:* content generation (Dropbox download, pandoc, processing) deliberately stays in
the local pipeline — the Dropbox tokens, pandoc, DocX corpus, and Telegram reporting live
there. Only build+deploy moved to CI. `actions/deploy-pages` occasionally returns a
transient "try again later"; `gh run rerun <id>` clears it.

## ✅ 7. Safer deploy: no `git add .`, no bare `--force`

**Was:** `git add .` + `git push --force origin main` — one `.gitignore` miss from
committing the `.env` Dropbox tokens, and `--force` could clobber a remote hotfix.

**Done** (`bee42faf`, then `5ce6d806`): explicit `git add` paths and
`git push --force-with-lease`. Now largely subsumed by #6 (CI does the deploy).

## ✅ 8. SEO basics: seo-tag, sitemap, per-page descriptions

**Was:** no meta descriptions, Open Graph/Twitter tags, canonical URLs, or sitemap.

**Done** (`ff4f3bdb`): added `jekyll-seo-tag` (`{% seo %}` in `default.html`) and
`jekyll-sitemap`. Each meditation gets a ~155-char `description` in front matter (from the
cleaned excerpt) and the badge icon as `og:image`, so shared links show real previews.
`robots.txt` points at the 563-URL sitemap. Titles/descriptions are JSON-escaped so quotes
can't break the YAML. Site verified in Google Search Console and sitemap submitted
(verification file `googleabc8ea00a67800ef.html` must stay in the repo).

## ✅ 9. Organize the corpus: tags, A–Z jump nav, per-meditation navigation

**Was:** the homepage was a single alphabetical list of 560 titles, and a meditation page
was a dead end — no prev/next, no related items, no reading time.

**Done** (`41ce46da`): curated title-pattern rules in `process_markdown.py` assign ~20
topics (Our Lady, saints & feast days, liturgical seasons, parables, gospel scenes,
virtues, Opus Dei, ...) — 460 of 560 meditations tagged. A generated `/topics/` page
(from `_data/topics.json`) lists every topic with a jump nav; the homepage gained an A–Z
jump bar with letter-grouped headings; each meditation page now shows reading time, topic
chips, three related meditations (scored by shared-tag rarity plus shared title words),
and prev/next links that follow the homepage order. Everything is computed in the
processor at build time — no Liquid lookups across the collection.

## ✅ 10. Fail loudly: exit codes, validation gate

**Was:** `download_from_dropbox.py` did `sys.exit(0 if result else 0)` — always 0.
Deletion matching used substring containment (deleting `faith.md` would nuke
`life-of-faith.md`). Nothing validated the build before deploy.

**Done** (`22dbc950`): download script now exits 1 on failure so the pipeline stops
instead of processing stale files. A new `validate` step (and the same check in CI) gates
deploy on: meditation count ≥ 500, search index parses and matches the collection,
built-page count matches, no empty HTML. The buggy substring deletion matching was removed
entirely with the #1 rewrite (the full rebuild has no delete step). Verified it both passes
on a good build and aborts on a sabotaged one.

---

### Done along the way (not in the original 10)

- **Favicon set** (`73a6e10a`) — `favicon.ico` + PNGs + apple-touch-icon derived from
  `logo-circ.png`, linked from `default.html`.
- **Search deploy fix** (`fc506457`) — a bare `vendor/` gitignore pattern silently dropped
  the vendored MiniSearch from the commit, 404ing live search; scoped to `/vendor/` and
  added `docs/.nojekyll`.

### Operator tasks (require account access, not code)

- **Delete two stray Dropbox duplicates** — `friendship-of-jesus.mvfpr.md` (byte-identical
  to `friendship-with-jesus.mvfpr.md`) and the non-`.rkpr` `the-harvest-is-plentiful.md`.
  The pipeline tolerates them (keeps the later/proofread one) but warns every run until
  they're removed.
- **(Optional) Google Search Console** — done: verified and sitemap submitted. Just monitor
  indexing over the coming days.
