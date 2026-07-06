import argparse
import os
import re
import json
import shutil
import unicodedata


def sanitize_title(title):
    """
    Sanitize title by removing Word-style superscript notation.
    Converts patterns like 2^(nd), 10^(th), 26^(th) to 2nd, 10th, 26th
    """
    # Replace common ordinal superscripts
    title = re.sub(r'(\d+)\^\(st\)', r'\1st', title)  # 1^(st) -> 1st
    title = re.sub(r'(\d+)\^\(nd\)', r'\1nd', title)  # 2^(nd) -> 2nd
    title = re.sub(r'(\d+)\^\(rd\)', r'\1rd', title)  # 3^(rd) -> 3rd
    title = re.sub(r'(\d+)\^\(th\)', r'\1th', title)  # 4^(th) -> 4th

    return title


def make_slug(title):
    """Create a URL slug from a title (lowercase, no diacritics, hyphenated)."""
    slug = title.lower()
    slug = unicodedata.normalize("NFKD", slug)
    slug = re.sub(r"[\u0300-\u036f]", "", slug)  # Remove combining diacritics
    slug = re.sub(r"[^\w\s-]", "", slug).replace(
        " ", "-"
    )  # Keep word chars, spaces and hyphens
    slug = re.sub(r"[-]+", "-", slug)  # Remove duplicate hyphens
    return slug.strip("-")


def remove_duplicate_title_lines(lines, title):
    """
    Remove lines that are duplicate bold versions of the title.
    Handles patterns like **Title**, *Title*, or just Title on its own line.
    """
    # Normalize title for comparison (remove punctuation, lowercase)
    def normalize(text):
        text = re.sub(r'[^\w\s]', '', text.lower())
        return ' '.join(text.split())

    normalized_title = normalize(title)
    filtered_lines = []

    for line in lines:
        stripped = line.strip()

        # Check for bold title: **Title** or __Title__
        bold_match = re.match(r'^(\*\*|__)(.+?)(\*\*|__)$', stripped)
        if bold_match:
            potential_title = bold_match.group(2).strip()
            if normalize(potential_title) == normalized_title:
                continue  # Skip this duplicate title line

        # Check for italic title that matches exactly: *Title*
        italic_match = re.match(r'^\*([^*]+)\*$', stripped)
        if italic_match:
            potential_title = italic_match.group(1).strip()
            if normalize(potential_title) == normalized_title:
                continue  # Skip this duplicate title line

        # Check for plain text title (no formatting) that matches exactly
        if stripped and normalize(stripped) == normalized_title:
            continue  # Skip this duplicate title line

        filtered_lines.append(line)

    return filtered_lines


def make_excerpt(content_lines, max_words=400):
    """
    Build the search/display excerpt for a meditation.

    Skips the standard opening boilerplate every meditation shares (byline,
    proofread marker, italic opening prayers) so excerpts start at the real
    content, strips emphasis markers for clean snippets, and truncates.
    """
    def is_boilerplate(paragraph):
        if paragraph.lower().startswith("by fr"):
            return True
        if paragraph.strip("*() ").lower() == "proofread":
            return True
        # Fully-italicized paragraph at the head = opening prayer
        if paragraph.startswith("*") and paragraph.endswith("*"):
            return True
        return False

    paragraphs = [line.strip() for line in content_lines if line.strip()]
    body = []
    skipping = True
    for paragraph in paragraphs:
        if skipping and is_boilerplate(paragraph):
            continue
        skipping = False
        body.append(paragraph)

    text = re.sub(r"[*_]+", "", " ".join(body))
    words = text.split()
    excerpt = " ".join(words[:max_words])
    if len(words) > max_words:
        excerpt += "..."
    return excerpt


def make_description(excerpt, max_chars=155):
    """Meta description: excerpt truncated to ~max_chars on a word boundary."""
    if len(excerpt) <= max_chars:
        return excerpt
    cut = excerpt.rfind(" ", 0, max_chars)
    if cut == -1:
        cut = max_chars
    return excerpt[:cut].rstrip(".,;:") + "..."


