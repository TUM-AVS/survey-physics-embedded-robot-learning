#!/usr/bin/env python3
"""Load the catalog from the annotated BibTeX files in ``bib/``.

The ``bib/*.bib`` files are the source of truth. Each entry carries its normal
bibliographic fields plus ``survey_*`` annotation fields holding the survey's
labels; BibTeX ignores unknown fields, so the files stay usable as an ordinary
bibliography. See CONTRIBUTING.md for the field reference.

Pure standard library: no third-party packages are needed to read or check the
catalog.
"""
from __future__ import annotations

import re
from pathlib import Path

import taxonomy

ROOT = Path(__file__).resolve().parent.parent
BIB_DIR = ROOT / "bib"


def gh_anchor(heading: str) -> str:
    """GitHub's heading anchor: lowercase, spaces to hyphens, drop punctuation."""
    return re.sub(r"[^a-z0-9_-]+", "", heading.lower().replace(" ", "-"))


def strip_tex(s: str) -> str:
    if not s:
        return ""
    s = s.replace("\n", " ")
    s = re.sub(r"\\url\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\href\{[^}]*\}\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\[a-zA-Z]+\{", "", s)
    s = s.replace("{", "").replace("}", "")
    s = s.replace("\\&", "&").replace("\\%", "%").replace("\\_", "_")
    s = s.replace("~", " ").replace("---", "—").replace("--", "–")
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"<div></div>", "", s)
    return s.strip(" .,;")


def split_entries(text: str) -> list[tuple[str, str, str]]:
    """Return list of (entry_type, key, body)."""
    out = []
    for m in re.finditer(r"@(\w+)\s*\{", text):
        etype = m.group(1)
        i = m.end()
        # key
        key_end = text.find(",", i)
        brace = text.find("{", i)
        if key_end == -1:
            continue
        key = text[i:key_end].strip()
        if not key or "\n" in key:
            # key on next line (e.g. @inproceedings{\nkey,)
            rest = text[i:i + 80]
            km = re.match(r"\s*([A-Za-z0-9_.:-]+)\s*,", rest)
            if not km:
                continue
            key = km.group(1)
            key_end = i + km.end() - 1
        # body until matching close brace of the entry
        start = key_end + 1
        depth = 1
        j = start
        while j < len(text):
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    out.append((etype, key, text[start:j]))
                    break
            j += 1
    return out


def parse_fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    i = 0
    n = len(body)
    while i < n:
        m = re.match(r"\s*([A-Za-z][A-Za-z0-9_-]*)\s*=\s*", body[i:])
        if not m:
            i += 1
            continue
        name = m.group(1).lower()
        i += m.end()
        if i >= n:
            break
        if body[i] == "{":
            depth = 0
            j = i
            while j < n:
                if body[j] == "{":
                    depth += 1
                elif body[j] == "}":
                    depth -= 1
                    if depth == 0:
                        fields[name] = body[i + 1 : j]
                        i = j + 1
                        break
                j += 1
            else:
                break
        elif body[i] == '"':
            j = i + 1
            while j < n and body[j] != '"':
                j += 1
            fields[name] = body[i + 1 : j]
            i = j + 1
        else:
            j = i
            while j < n and body[j] not in ",\n":
                j += 1
            fields[name] = body[i:j].strip()
            i = j
    return fields


ARXIV_ID_RE = re.compile(r"^(?:arXiv:)?(\d{4}\.\d{4,5}(?:v\d+)?|[a-z\-]+/\d{7})$", re.I)
DOI_RE = re.compile(r"10\.\d{4,9}/[^\s]+")

# Some publisher exports title-case the whole venue, turning acronyms into
# "Ieee Access" or "Acm Transactions". Restore them wherever no rule above fired.
ACRONYM_CASE_RE = re.compile(
    r"\b(IEEE|ACM|IFAC|ASME|SIAM|AIAA|RSS|ICRA|IROS|CoRL|PMLR|NeurIPS|IJCAI|IET)\b",
    re.I)

