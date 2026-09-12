#!/usr/bin/env python3
"""Check the catalog. Run this before opening a pull request.

    python3 scripts/validate.py

Reports every problem it finds in one pass, and exits non-zero if any are
errors. Warnings (a missing DOI, say) never fail the build: they are hints, not
blockers. Standard library only -- no installation needed.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import catalog
import taxonomy

YEAR_MIN = 1900  # Koopman 1931 is the oldest reference in the catalog
YEAR_MAX = 2030


def check(all_papers: dict[str, list[dict]]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    papers = [p for entries in all_papers.values() for p in entries]
    if not papers:
        errors.append("bib/ contains no entries at all -- is the directory empty?")
        return errors, warnings

    titles: dict[str, str] = {}
    for p in papers:
        where = f"bib/{p['file']}: @{p['key']}"

        if not re.fullmatch(r"[A-Za-z0-9_.:+-]+", p["key"]):
            errors.append(f"{where}: citation key has characters BibTeX may choke on")

        if p["year"] is None:
            errors.append(f"{where}: missing or unparsable year")
        elif not (YEAR_MIN <= p["year"] <= YEAR_MAX):
            errors.append(f"{where}: year {p['year']} is outside {YEAR_MIN}-{YEAR_MAX}")

        # Near-duplicate detection: same title, different key. Catches the most
        # common contribution mistake, adding a paper the catalog already has.
        norm = re.sub(r"[^a-z0-9]+", " ", p["title"].lower()).strip()
        if norm in titles and titles[norm] != p["key"]:
            errors.append(f"{where}: same title as @{titles[norm]} -- already in the catalog?")
        titles.setdefault(norm, p["key"])

        if not p["link"]:
            warnings.append(f"{where}: no doi/url/eprint, so the README cannot link it")

        if p["code"] and not p["code"].startswith("http"):
            errors.append(f"{where}: survey_code must be a full URL, got {p['code']!r}")

    return errors, warnings


def summarize(all_papers: dict[str, list[dict]]) -> None:
    methods = catalog.methods(all_papers)
    n = len(methods)
    print(f"\n  {sum(len(v) for v in all_papers.values())} references in "
          f"{len(all_papers)} files, {n} reviewed methods")
    kinds = Counter(p["kind"] for v in all_papers.values() for p in v)
    print("  by kind: " + ", ".join(f"{kinds[k]} {k}" for k in taxonomy.KINDS if kinds[k]))
    if not n:
        return
    primary = Counter(taxonomy.primary_route(p) for p in methods)
    print("  by primary route: " + ", ".join(
        f"{primary[r]} {taxonomy.ROUTE_LABELS[r].lower()} ({100 * primary[r] / n:.0f}%)"
        for r in taxonomy.ROUTES))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--warnings", action="store_true",
                    help="list every warning instead of just counting them")
    args = ap.parse_args()

    all_papers, problems = catalog.load()
    errors, warnings = check(all_papers)
    errors = problems + errors

    if warnings:
        if args.warnings:
            for w in warnings:
                print(f"  warning: {w}")
            print(f"\n{len(warnings)} warning(s) -- these never block a merge.")
        else:
            print(f"{len(warnings)} warning(s) (mostly older entries with no DOI); "
                  "re-run with --warnings to see them. They never block a merge.")

    if errors:
        print(f"\n{len(errors)} error(s):\n")
        for e in errors:
            print(f"  error: {e}")
        print("\nSee CONTRIBUTING.md for the allowed survey_* values.")
        return 1

    print("\nCatalog OK.", end="")
    summarize(all_papers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