# Topic tags assigned by matching regex patterns against the lowercased
# title: (tag, [include patterns], [exclude patterns]). A meditation gets a
# tag when any include pattern matches and no exclude pattern does. Curated
# for this corpus; imperfect matches are acceptable — tags are navigation
# aids, not taxonomy.
TAG_RULES = [
    ("Our Lady", [
        r"our lady", r"our mother", r"\bmary,", r"mary mother", r"of mary\b",
        r"and mary\b", r"through mary", r"annunciation", r"assumption",
        r"visitation", r"magnificat", r"rosary", r"immaculate",
        r"mother of god", r"mother of fair love", r"mother of the church",
        r"seven sorrows",
    ], [r"magdalene", r"bethany", r"martha", r"mary major"]),
    ("St. Joseph", [r"joseph"], []),
    ("Saints & Feast Days", [
        r"\bst\.", r"\bsts\.", r"all saints", r"archangel", r"guardian angel",
        r"martyr", r"blessed guadalupe", r"blessed [aá]lvaro", r"newman",
    ], []),
    ("Opus Dei", [
        r"josemar[ií]a", r"escriv[aá]", r"prelate", r"prelature",
        r"[aá]lvaro del portillo", r"guadalupe ortiz", r"aunt carmen",
        r"the grandfather", r"the grandmother", r"in the work",
        r"don fernando", r"oc[aá]riz", r"priestly society",
    ], []),
    ("Advent & Christmas", [
        r"advent", r"christmas", r"bethlehem", r"epiphany", r"manger",
        r"holy innocents", r"shepherds", r"wise men", r"adoration of the kings",
        r"\bnativity", r"simeon", r"incarnation", r"come, lord jesus",
        r"expectation", r"waiting for", r"prince of peace", r"caesar augustus",
    ], [r"nativity of our lady"]),
    ("Lent, Holy Week & Easter", [
        r"\blent\b", r"\(lent\)", r"ash wednesday", r"palm sunday",
        r"holy thursday", r"good friday", r"holy saturday", r"easter",
        r"resurrection", r"crucifixion", r"\bpassion\b", r"calvary",
        r"good thief", r"washing of the feet", r"emmaus", r"i thirst",
        r"\bjudas\b", r"ascension",
    ], [r"passion for"]),
    ("The Cross & Suffering", [
        r"\bcross", r"calvary", r"crucifixion", r"illness", r"\bsick\b",
        r"adversity", r"setbacks", r"low moments", r"crises",
    ], []),
    ("Holy Spirit", [
        r"holy spirit", r"pentecost", r"the gift of ",
    ], [r"gift of god"]),
    ("Eucharist & the Mass", [
        r"eucharist", r"\bmass\b", r"communion", r"corpus christi",
        r"bread of life", r"bread our", r"real presence", r"precious blood",
        r"high priest", r"body and blood", r"it is right and just",
    ], [r"communion of saints"]),
    ("Confession & Mercy", [
        r"confession", r"contrition", r"\bmercy\b", r"merciful",
        r"forgiveness", r"prodigal son", r"friend of sinners", r"our sins",
        r"caught in adultery",
    ], []),
    ("Prayer & Interior Life", [
        r"prayer", r"contemplat", r"presence of god", r"plan of life",
        r"examination of conscience", r"spiritual direction", r"retreat",
        r"\binterior\b", r"thanksgiving", r"divine intimacies", r"abandonment",
        r"divine filiation", r"spiritual childhood", r"life of childhood",
        r"our father god", r"learning to ask", r"aspirations", r"listening",
    ], []),
    ("Virtues & Struggle", [
        r"humility", r"charity", r"\bfaith", r"\bhope\b", r"patience",
        r"obedience", r"temperance", r"prudence", r"fortitude", r"sincerity",
        r"loyalty", r"generosity", r"cheerfulness", r"optimism", r"kindness",
        r"meek", r"magnanimity", r"perseverance", r"\border\b", r"virtue",
        r"self-denial", r"mortification", r"self-love", r"lukewarmness",
        r"tepidity", r"detachment", r"poverty", r"\bpurity", r"chastity",
        r"freedom", r"docility", r"simplicity", r"naturalness", r"justice",
        r"responsibility", r"temptation", r"struggle", r"vigilance",
        r"watchfulness", r"gratitude", r"fraternal correction",
    ], []),
    ("Family & Marriage", [
        r"marriage", r"conjugal", r"\bfamily\b", r"children", r"mother.s day",
        r"father.s day", r"great mothers", r"domestic church", r"til death",
        r"education",
    ], [r"children of god"]),
    ("Parables", [
        r"parable", r"prodigal son", r"good samaritan", r"lost sheep",
        r"house on the rock", r"grain of wheat", r"unmerciful servant",
        r"useless servants", r"narrow gate", r"narrow path", r"salt and light",
        r"salt that", r"grass of the field", r"sparrows",
        r"pharisee and the publican",
    ], []),
    ("Gospel Scenes & Miracles", [
        r"healing", r"curing", r"cure of", r"miracle", r"miraculous",
        r"multiplication", r"bartimaeus", r"centurion", r"blind man",
        r"paralytic", r"possessed", r"unclean spirit", r"lepers", r"jairus",
        r"issue of blood", r"bent over woman", r"syrophoenician",
        r"widow of naim", r"widow.s mite", r"storm on the lake",
        r"walking on the water", r"raising of lazarus", r"\bcana\b",
        r"pool at", r"temple tax", r"first disciples", r"good shepherd",
        r"transfiguration", r"martha, martha",
    ], []),
    ("Apostolate", [
        r"apostolate", r"fishers of men", r"evangeli", r"salt and light",
        r"salt that", r"fire on earth", r"cast fire", r"raise the world",
        r"harvest", r"ripples", r"bridge-builder", r"helping to do good",
        r"infectious faith", r"light of the world", r"loving the world",
        r"human respect", r"friendship and confidence", r"\bzeal\b",
    ], []),
    ("Work & Ordinary Life", [
        r"\bwork\b", r"worker", r"professional", r"\bstudy\b",
        r"little things", r"little duties", r"ordinary life", r"today.s task",
        r"use of time", r"lost time", r"sanctification", r"unity of life",
        r"artisan", r"carpenter", r"\brest\b",
    ], [r"in the work"]),
    ("Death & Eternal Life", [
        r"\bdeath", r"\beternal", r"heaven", r"\bhell\b", r"purgatory",
        r"all souls", r"pray for the dead", r"end of life", r"last day",
    ], [r"til death", r"high priest"]),
    ("Church & Priesthood", [
        r"\bpope\b", r"\bchurch\b", r"priest", r"\bpeter\b",
        r"unity of christians", r"laity", r"jubilee", r"communion of saints",
    ], []),
    ("Vocation", [r"vocation", r"discerning", r"to serve", r"spirit of service"], []),
]