VENUE_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"arxiv|corr\b", re.I), "arXiv"),
    (re.compile(r"Learning for Dynamics and Control", re.I), "L4DC"),
    (re.compile(r"Conference on Robot Learning", re.I), "CoRL"),
    (re.compile(r"Robotics:? Science and Systems", re.I), "RSS"),
    (re.compile(r"Intelligent Robots and Systems", re.I), "IROS"),
    (re.compile(r"International Conference on Robotics and Automation", re.I), "ICRA"),
    (re.compile(r"Robotics and Automation Letters", re.I), "IEEE RA-L"),
    (re.compile(r"Transactions on Robotics", re.I), "T-RO"),
    (re.compile(r"International Journal of Robotics Research", re.I), "IJRR"),
    (re.compile(r"Neural Information Processing Systems", re.I), "NeurIPS"),
    (re.compile(r"International Conference on Learning Representations", re.I), "ICLR"),
    (re.compile(r"International Conference on Machine Learning", re.I), "ICML"),
    (re.compile(r"\bICLR\b", re.I), "ICLR"),
    (re.compile(r"AAAI Conference", re.I), "AAAI"),
    (re.compile(r"Computer Vision and Pattern Recognition", re.I), "CVPR"),
    (re.compile(r"Transactions on Industrial Electronics", re.I), "TIE"),
    (re.compile(r"Transactions on Mechatronics", re.I), "T-Mech"),
    (re.compile(r"Transactions on Control Systems Technology", re.I), "TCST"),
    (re.compile(r"Automatica", re.I), "Automatica"),
]


def _http(s: str) -> str:
    return s.strip().rstrip(".,);")


def normalize_doi(raw: str) -> str | None:
    s = strip_tex(raw or "")
    for prefix in (
        "https://doi.org/",
        "http://doi.org/",
        "https://dx.doi.org/",
        "http://dx.doi.org/",
    ):
        s = s.replace(prefix, "")
    s = s.strip().split()[0] if s.strip() else ""
    s = s.rstrip(".,);")
    if s.startswith("10."):
        return s
    m = DOI_RE.search(strip_tex(raw or ""))
    return m.group(0).rstrip(".,);") if m else None


def arxiv_id(fields: dict[str, str]) -> str | None:
    eprint = strip_tex(fields.get("eprint", ""))
    if eprint and not eprint.startswith("http"):
        m = ARXIV_ID_RE.match(eprint)
        if m:
            return m.group(1)
    blob = " ".join(
        strip_tex(fields.get(k, ""))
        for k in ("url", "doi", "volume", "howpublished", "note", "eprint")
    )
    m = re.search(r"arxiv\.org/abs/([a-z\-]+/\d{7}|\d{4}\.\d{4,5}(?:v\d+)?)", blob, re.I)
    if m:
        return m.group(1)
    m = re.search(r"10\.48550/arXiv\.(\d{4}\.\d{4,5})", blob)
    if m:
        return m.group(1)
    m = re.search(r"\babs/(\d{4}\.\d{4,5})\b", blob)
    if m:
        return m.group(1)
    m = re.search(r"arXiv[:\s]+(\d{4}\.\d{4,5})", blob, re.I)
    if m:
        return m.group(1)
    return None


def paper_link(fields: dict[str, str]) -> str | None:
    url = _http(strip_tex(fields.get("url", "")))
    doi = normalize_doi(fields.get("doi", ""))
    aid = arxiv_id(fields)
    eprint = strip_tex(fields.get("eprint", ""))

    def is_dblp(u: str) -> bool:
        return "dblp.org" in u and u.endswith(".bib")

    def is_code_host(u: str) -> bool:
        return any(h in u for h in ("github.com", "gitlab.com", "bitbucket.org"))

    if url.startswith("http") and not is_dblp(url) and not is_code_host(url):
        return url
    if doi and not doi.startswith("10.48550/arXiv"):
        return f"https://doi.org/{doi}"
    if aid:
        return f"https://arxiv.org/abs/{aid}"
    if doi:
        return f"https://doi.org/{doi}"
    if eprint.startswith("http"):
        d = normalize_doi(eprint)
        if d:
            return f"https://doi.org/{d}"
        return _http(eprint)
    if url.startswith("http"):
        return url
    return None


