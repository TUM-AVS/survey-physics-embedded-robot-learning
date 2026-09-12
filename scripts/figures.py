"""Catalog figures, regenerated from bib/*.bib by build.py.

Four figures, each emitted as a self-contained TikZ/PGFPlots fragment
(``\\input``-able by the survey) and as a compiled, tightly cropped PDF:

``paper_timeline``                 stacked publication years by route + cumulative line
``papers_by_application``          application x route stacked bars
``papers_by_robot``                robot platform x route stacked bars
``papers_by_application_and_robot`` both bar charts side by side, vertically centred

PDF compilation needs ``pdflatex``; it is skipped with a warning when absent.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

import taxonomy as classify
from taxonomy import (APPLICATIONS, ROBOTS, ROUTE_COLORS, ROUTE_FILLS,
                      ROUTE_LABELS, ROUTES)

# ---------------------------------------------------------------- styling ---
# Everything about how the generated figures look is set here.
#
#   * To change the FONT SIZE, edit PDF_AXIS_LABEL_SIZE, PDF_TICK_LABEL_SIZE,
#     PDF_LEGEND_SIZE and PDF_VALUE_SIZE independently; PDF_FONT_SIZE is only
#     the fallback for anything none of them covers. These are point sizes:
#     any number works, fractions included.
#   * PDF_BORDER is the white margin kept around the cropped PDF.
PDF_BORDER = "0pt"
# Matches \RequirePackage{times} pulled in by the sagej [times] class option,
# so figure text is set in the same face as the manuscript body.
PDF_FONT_PACKAGE = r"\usepackage{times}"
PDF_FONT_SIZE = 13          # pt -- base font, used by anything not listed below
PDF_AXIS_LABEL_SIZE = 13    # pt -- "Number of papers", "Publication year", ...
PDF_TICK_LABEL_SIZE = 13    # pt -- years and numbers along the axes; in the bar
                            #       charts this also sets the category names,
                            #       which pgfplots treats as y tick labels
PDF_LEGEND_SIZE = 13        # pt -- legend entries
PDF_VALUE_SIZE = 13         # pt -- numbers on and after the bars
PDF_BASELINE_RATIO = 1.2    # baseline skip as a multiple of the point size

# --- vertical size of each plot -------------------------------------------
# Heights are in cm and cover the whole axis (plot area + tick labels + axis
# label). The bar charts keep their bars proportional to the height, so raising
# these makes the bars thicker rather than just adding white space.
PDF_TIMELINE_HEIGHT = 8.0        # cm -- figures/paper_timeline
PDF_APPLICATION_HEIGHT = 5.0     # cm -- figures/papers_by_application
PDF_ROBOT_HEIGHT = 8.1           # cm -- figures/papers_by_robot

# --- the combined side-by-side figure --------------------------------------
# The two panels keep their own heights (above) and are centred on each other.
PDF_COMBINED_PANEL_WIDTH = 8.0   # cm -- width of each of the two panels
PDF_COMBINED_GAP = 0.9           # cm -- gap between the panels, labels included
# Vertical position of the shared legend, in mm below the bottom of the panels.
# LOWER THIS NUMBER (negatives are fine) TO MOVE THE LEGEND UP. It applies to the
# combined figure only; the standalone bar charts keep their own legend.
PDF_COMBINED_LEGEND_GAP = -3     # mm

# The collection window closes mid-year, so the final bar is incomplete: its tick
# label carries this marker, which the figure caption must explain.
PDF_PARTIAL_YEAR = 2026
PDF_PARTIAL_MARK = r"$^{*}$"

# Gap between the x-axis and its tick labels in the timeline. pgfplots measures
# "xticklabel shift" outward from the axis, so it stays correct under rotation.
PDF_TICK_LABEL_SHIFT = 3         # pt -- figures/paper_timeline

TIMELINE_START = 2016
TIMELINE_END = 2026

# GitHub cannot render PDFs inline in Markdown, so each PDF also gets a raster
# preview for the README. The PDF stays the canonical, vector artifact.
PREVIEW_WIDTH = 1400            # px -- width of the README preview images
# Manuscript figures reproduced in the README; previewed from their own PDFs.
MANUSCRIPT_FIGURES = ("overview_physics_injection", "lifecycle", "physics_encoded")

FIG_TIMELINE = "paper_timeline"
FIG_APPLICATION = "papers_by_application"
FIG_ROBOT = "papers_by_robot"
FIG_COMBINED = "papers_by_application_and_robot"


def pt(size: float) -> str:
    """LaTeX font selection at an arbitrary point size.

    ``\\fontsize`` takes the size and the baseline skip, so any number can be
    used rather than only the named commands (``\\small``, ``\\large``, ...).
    """
    return f"\\fontsize{{{size:g}}}{{{size * PDF_BASELINE_RATIO:g}}}\\selectfont"


# ------------------------------------------------------------------- data ---
def method_papers(all_papers: dict[str, list[dict]]) -> list[dict]:
    """Cited papers that the survey reviews as physics-embedded robot learning."""
    return [p for entries in all_papers.values() for p in entries if p.get("is_method")]


def build_timeline(papers: list[dict]) -> tuple[list[int], dict[str, list[int]], list[int]]:
    """Yearly counts per primary route, plus the cumulative total.

    Each paper contributes to exactly one stack segment, so the bar heights sum
    to the yearly paper count and stay consistent with the cumulative line.
    """
    years = list(range(TIMELINE_START, TIMELINE_END + 1))
    counts: dict[str, Counter] = {r: Counter() for r in ROUTES}
    for paper in papers:
        year = paper.get("year")
        route = classify.primary_route(paper)
        if year is None or route is None or not (TIMELINE_START <= year <= TIMELINE_END):
            continue
        counts[route][year] += 1
    series = {r: [counts[r][y] for y in years] for r in ROUTES}
    annual = [sum(series[r][i] for r in ROUTES) for i in range(len(years))]
    cumulative, acc = [], 0
    for n in annual:
        acc += n
        cumulative.append(acc)
    return years, series, cumulative


def build_matrix(papers: list[dict], rows: tuple[str, ...], field: str) -> dict[str, list[int]]:
    """Counts per (row category, route); multi-label papers count in each cell."""
    return {
        row: [sum(1 for p in papers if row in p[field] and route in p["routes"])
              for route in ROUTES]
        for row in rows
    }


def _nice_max(value: int, step: int = 10) -> int:
    if value <= 0:
        return step
    return ((value + step - 1) // step) * step or step


# -------------------------------------------------------------------- TeX ---
def _defs() -> str:
    return "\n".join(
        f"\\providecolor{{route{r}}}{{HTML}}{{{ROUTE_COLORS[r].lstrip('#').upper()}}}\n"
        f"\\providecolor{{fill{r}}}{{HTML}}{{{ROUTE_FILLS[r].lstrip('#').upper()}}}"
        for r in ROUTES
    )


def _axis_fonts() -> str:
    return (f"    label style={{font={pt(PDF_AXIS_LABEL_SIZE)}}},\n"
            f"    tick label style={{font={pt(PDF_TICK_LABEL_SIZE)}}},")


def write_timeline_tex(years, series, cumulative, path: Path) -> None:
    rows = "\n".join(
        f"{y} " + " ".join(str(series[r][i]) for r in ROUTES) + f" {cumulative[i]}"
        for i, y in enumerate(years)
    )
    plots = "\n".join(
        f"\\addplot[fill=fill{r}, draw=route{r}] table[x=Year, y={r.capitalize()}] "
        f"{{\\PPdata}};\n\\addlegendentry{{{ROUTE_LABELS[r]}}}"
        for r in ROUTES
    )
    annual = [sum(series[r][i] for r in ROUTES) for i in range(len(years))]
    ymax_left = _nice_max(max(annual) if annual else 1, 10)
    ymax = _nice_max(cumulative[-1] if cumulative else 1, 50)
    ticklabels = ", ".join(
        f"{y}{PDF_PARTIAL_MARK}" if y == PDF_PARTIAL_YEAR else str(y) for y in years
    )
    body = rf"""% Publication timeline by taxonomy route. Generated by scripts/build.py.
{_defs()}
\pgfplotstableread{{
Year {' '.join(r.capitalize() for r in ROUTES)} Cumulative
{rows}
}}\PPdata