def slugify_tag(tag):
    """Anchor id for a tag — must match Jekyll's `slugify` filter output."""
    return re.sub(r"[^a-z0-9]+", "-", tag.lower()).strip("-")


def tags_for(title):
    """Tags whose include patterns match the title (and excludes don't)."""
    t = title.lower()
    tags = []
    for tag, includes, excludes in TAG_RULES:
        if any(re.search(p, t) for p in includes) and not any(
            re.search(p, t) for p in excludes
        ):
            tags.append(tag)
    return tags


def convert_markdown_to_meditations(source_dir, output_dir, data_dir):
    """
    Converts all source markdown files to Jekyll collection documents in
    _meditations/ and (re)creates the JSON indexes.

    This is a full rebuild on every run: filenames are slug-based (no dates),
    so output is deterministic — unchanged sources produce byte-identical
    files, and deletions/renames in the source folder sync automatically.

    Two passes: first parse every source file, then (once the full sorted
    list is known) compute tags, reading time, prev/next and related
    meditations, and write the collection documents with that front matter.
    """
    # Start clean so removed/renamed sources disappear from the site
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)

    meditations = []
    slug_sources = {}

    for filename in sorted(os.listdir(source_dir)):
        if not filename.endswith(".md"):
            continue
        filepath = os.path.join(source_dir, filename)

        with open(filepath, "r") as f:
            lines = f.readlines()

        title_line_index = -1
        for i, line in enumerate(lines):
            if line.rstrip("\r\n").lstrip().startswith("#"):
                title_line_index = i
                break

        if title_line_index == -1:
            print(f"Skipping {filename} (no title found).")
            continue

        title = lines[title_line_index].rstrip("\r\n").lstrip("# ").strip()
        title = sanitize_title(title)  # Sanitize Word-style superscripts

        slug = make_slug(title)
        if not slug:
            print(
                f"Skipping {filename}: heading '{title}' produced an empty slug. "
                f"Fix the source file's first '#' heading."
            )
            continue

        if slug in slug_sources:
            # Two source files produce the same slug (e.g. a stray copy in
            # Dropbox). Keep the later one (sorted order) so the choice is
            # deterministic, and warn so the stray can be cleaned up.
            print(
                f"WARNING: duplicate slug '{slug}': {filename} replaces "
                f"{slug_sources[slug]}. Remove the stray copy from Dropbox."
            )
            meditations = [m for m in meditations if m["slug"] != slug]
        slug_sources[slug] = filename

        # Get content lines (after the title) and clean up
        content_lines = lines[title_line_index + 1 :]
        content_lines = remove_duplicate_title_lines(content_lines, title)

        # Get full content (join lines with spaces, collapse whitespace)
        full_content = " ".join(
            "\n".join(line.rstrip("\r\n") for line in content_lines).split()
        )

        meditations.append(
            {
                "title": title,
                "slug": slug,
                "content": full_content,
                "excerpt": make_excerpt(content_lines),
                "content_lines": content_lines,
            }
        )

    # Sort by title — matches the homepage's Liquid `sort: "title"` order,
    # so prev/next navigation follows the listing the reader came from
    meditations.sort(key=lambda x: x["title"])

    # Enrich: tags, reading time, then related (weighted by tag rarity so a
    # shared niche tag counts for more than a shared broad one)
    for m in meditations:
        m["tags"] = tags_for(m["title"])
        m["reading_time"] = max(1, round(len(m["content"].split()) / 200))

    tag_counts = {}
    for m in meditations:
        for tag in m["tags"]:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    def title_words(title):
        stop = {"the", "and", "for", "our", "with", "his", "her", "you"}
        return {
            w for w in re.findall(r"[a-z]+", title.lower())
            if len(w) > 3 and w not in stop
        }

    for m in meditations:
        own_tags = set(m["tags"])
        own_words = title_words(m["title"])
        scored = []
        for other in meditations:
            if other is m:
                continue
            shared_tags = own_tags & set(other["tags"])
            shared_words = own_words & title_words(other["title"])
            if shared_tags or shared_words:
                # Rare shared tags count more than broad ones; shared title
                # words (e.g. both about "humility") outrank tag-only matches
                weight = sum(1.0 / tag_counts[t] for t in shared_tags)
                weight += 0.5 * len(shared_words)
                scored.append((-weight, other["title"], other))
        scored.sort(key=lambda x: (x[0], x[1]))
        m["related"] = [
            {"slug": o["slug"], "title": o["title"]} for _, _, o in scored[:3]
        ]

    # Write the collection documents
    for i, m in enumerate(meditations):
        # json.dumps produces valid YAML double-quoted strings, so titles or
        # descriptions containing quotes cannot break the front matter
        fm = [
            "---",
            "layout: homily",
            f"title: {json.dumps(m['title'])}",
            f"description: {json.dumps(make_description(m['excerpt']))}",
            f"reading_time: {m['reading_time']}",
        ]
        if m["tags"]:
            fm.append(f"tags: {json.dumps(m['tags'])}")
        if i > 0:
            fm.append(f"prev_slug: {meditations[i - 1]['slug']}")
            fm.append(f"prev_title: {json.dumps(meditations[i - 1]['title'])}")
        if i < len(meditations) - 1:
            fm.append(f"next_slug: {meditations[i + 1]['slug']}")
            fm.append(f"next_title: {json.dumps(meditations[i + 1]['title'])}")
        if m["related"]:
            fm.append(f"related: {json.dumps(m['related'])}")
        fm.append("---")

        with open(os.path.join(output_dir, f"{m['slug']}.md"), "w") as f:
            f.write("\n".join(fm) + "\n")
            f.writelines(
                [line.rstrip("\r\n") + "\n" for line in m["content_lines"]]
            )
        del m["content_lines"]
        del m["related"]

    os.makedirs(data_dir, exist_ok=True)

    # Topics index for the /topics/ page (_data/ is read by Jekyll as site.data)
    topics = []
    for tag, _, _ in TAG_RULES:
        items = [
            {"title": m["title"], "slug": m["slug"]}
            for m in meditations
            if tag in m["tags"]
        ]
        if items:
            topics.append(
                {"tag": tag, "anchor": slugify_tag(tag), "meditations": items}
            )
    data_underscore_dir = os.path.join(os.path.dirname(output_dir), "_data")
    os.makedirs(data_underscore_dir, exist_ok=True)
    topics_path = os.path.join(data_underscore_dir, "topics.json")
    with open(topics_path, "w") as f:
        json.dump(topics, f, indent=1)
    print(f"Created: {topics_path} ({len(topics)} topics)")

    # Full index: local artifact only (gitignored), used by the URL-shortener
    meditations_json_path = os.path.join(data_dir, "meditations.json")
    with open(meditations_json_path, "w") as f:
        json.dump(meditations, f, indent=2)
    print(f"Created: {meditations_json_path}")

    # Lightweight search index (title, slug, excerpt only), shipped to visitors
    search_index = [
        {"title": m["title"], "slug": m["slug"], "excerpt": m["excerpt"]}
        for m in meditations
    ]
    search_index_path = os.path.join(data_dir, "search_index.json")
    with open(search_index_path, "w") as f:
        # Minified: this file is shipped to every visitor who searches
        json.dump(search_index, f, separators=(",", ":"))
    print(f"Created: {search_index_path}")

    print(f"Processed {len(meditations)} meditations.")


# --- Main execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process source markdown files into the Jekyll meditations collection."
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="No-op, kept for pipeline compatibility (processing always rebuilds fully)"
    )
    parser.parse_args()

    # Get the directory where this script is located (meditations/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Parent directory is upload_frcmed_to_web (one level up from meditations)
    parent_dir = os.path.dirname(script_dir)

    source_directory = os.path.join(parent_dir, "transcript_proofread_std_markdown")
    output_directory = os.path.join(script_dir, "_meditations")
    data_directory = os.path.join(script_dir, "data")

    print(f"Source Directory: {source_directory}")
    print(f"Output Directory: {output_directory}")
    print(f"Data Directory: {data_directory}")

    convert_markdown_to_meditations(
        source_directory, output_directory, data_directory
    )