def github_link(fields: dict[str, str]) -> str | None:
    blob = " ".join(fields.values())
    m = re.search(r"https?://(?:www\.)?github\.com/[^\s\}]+", blob)
    if m:
        return _http(m.group(0))
    return None


def venue(fields: dict[str, str]) -> str:
    v = strip_tex(
        fields.get("journal")
        or fields.get("booktitle")
        or fields.get("publisher")
        or fields.get("howpublished")
        or fields.get("school")
        or fields.get("institution")      # @techreport
        or ""
    )
    if not v:
        # Preprints often carry no venue field at all. Their identifier says where
        # they live, which is the honest answer for an unpublished paper.
        blob = " ".join(strip_tex(fields.get(k, "")) for k in ("doi", "url", "eprint")).lower()
        if arxiv_id(fields):
            return "arXiv"
        if "techrxiv" in blob or "10.36227" in blob:
            return "TechRxiv"
        if "openreview.net" in blob:
            return "OpenReview"
        if "ssrn" in blob:
            return "SSRN"
        return "—"
    if v.startswith("http"):
        if "github.com" in v:
            return "GitHub"
        return "—"
    for pat, short in VENUE_RULES:
        if pat.search(v):
            return short
    v = ACRONYM_CASE_RE.sub(lambda m: m.group(0).upper(), v)
    if len(v) > 56:
        v = v[:53] + "…"
    return v

def parse_bib_file(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="replace")
    papers = []
    seen = set()
    for etype, key, body in split_entries(text):
        if not key or key in seen:
            continue
        seen.add(key)
        fields = parse_fields(body)
        title = strip_tex(fields.get("title", ""))
        if not title:
            continue
        year = strip_tex(fields.get("year", ""))
        ym = re.search(r"(19|20)\d{2}", year)
        year_i = int(ym.group(0)) if ym else None
        papers.append(
            {
                "key": key,
                "type": etype.lower(),
                "title": title,
                "year": year_i,
                "year_raw": year or "—",
                "venue": venue(fields),
                "venue_raw": strip_tex(
                    fields.get("journal")
                    or fields.get("booktitle")
                    or fields.get("publisher")
                    or fields.get("howpublished")
                    or fields.get("school")
                    or ""
                ),
                "link": paper_link(fields),
                "code": github_link(fields),
                "file": path.name,
            }
        )
    papers.sort(key=lambda p: (p["year"] is None, p["year"] or 0, p["title"].lower()))
    return papers


def md_escape(s: str) -> str:
    return s.replace("|", "\\|").replace("[", "\\[").replace("]", "\\]")




# ------------------------------------------------------------ survey annotations ---

def split_list(raw: str) -> list[str]:
    """``{a, b}`` -> ['a', 'b']; tolerant of extra whitespace and empty values."""
    return [v.strip().lower() for v in re.split(r"[,;]", strip_tex(raw or "")) if v.strip()]


class CatalogError(Exception):
    """A survey_* field that validate.py must report."""


