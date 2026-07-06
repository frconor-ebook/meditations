"""Tests for process_markdown.py — the load-bearing content processor.

Covers the helpers (slugs, excerpts, descriptions, tags) and the full
conversion pipeline (front matter, ordering, prev/next, related, topics,
duplicate handling, idempotency, deletion sync). Every edge case here
corresponds to a real bug or near-miss found during the 2026-07 overhaul.
"""
import json
import os

import pytest
import yaml

from process_markdown import (
    convert_markdown_to_meditations,
    make_description,
    make_excerpt,
    make_slug,
    remove_duplicate_title_lines,
    sanitize_title,
    slugify_tag,
    tags_for,
)


# ---------------------------------------------------------------- helpers

# NOTE: like the real pandoc output, each paragraph is ONE physical line —
# make_excerpt's boilerplate detection relies on that (a hand-wrapped
# multi-line italic prayer would leak into excerpts).
BOILERPLATE = """
By Fr. Conor Donnelly

(*Proofread*)

*In the name of the Father, and of the Son, and of the Holy Spirit. Amen.*

*My Lord and my God, I firmly believe that you are here, that you see me, that you hear me.*
"""


def meditation_source(title, body):
    return f"# {title}\n{BOILERPLATE}\n{body}\n"


def write_corpus(source_dir, files):
    os.makedirs(source_dir, exist_ok=True)
    for name, content in files.items():
        with open(os.path.join(source_dir, name), "w") as f:
            f.write(content)


def read_front_matter(path):
    text = open(path).read()
    _, fm, body = text.split("---\n", 2)
    return yaml.safe_load(fm), body


# ---------------------------------------------------------------- unit


class TestSanitizeTitle:
    @pytest.mark.parametrize("raw,clean", [
        ("The 1^(st) Sunday", "The 1st Sunday"),
        ("The 2^(nd) Sunday", "The 2nd Sunday"),
        ("The 3^(rd) Sunday", "The 3rd Sunday"),
        ("Dec. 8^(th)", "Dec. 8th"),
    ])
    def test_ordinal_superscripts(self, raw, clean):
        assert sanitize_title(raw) == clean

    def test_plain_title_unchanged(self):
        assert sanitize_title("Humility") == "Humility"


class TestMakeSlug:
    def test_diacritics_removed(self):
        assert make_slug("St. Josemaría Escrivá (Feast, June 26th)") == \
            "st-josemaria-escriva-feast-june-26th"

    def test_apostrophes_dropped(self):
        assert make_slug("Mary of Bethany’s Authentic Love") == \
            "mary-of-bethanys-authentic-love"

    def test_hyphen_runs_collapse(self):
        assert make_slug("Walking on the Water––Faith") == \
            "walking-on-the-waterfaith"

    def test_pure_punctuation_gives_empty_slug(self):
        assert make_slug("???") == ""


class TestRemoveDuplicateTitleLines:
    def test_bold_duplicate_removed(self):
        lines = ["**Humility**\n", "Real content.\n"]
        assert remove_duplicate_title_lines(lines, "Humility") == ["Real content.\n"]

    def test_italic_duplicate_removed(self):
        lines = ["*Humility*\n", "Real content.\n"]
        assert remove_duplicate_title_lines(lines, "Humility") == ["Real content.\n"]

    def test_plain_duplicate_with_punctuation_removed(self):
        lines = ["Martha, Martha!\n", "Real content.\n"]
        assert remove_duplicate_title_lines(lines, "Martha, Martha") == ["Real content.\n"]

    def test_unrelated_italic_kept(self):
        lines = ["*A scripture quote.*\n"]
        assert remove_duplicate_title_lines(lines, "Humility") == lines