\begin{{tikzpicture}}[font={pt(PDF_FONT_SIZE)}]
\begin{{axis}}[
    width=\linewidth, height={PDF_TIMELINE_HEIGHT:g}cm,
    ybar stacked, bar width=11pt,
    enlarge x limits=0.04,
{_axis_fonts()}
    xtick=data, xticklabel style={{rotate=45, anchor=east}},
    xticklabel shift={PDF_TICK_LABEL_SHIFT:g}pt,
    xticklabels={{{ticklabels}}},
    ylabel={{Number of papers}}, xlabel={{Publication year}},
    legend style={{at={{(0.02,0.98)}}, anchor=north west, draw=none,
                  legend columns=1, cells={{anchor=west}}, font={pt(PDF_LEGEND_SIZE)}}},
    axis y line*=left, ymin=0, ymax={ymax_left},
]
{plots}
\addlegendimage{{legend image code/.code={{%
    \draw[black, thick] (0cm,0cm) -- (0.55cm,0cm);
    \fill[black] (0.275cm,0cm) circle (1.3pt);}}}}
\addlegendentry{{Cumulative}}
\end{{axis}}

\begin{{axis}}[
    width=\linewidth, height={PDF_TIMELINE_HEIGHT:g}cm,
    axis x line=none, axis y line*=right,
    ymin=0, ymax={ymax}, ylabel={{Cumulative paper count}},
{_axis_fonts()}
    enlarge x limits=0.04, xtick=\empty,
]
\addplot[black, thick, mark=*, mark options={{fill=black, scale=0.7}}]
    table[x expr=\coordindex, y=Cumulative] {{\PPdata}};