def annotate(paper: dict, fields: dict[str, str], problems: list[str]) -> dict:
    """Resolve the survey_* fields of one entry into the model the tools use."""
    where = f"bib/{paper['file']}: @{paper['key']}"

    def bad(msg: str) -> None:
        problems.append(f"{where}: {msg}")

    kind = strip_tex(fields.get("survey_kind", "")).strip().lower()
    if not kind:
        bad("missing survey_kind (one of: " + ", ".join(taxonomy.KINDS) + ")")
        kind = "background"
    elif kind not in taxonomy.KINDS:
        bad(f"survey_kind = {{{kind}}} is not one of: " + ", ".join(taxonomy.KINDS))
        kind = "background"

    family = strip_tex(fields.get("survey_family", "")).strip().lower()
    expected = paper["file"][:-4]
    if not family:
        bad(f"missing survey_family (expected {{{expected}}})")
        family = expected
    elif family not in taxonomy.FAMILIES:
        bad(f"survey_family = {{{family}}} is not a known family")
    elif family != expected:
        bad(f"survey_family = {{{family}}} but the entry lives in bib/{paper['file']}")

    routes, apps, robots = set(), set(), set()
    no_platform = False

    for slug in split_list(fields.get("survey_route", "")):
        if slug in taxonomy.ROUTE_SLUG:
            routes.add(taxonomy.ROUTE_SLUG[slug])
        else:
            bad(f"survey_route = {{{slug}}} is not one of: "
                + ", ".join(taxonomy.ROUTE_SLUG))

    for slug in split_list(fields.get("survey_application", "")):
        if slug in taxonomy.APPLICATION_SLUG:
            apps.add(taxonomy.APPLICATION_SLUG[slug])
        else:
            bad(f"survey_application = {{{slug}}} is not one of: "
                + ", ".join(taxonomy.APPLICATION_SLUG))

    for slug in split_list(fields.get("survey_robot", "")):
        if slug == "none":
            no_platform = True
        elif slug in taxonomy.ROBOT_SLUG:
            robots.add(taxonomy.ROBOT_SLUG[slug])
        else:
            bad(f"survey_robot = {{{slug}}} is not one of: "
                + ", ".join(list(taxonomy.ROBOT_SLUG) + ["none"]))

    if kind == "method":
        if not routes:
            bad("survey_kind = {method} requires survey_route")
        if not apps:
            bad("survey_kind = {method} requires survey_application")
        if not robots and not no_platform:
            bad("survey_kind = {method} requires survey_robot "
                "(use {none} for a platform-free methodology paper)")
    else:
        for f in ("survey_route", "survey_application", "survey_robot"):
            if fields.get(f):
                bad(f"{f} is only meaningful for survey_kind = {{method}}")

    if not paper.get("code"):
        code = strip_tex(fields.get("survey_code", "")).strip()
        if code:
            paper["code"] = code

    paper.update(
        kind=kind,
        family=family,
        routes=routes,
        apps=apps,
        robots=robots,
        is_method=(kind == "method"),
        no_platform=no_platform,
    )
    return paper


def load(bib_dir: Path | None = None) -> tuple[dict[str, list[dict]], list[str]]:
    """Return ({bib file name: [paper, ...]}, [problem, ...]).

    Problems are collected rather than raised so `validate.py` can report every
    issue in one run instead of one per invocation.
    """
    bib_dir = bib_dir or BIB_DIR
    problems: list[str] = []
    out: dict[str, list[dict]] = {}
    seen: dict[str, str] = {}

    for path in sorted(bib_dir.glob("*.bib")):
        if path.stem not in taxonomy.FAMILIES:
            problems.append(
                f"bib/{path.name}: not a known family; add it to taxonomy.FAMILIES "
                "or rename the file")
        text = path.read_text(encoding="utf-8", errors="replace")
        fields_by_key = {
            key: parse_fields(body) for _etype, key, body in split_entries(text)
        }
        papers = parse_bib_file(path)
        for paper in papers:
            if paper["key"] in seen:
                problems.append(
                    f"bib/{path.name}: duplicate key @{paper['key']} "
                    f"(already in bib/{seen[paper['key']]})")
            seen[paper["key"]] = path.name
            annotate(paper, fields_by_key.get(paper["key"], {}), problems)
        out[path.name] = papers

    return out, problems


def methods(all_papers: dict[str, list[dict]]) -> list[dict]:
    """Every reviewed physics-embedded robot-learning method."""
    return [p for entries in all_papers.values() for p in entries if p["is_method"]]