class TestMakeExcerpt:
    def test_skips_opening_boilerplate(self):
        lines = meditation_source("T", "St. Paul says something profound.").splitlines(True)[1:]
        excerpt = make_excerpt(lines)
        assert excerpt.startswith("St. Paul says")
        assert "Proofread" not in excerpt
        assert "In the name of the Father" not in excerpt

    def test_emphasis_markers_stripped(self):
        excerpt = make_excerpt(["He said **do this** and *do that*.\n"])
        assert excerpt == "He said do this and do that."

    def test_truncates_at_max_words_with_ellipsis(self):
        excerpt = make_excerpt(["word " * 500 + "\n"], max_words=400)
        assert len(excerpt.split()) == 400
        assert excerpt.endswith("...")

    def test_short_content_no_ellipsis(self):
        assert make_excerpt(["Short text only.\n"]) == "Short text only."

    def test_italic_paragraph_after_content_is_kept(self):
        lines = ["Plain paragraph first.\n", "\n", "*Italic quote after.*\n"]
        assert "Italic quote after." in make_excerpt(lines)


class TestMakeDescription:
    def test_short_excerpt_passthrough(self):
        assert make_description("Short.") == "Short."

    def test_truncates_on_word_boundary(self):
        desc = make_description("word " * 100)
        assert len(desc) <= 158
        assert desc.endswith("...")
        assert not desc[:-3].endswith(" ")  # cut lands on a word, not a space

    def test_strips_trailing_punctuation_before_ellipsis(self):
        text = ("a" * 150) + ", trailing"
        assert ",..." not in make_description(text)


class TestSlugifyTag:
    @pytest.mark.parametrize("tag,anchor", [
        ("Advent & Christmas", "advent-christmas"),      # must match Jekyll slugify
        ("St. Joseph", "st-joseph"),
        ("Lent, Holy Week & Easter", "lent-holy-week-easter"),
        ("Our Lady", "our-lady"),
    ])
    def test_matches_jekyll_slugify(self, tag, anchor):
        assert slugify_tag(tag) == anchor


class TestTagsFor:
    """Each case here is a real title from the corpus that once mis-tagged."""

    @pytest.mark.parametrize("title,tag,expected", [
        ("St. Mary Magdalene", "Our Lady", False),
        ("Mary, Mother of God", "Our Lady", True),
        ("The Grandfather", "Opus Dei", True),
        ("The Grandfather", "Family & Marriage", False),
        ("Christmas", "Eucharist & the Mass", False),   # \bmass\b, not substring
        ("Daily Mass", "Eucharist & the Mass", True),
        ("The Fifth Sunday of St. Joseph (2026)", "St. Joseph", True),
        ("The Parable of the Sower", "Parables", True),
        ("Children of God", "Family & Marriage", False),
        ("The Eternal High Priest", "Death & Eternal Life", False),
        ("The Eternal High Priest", "Eucharist & the Mass", True),
        ("‘Til Death Do Us Part", "Death & Eternal Life", False),
        ("‘Til Death Do Us Part", "Family & Marriage", True),
        ("Passion for Unity", "Lent, Holy Week & Easter", False),
        ("Good Friday of the Lord’s Passion", "Lent, Holy Week & Easter", True),
    ])
    def test_edge_cases(self, title, tag, expected):
        assert (tag in tags_for(title)) is expected

    def test_generic_title_untagged(self):
        assert tags_for("Aim High") == []


# ---------------------------------------------------------------- integration


@pytest.fixture
def site(tmp_path):
    """A small corpus run through the full converter."""
    source = tmp_path / "source"
    root = tmp_path / "site"
    output = root / "_meditations"
    data = root / "data"

    body = "St. Paul teaches us. " + ("More prayerful words here. " * 120)
    write_corpus(str(source), {
        "humility.ewpr.md": meditation_source("Humility", body),
        "humility-lent.ewpr.md": meditation_source("Humility (Lent)", body),
        "our-lady-of-fatima.ewpr.md": meditation_source("Our Lady of Fatima", body),
        "quoted.ewpr.md": meditation_source('The "Say" So', body),
        "no-heading.md": "Just text, no heading at all.\n",
        "notes.txt": "not markdown\n",
    })
    convert_markdown_to_meditations(str(source), str(output), str(data))
    return {"source": source, "root": root, "output": output, "data": data}


