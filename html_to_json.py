#!/usr/bin/env python3
"""
html_to_json.py  ––  v4.7  (2025-04-29)
---------------------------------------
Scans monsters_html/*.html  (Markdown fallback monsters_md/*.md)
and writes monstersfromhtml.json with columns:

    name, cr, ac, hp, languages, type, skills, gear, source,
    hasLegendaryActions, file
"""

from __future__ import annotations

import json, pathlib, re, html
from typing import Optional

from bs4 import BeautifulSoup

# ---------- constants --------------------------------------------------------
OUT_FILE = pathlib.Path("monstersfromhtml.json")
HTML_DIR = pathlib.Path("monsters_html")
MD_DIR   = pathlib.Path("monsters_md")

SIZE_WORDS = {"tiny", "small", "medium", "large", "huge", "gargantuan"}

# Normal-form creature types (SRD list)
_CANON_TYPES = {
    t.lower(): t
    for t in (
        "Aberration", "Beast", "Celestial", "Construct", "Dragon",
        "Elemental", "Fey", "Fiend", "Giant", "Humanoid", "Monstrosity",
        "Ooze", "Plant", "Swarm", "Undead"
    )
}

# ---------- helpers ----------------------------------------------------------
def clean(txt: str | None) -> str:
    return re.sub(r"\s+", " ", html.unescape(txt or "")).strip()


def normalise(label: str) -> str:
    """Lower-case a header label & strip trailing punctuation."""
    return re.sub(r"[:–—-]\s*$", "", clean(label).lower())


_LEADING_PUNCT_RE = re.compile(r"^[\s:–—-]+\s*")
def strip_leading_punct(txt: str) -> str:
    return _LEADING_PUNCT_RE.sub("", txt)


def canonical_type(txt: str) -> str:
    """Return SRD-style capitalisation (‘Dragon’, ‘Undead’, …)."""
    key = txt.strip().lower()
    return _CANON_TYPES.get(key, txt.capitalize())


_NUM_RE = re.compile(r"\d+")
_CR_RE  = re.compile(r"([\d./]+)")

def number_only(text: str) -> str:
    m = _NUM_RE.search(text)
    return m.group(0) if m else ""


def extract_type_from_em(em_text: str) -> str:
    base = em_text.split(",", 1)[0]        # drop alignment
    tokens = [t for t in base.split() if t.lower() not in SIZE_WORDS]
    return clean(" ".join(tokens))


# ---------- HTML parser ------------------------------------------------------
def parse_html(path: pathlib.Path) -> Optional[dict]:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "lxml")

    name = clean((soup.select_one("h1, h2") or {}).get_text() or path.stem)
    rows: dict[str, str] = {}

    # table rows
    for tr in soup.find_all("tr"):
        hdr  = tr.find("th") or tr.find("td")
        data = hdr.find_next_sibling("td") if hdr else None
        if hdr and data:
            rows[normalise(hdr.get_text())] = strip_leading_punct(
                clean(data.get_text())
            )

    # bullet rows
    for li in soup.find_all("li"):
        strong = li.find("strong")
        if strong:
            label = normalise(strong.get_text())
            value = strip_leading_punct(
                clean(li.get_text().replace(strong.get_text(), ""))
            )
            rows[label] = value

    cr_raw = rows.get("cr") or rows.get("challenge rating", "")
    m      = _CR_RE.search(cr_raw)
    cr     = m.group(1) if m else ""
    if not cr:
        print(f"⚠️  {path.name}: no CR, skipped.")
        return None

    # ---- type ---------------------------------------------------------------
    type_txt = ""
    for p in soup.find_all("p"):
        ems = p.find_all("em")
        if ems:
            if len(ems) >= 2:
                type_txt = clean(ems[1].get_text())
                break
            candidate = extract_type_from_em(ems[0].get_text())
            if candidate:
                type_txt = candidate
                break
    type_txt = canonical_type(type_txt.split("(", 1)[0].strip())

    # ---- numeric & misc ------------------------------------------------------
    ac        = number_only(rows.get("armor class", ""))
    hp        = number_only(rows.get("hit points", ""))
    languages = rows.get("languages", "")
    skills    = rows.get("skills", "").replace(",", ";")
    gear      = rows.get("gear", "")                      # ← NEW

    src_raw = rows.get("source", "")
    source  = src_raw.split(" page")[0] if " page" in src_raw else src_raw
    if path.stem.endswith("_mm_2024"):
        source = "WotC SRD 5.2"

    has_leg = bool(soup.find(string=re.compile(r"\blegendary actions\b", re.I)))

    return {
        "name"               : name,
        "cr"                 : cr,
        "ac"                 : ac,
        "hp"                 : hp,
        "languages"          : languages,
        "type"               : type_txt,
        "skills"             : skills,
        "gear"               : gear,                    # ← NEW
        "source"             : source,
        "hasLegendaryActions": "Yes" if has_leg else "No",
        "file"               : path.name,
    }


# ---------- Markdown parser --------------------------------------------------
_MD_FIELD_RE = re.compile(r"^\*\*(.+?)\*\*[:,]?\s*(.+)$", re.I)
_ITALIC_RE   = re.compile(r"[_*](.+?)[_*]")

def parse_md(path: pathlib.Path) -> Optional[dict]:
    text  = path.read_text(encoding="utf-8")
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    fields: dict[str, str] = {}
    for ln in lines:
        m = _MD_FIELD_RE.match(ln)
        if m:
            fields[normalise(m.group(1))] = strip_leading_punct(m.group(2).strip())

    cr = fields.get("cr") or fields.get("challenge rating")
    if not cr:
        return None

    ac        = number_only(fields.get("armor class", ""))
    hp        = number_only(fields.get("hit points", ""))
    languages = fields.get("languages", "")
    skills    = fields.get("skills", "").replace(",", ";")
    gear      = fields.get("gear", "")                  # ← NEW

    type_txt = fields.get("type", "")
    if not type_txt and len(lines) > 1:
        itals = _ITALIC_RE.findall(lines[1])
        if itals:
            type_txt = extract_type_from_em(itals[0])
    type_txt = canonical_type(type_txt.split("(", 1)[0].strip())

    source = fields.get("source", "")
    if path.stem.endswith("_mm_2024"):
        source = "WotC SRD 5.2"
    elif " page" in source:
        source = source.split(" page")[0]

    has_leg = any("legendary actions" in ln.lower() for ln in lines)

    return {
        "name"               : clean(lines[0].lstrip("#")),
        "cr"                 : cr,
        "ac"                 : ac,
        "hp"                 : hp,
        "languages"          : languages,
        "type"               : type_txt,
        "skills"             : skills,
        "gear"               : gear,                   # ← NEW
        "source"             : source,
        "hasLegendaryActions": "Yes" if has_leg else "No",
        "file"               : path.name,
    }


# ---------- main -------------------------------------------------------------
def main(root: pathlib.Path = pathlib.Path.cwd()) -> None:
    records: list[dict] = []

    for html_file in sorted((root / HTML_DIR).glob("*.html")):
        rec = parse_html(html_file)
        if rec:
            records.append(rec)

    for md_file in sorted((root / MD_DIR).glob("*.md")):
        rec = parse_md(md_file)
        if rec:
            records.append(rec)

    OUT_FILE.write_text(
        json.dumps(records, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"✅  Wrote {len(records):,} monsters to {OUT_FILE}")


if __name__ == "__main__":
    main()