\end{{axis}}
\end{{tikzpicture}}
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _bars_axis(cells: dict[str, list[int]], height: float, width: str,
               name: str = "", extra: str = "", legend: bool = True) -> str:
    """One horizontal stacked-bar axis, ordered by decreasing total.

    Shared by the standalone bar figures and by the combined side-by-side one,
    so the two always render identically.
    """
    order = sorted(cells, key=lambda k: (-sum(cells[k]), k))
    xmax = _nice_max(max((sum(v) for v in cells.values()), default=1), 10)
    labels = ", ".join(n.replace("&", r"\&") for n in order)
    plots = []
    for j, route in enumerate(ROUTES):
        coords = " ".join(f"({cells[n][j]},{i})" for i, n in enumerate(order))
        entry = (f"\n\\addlegendentry{{{ROUTE_LABELS[route]}}}") if legend else ""
        plots.append(
            f"\\addplot[fill=fill{route}, draw=route{route}] coordinates {{{coords}}};{entry}")
    totals = "\n".join(
        f"\\node[anchor=west, font={pt(PDF_VALUE_SIZE)}\\bfseries] "
        f"at (axis cs:{sum(cells[n])},{i}) {{{sum(cells[n])}}};"
        for i, n in enumerate(order)
    )
    # Keep the bars proportional to the axis height so it stays legible at any size.
    bar_width = min(0.6, 0.42 * height / len(order))
    legend_style = (
        f"    legend style={{at={{(0.5,0)}}, anchor=north, yshift=-1.05cm, legend columns=3,\n"
        f"                  draw=none, /tikz/every even column/.append style={{column sep=0.35cm}},\n"
        f"                  font={pt(PDF_LEGEND_SIZE)}}},\n"
    ) if legend else ""
    return rf"""\begin{{axis}}[
    xbar stacked,
    bar width={bar_width:.3f}cm,
{_axis_fonts()}
    width={width}, height={height:g}cm,
    xmin=0, xmax={xmax + xmax * 0.12:.0f},
    ytick={{{','.join(str(i) for i in range(len(order)))}}},
    yticklabels={{{labels}}},
    y dir=reverse,
    ytick style={{draw=none}},
    enlarge y limits={{abs=0.6}},
    xlabel={{Number of papers}},
    xmajorgrids, grid style={{black!12}},
    axis y line*=left, axis x line*=bottom,
{legend_style}{name}{extra}]
{chr(10).join(plots)}
{totals}
\end{{axis}}"""


