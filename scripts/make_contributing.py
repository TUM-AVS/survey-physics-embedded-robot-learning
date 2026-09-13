#!/usr/bin/env python3
"""Regenerate CONTRIBUTING.md.

The label tables are built from `taxonomy.py`, so the contributor documentation
can never drift from the vocabulary the validator actually enforces. Called by
`build.py`; run it directly to refresh only this file.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import taxonomy as t

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "CONTRIBUTING.md"
ISSUE_URL = ("https://github.com/TUM-AVS/survey-physics-embedded-robot-learning"
             "/issues/new?template=add_paper.yml")


def _table(slugs, help_map) -> str:
    rows = ["| value | meaning |", "| --- | --- |"]
    rows += [f"| `{s}` | {help_map[s]} |" for s in slugs]
    return "\n".join(rows)


def render() -> str:
    families = "\n".join(f"| `{k}.bib` | {v} |" for k, v in t.FAMILIES.items())
    kinds = _table(t.KINDS, t.KIND_HELP)
    routes = _table(list(t.ROUTE_SLUG),
                    {k: t.ROUTE_HELP[v] for k, v in t.ROUTE_SLUG.items()})
    apps = _table(list(t.APPLICATION_SLUG), t.APPLICATION_HELP)
    robots = _table(list(t.ROBOT_SLUG) + ["none"], t.ROBOT_HELP)
    return TEMPLATE.format(issue_url=ISSUE_URL, families=families, kinds=kinds,
                           routes=routes, applications=apps, robots=robots)


def main() -> int:
    OUT.write_text(render(), encoding="utf-8")
    print(f"Wrote {OUT.name}")
    return 0


TEMPLATE = r"""# Contributing

Thanks for helping keep this catalog current. **Adding a paper is meant to take
two minutes**, and you do not need to install anything.

## Two ways to contribute

### 1. Open an issue (no git required)

Use the **[Add a paper]({issue_url})** issue form. Paste the BibTeX, pick the labels
from the dropdowns, and a maintainer will add it. This is the recommended route
if you are unsure about the classification — say so in the issue and we will
work it out together.

### 2. Open a pull request

Add **one BibTeX entry** to the matching file in [`bib/`](bib/) and open a PR.
You can do this entirely in the GitHub web UI: open the file, click the pencil
icon, paste, and choose *Create a new branch and start a pull request*.

Automated checks run on every PR and tell you exactly what to fix. You do not
have to regenerate `README.md` — a maintainer does that when merging.

## The entry format

The `bib/*.bib` files are ordinary BibTeX, with extra `survey_*` fields carrying
the survey's labels. BibTeX ignores unknown fields, so these files still work as
a plain bibliography if you want to cite the corpus yourself.

```bibtex
@inproceedings{{lastname2026keyword,
  title   = {{A physics-encoded network for contact-rich manipulation}},
  author  = {{Lastname, First and Other, Second}},
  booktitle = {{Conference on Robot Learning (CoRL)}},
  year    = {{2026}},
  doi     = {{10.0000/example}},
  survey_kind        = {{method}},
  survey_family      = {{model-structured}},
  survey_route       = {{physics-encoded}},
  survey_application = {{dynamics-learning, control}},
  survey_robot       = {{manipulators}},
  survey_code        = {{https://github.com/example/repo}},
}}
```

Copy the bibliographic half straight from the publisher, Google Scholar, DBLP,
or arXiv — please do not retype it. Include a `doi`, `url`, or `eprint` so the
README can link the paper.

### Which file?

Pick the file under `bib/` matching the method family. The family only decides
where the entry lives and which README section it appears under; the *route* is
stated per entry, so a paper in `hybrid-physics.bib` can still be labelled
physics-informed.

| file in `bib/` | Method family |
| --- | --- |
{families}

## The `survey_*` fields

### `survey_kind` (required)

Only `method` entries are counted in the statistics and figures.

{kinds}

### `survey_route` (required for methods)

**How** the physics prior enters the learning algorithm — the survey's central
question. List several, comma-separated, if the paper genuinely uses more than
one.

{routes}

Not sure? Let's work it out together — open an issue and ask.

### `survey_application` (required for methods)

What the method is *for*. Several values are allowed.

{applications}

### `survey_robot` (required for methods)

Which platform the paper actually reports results on — not what it could apply
to in principle. Several values are allowed. Use `none` for a methodology paper
with no specific platform.

{robots}

### `survey_family` (required)

Must match the file name, e.g. `hybrid-physics` in `bib/hybrid-physics.bib`.
It is stated explicitly so a misfiled entry is caught rather than silently
counted under the wrong heading.

### `survey_code` (optional)

Link to the paper's open-source implementation. A `url` field pointing at
GitHub/GitLab is picked up automatically, so `survey_code` is only needed when
the code lives somewhere the `url` field does not point.

## Checking your work

Everything is standard-library Python 3.9+, so there is nothing to install:

```bash
python3 scripts/validate.py              # catalog checks (what CI runs)
python3 scripts/validate.py --warnings   # ... including non-blocking hints
python3 scripts/build.py                 # regenerate README.md + exports/papers.csv
python3 scripts/build.py --figures       # ... and the figures (needs pdflatex)
```

`validate.py` reports every problem at once and points at the offending entry.
It also flags a paper whose title already appears in the catalog, which is the
easiest mistake to make.

## What is generated, and what is not

| Path | |
| --- | --- |
| `bib/*.bib` | **Source of truth.** Edit these. |
| `README.md` | Generated by `scripts/build.py`. Do not edit by hand. |
| `exports/papers.csv` | Generated. A flat view for spreadsheets and scripts. |
| `figures/*.pdf`, `figures/*.png` | Generated. |
| `scripts/taxonomy.py` | The controlled vocabulary. Changing it changes the survey's taxonomy — open an issue first. |

Because the README is generated, a pull request that edits it directly will be
overwritten. Change the BibTeX instead.

## Scope

The survey covers methods that embed **physics priors specific to a robotic
system** — governing equations, conservation laws and symmetries, geometric and
kinematic structure, constitutive and interaction models, physical consistency
and admissibility — into machine learning algorithms.

Generic mathematical structure alone does not qualify. A paper is in scope when
the prior expresses concrete physical knowledge about the system being learned,
and when the work is evaluated on a robotic system or a mechanical system used
as a robotics benchmark. Purely computational-physics work with no robotics
application is out of scope, however good it is.

If you are unsure whether a paper is in scope, open an issue and ask — that is
useful feedback on the taxonomy itself.
"""


if __name__ == "__main__":
    raise SystemExit(main())