class TestConversion:
    def test_outputs_and_skips(self, site):
        files = sorted(os.listdir(site["output"]))
        assert files == [
            "humility-lent.md", "humility.md", "our-lady-of-fatima.md", "the-say-so.md",
        ]

    def test_front_matter_is_valid_yaml_even_with_quotes(self, site):
        fm, _ = read_front_matter(site["output"] / "the-say-so.md")
        assert fm["layout"] == "homily"
        assert fm["title"] == 'The "Say" So'
        assert len(fm["description"]) <= 158

    def test_reading_time(self, site):
        fm, _ = read_front_matter(site["output"] / "humility.md")
        meds = json.load(open(site["data"] / "meditations.json"))
        words = len(next(m for m in meds if m["slug"] == "humility")["content"].split())
        assert fm["reading_time"] == max(1, round(words / 200))

    def test_prev_next_chain_in_title_order(self, site):
        first, _ = read_front_matter(site["output"] / "humility.md")
        mid, _ = read_front_matter(site["output"] / "humility-lent.md")
        last, _ = read_front_matter(site["output"] / "the-say-so.md")
        assert "prev_slug" not in first and first["next_slug"] == "humility-lent"
        assert mid["prev_slug"] == "humility" and mid["next_slug"] == "our-lady-of-fatima"
        assert "next_slug" not in last

    def test_related_prefers_shared_title_words(self, site):
        fm, _ = read_front_matter(site["output"] / "humility.md")
        assert fm["related"][0]["slug"] == "humility-lent"

    def test_tags_and_topics_page_data(self, site):
        fm, _ = read_front_matter(site["output"] / "our-lady-of-fatima.md")
        assert "Our Lady" in fm["tags"]
        topics = json.load(open(site["root"] / "_data" / "topics.json"))
        our_lady = next(t for t in topics if t["tag"] == "Our Lady")
        assert our_lady["anchor"] == "our-lady"
        assert any(m["slug"] == "our-lady-of-fatima" for m in our_lady["meditations"])

    def test_search_index_minified_with_clean_excerpts(self, site):
        raw = open(site["data"] / "search_index.json").read()
        assert "\n" not in raw.strip()
        idx = json.load(open(site["data"] / "search_index.json"))
        assert set(idx[0].keys()) == {"title", "slug", "excerpt"}
        assert all(m["excerpt"].startswith("St. Paul teaches") for m in idx)

    def test_idempotent_rerun(self, site):
        before = (site["output"] / "humility.md").read_bytes()
        topics_before = (site["root"] / "_data" / "topics.json").read_bytes()
        convert_markdown_to_meditations(
            str(site["source"]), str(site["output"]), str(site["data"])
        )
        assert (site["output"] / "humility.md").read_bytes() == before
        assert (site["root"] / "_data" / "topics.json").read_bytes() == topics_before

    def test_deleted_source_disappears(self, site):
        os.remove(site["source"] / "our-lady-of-fatima.ewpr.md")
        convert_markdown_to_meditations(
            str(site["source"]), str(site["output"]), str(site["data"])
        )
        assert not (site["output"] / "our-lady-of-fatima.md").exists()
        idx = json.load(open(site["data"] / "search_index.json"))
        assert all(m["slug"] != "our-lady-of-fatima" for m in idx)

    def test_new_meditation_reported(self, site, capsys):
        write_corpus(str(site["source"]), {
            "aim-high.md": meditation_source("Aim High", "New content."),
        })
        capsys.readouterr()
        convert_markdown_to_meditations(
            str(site["source"]), str(site["output"]), str(site["data"])
        )
        out = capsys.readouterr().out
        assert "New: Aim High [UNTAGGED" in out


class TestDuplicateSlugs:
    def test_later_sorted_file_wins_with_warning(self, tmp_path, capsys):
        source = tmp_path / "source"
        root = tmp_path / "site"
        write_corpus(str(source), {
            "aaa-old-copy.md": meditation_source("Humility", "Old unproofread text."),
            "humility.rkpr.md": meditation_source("Humility", "Proofread text."),
        })
        convert_markdown_to_meditations(
            str(source), str(root / "_meditations"), str(root / "data")
        )
        out = capsys.readouterr().out
        assert "duplicate slug 'humility'" in out
        assert "Proofread text." in (root / "_meditations" / "humility.md").read_text()
        idx = json.load(open(root / "data" / "search_index.json"))
        assert len(idx) == 1