def write_bars_tex(cells: dict[str, list[int]], row_title: str, path: Path,
                   height: float) -> None:
    width = r"0.72\linewidth"
    axis = _bars_axis(cells, height, width)
    body = (f"% {row_title} x taxonomy route. Generated by scripts/build.py.\n"
            f"{_defs()}\n"
            f"\\begin{{tikzpicture}}[font={pt(PDF_FONT_SIZE)}]\n"
            f"{axis}\n"
            f"\\end{{tikzpicture}}\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def write_combined_tex(apps: dict[str, list[int]], robots: dict[str, list[int]],
                       path: Path) -> None:
    """Both bar charts side by side, centred on each other, with one legend.

    The right panel is anchored ``outer west`` to the left panel's ``outer
    east``: those anchors sit at the vertical middle of each panel *including*
    its tick labels, which both centres the panels and keeps the long robot
    category names clear of the left panel.
    """
    width = f"{PDF_COMBINED_PANEL_WIDTH:g}cm"
    swatch = r"\raisebox{0.2ex}{\tikz\filldraw[fill=fill%s, draw=route%s] (0,0) rectangle (2.8mm,2.1mm);}"
    entries = r"\quad ".join(
        f"{swatch % (r, r)}\\," + ROUTE_LABELS[r].replace("-", "-") for r in ROUTES
    )
    left_axis = _bars_axis(apps, PDF_APPLICATION_HEIGHT, width,
                           name="    name=appaxis,\n", legend=False)
    placement = ("    at={(appaxis.outer east)}, anchor=outer west,\n"
                 f"    xshift={PDF_COMBINED_GAP:g}cm,\n")
    right_axis = _bars_axis(robots, PDF_ROBOT_HEIGHT, width,
                            name="    name=robotaxis,\n", extra=placement, legend=False)
    body = rf"""% Application and robot-platform distributions side by side.
% Generated by scripts/build.py.
{_defs()}
\begin{{tikzpicture}}[font={pt(PDF_FONT_SIZE)}]
{left_axis}

{right_axis}

% Shared legend, centred under the pair and dropped below the taller panel.
\coordinate (pplegendx) at ($(appaxis.outer south west)!0.5!(robotaxis.outer south east)$);
\node[anchor=north, yshift={-PDF_COMBINED_LEGEND_GAP:g}mm, font={pt(PDF_LEGEND_SIZE)}]
    at (robotaxis.outer south -| pplegendx) {{{entries}}};
\end{{tikzpicture}}
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


# -------------------------------------------------------------------- PDF ---
STANDALONE = """\\documentclass[border={border}]{{standalone}}
{font}
\\usepackage{{tikz}}
\\usetikzlibrary{{calc}}
\\usepackage{{pgfplots}}
\\usepackage{{pgfplotstable}}
\\pgfplotsset{{compat=1.18}}
\\usepackage{{xcolor}}
\\begin{{document}}
\\input{{{fragment}}}
\\end{{document}}
"""


def compile_pdf(tex: Path, out_dir: Path) -> bool:
    """Compile a fragment into ``out_dir/<name>.pdf`` via pdflatex."""
    if not shutil.which("pdflatex"):
        return False
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        wrapper = tmp_path / "wrap.tex"
        wrapper.write_text(
            STANDALONE.format(border=PDF_BORDER, font=PDF_FONT_PACKAGE,
                              fragment=tex.resolve().as_posix()),
            encoding="utf-8",
        )
        proc = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-halt-on-error",
             "-output-directory", str(tmp_path), str(wrapper)],
            capture_output=True, text=True,
        )
        produced = tmp_path / "wrap.pdf"
        if proc.returncode != 0 or not produced.exists():
            tail = "\n".join(proc.stdout.strip().splitlines()[-12:])
            print(f"  ! pdflatex failed for {tex.name}:\n{tail}")
            return False
        shutil.copyfile(produced, out_dir / f"{tex.stem}.pdf")
    return True


def make_preview(pdf: Path) -> bool:
    """Render ``pdf`` to a same-named PNG beside it, for Markdown embedding."""
    if not shutil.which("pdftoppm") or not pdf.exists():
        return False
    proc = subprocess.run(
        ["pdftoppm", "-png", "-singlefile",
         "-scale-to-x", str(PREVIEW_WIDTH), "-scale-to-y", "-1",
         str(pdf), str(pdf.with_suffix(""))],
        capture_output=True, text=True,
    )
    return proc.returncode == 0 and pdf.with_suffix(".png").exists()


# ------------------------------------------------------------------ driver ---
def write_all(all_papers: dict[str, list[dict]], catalog_root: Path,
              compile_pdfs: bool = True) -> dict:
    """Emit every catalog figure and return the counts used to caption them.

    With ``compile_pdfs=False`` only the TikZ fragments are refreshed and the
    existing PDFs/PNGs are left alone, so the README can be rebuilt on a machine
    with no LaTeX installed.
    """
    figures = catalog_root / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    papers = method_papers(all_papers)

    years, series, cumulative = build_timeline(papers)
    apps = build_matrix(papers, APPLICATIONS, "apps")
    robots = build_matrix(papers, ROBOTS, "robots")

    write_timeline_tex(years, series, cumulative, figures / f"{FIG_TIMELINE}.tex")
    write_bars_tex(apps, "Application", figures / f"{FIG_APPLICATION}.tex",
                   PDF_APPLICATION_HEIGHT)
    write_bars_tex(robots, "Robot platform", figures / f"{FIG_ROBOT}.tex",
                   PDF_ROBOT_HEIGHT)
    write_combined_tex(apps, robots, figures / f"{FIG_COMBINED}.tex")

    generated = (FIG_TIMELINE, FIG_APPLICATION, FIG_ROBOT, FIG_COMBINED)
    if compile_pdfs:
        pdfs = [n for n in generated if compile_pdf(figures / f"{n}.tex", figures)]
        previews = [n for n in (*pdfs, *MANUSCRIPT_FIGURES)
                    if make_preview(figures / f"{n}.pdf")]
        missing = [n for n in (*pdfs, *MANUSCRIPT_FIGURES) if n not in previews]
        if missing:
            print("  ! no PNG preview (is pdftoppm installed?): " + ", ".join(missing))
    else:
        # Keep whatever was committed; the README links to these by name.
        pdfs = [n for n in generated if (figures / f"{n}.pdf").exists()]
        previews = [n for n in (*generated, *MANUSCRIPT_FIGURES)
                    if (figures / f"{n}.png").exists()]

    n_pre = sum(1 for p in papers if p.get("year") and p["year"] < TIMELINE_START)
    # Primary-route totals over every reviewed method, so shares sum to 100%.
    primary = Counter(classify.primary_route(p) for p in papers)
    return {
        "primary": {r: primary[r] for r in ROUTES},
        "years": years,
        "series": series,
        "cumulative": cumulative,
        "applications": apps,
        "robots": robots,
        "n_method": len(papers),
        "n_timeline": cumulative[-1] if cumulative else 0,
        "n_pre": n_pre,
        "pdfs": pdfs,
        "previews": previews,
    }
