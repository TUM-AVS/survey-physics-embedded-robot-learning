#!/usr/bin/env python3
"""Rebuild every generated file in this repository from ``bib/*.bib``.

    python3 scripts/build.py             # README.md + exports/papers.csv
    python3 scripts/build.py --figures   # ... and regenerate the figures (needs pdflatex)

``bib/*.bib`` is the only source of truth. Everything this script writes --
README.md, exports/papers.csv, figures/ -- is generated, so edit the BibTeX
entries and re-run rather than editing the output by hand.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import catalog
import figures as timeline
import make_contributing
import taxonomy as classify
from catalog import gh_anchor, md_escape, parse_bib_file, venue  # noqa: F401

ROOT = Path(__file__).resolve().parent.parent
BIB_DIR = ROOT / "bib"
README = ROOT / "README.md"
CSV_OUT = ROOT / "exports" / "papers.csv"

# Announced in the abstract of main.tex.
REPO_URL = "https://github.com/TUM-AVS/survey-physics-embedded-robot-learning"
SURVEY_TITLE = "Embedding Physics Priors in Robot Learning: A Survey"

# Heading of the decision-flow section, which the survey (Sec. "Classification
# Flow" and Sec. "Scope of the Considered Literature") promises this repo hosts.
FLOW_HEADING = ":twisted_rightwards_arrows: Classification flow"
# Linked from the very first lines, so a reader sees how to contribute immediately.
CONTRIB_HEADING = "Contributing"

# Mirrors the manuscript: one entry per survey section, one sub-entry per
# survey subsection, with the same titles and the same order. Changing a
# subsection title in the paper means renaming the matching bib file here.
SECTIONS = [
    (
        "Physics-Encoded Architectures",
        "encoded",
        "Physics-encoded architectures incorporate physical insights through tailored internal "
        "structures, layers, topologies, equations, architectural constraints, energy, invariance "
        "and symmetry principles, extending or augmenting physics-based models with robotics "
        "domain knowledge. \n"
        "The largest body of work, and therefore reviewed first.",
        [
            ("Lagrangian Learning Models", "physics-encoded/lagrangian-learning-models.bib"),
            ("Hamiltonian Learning Models", "physics-encoded/hamiltonian-learning-models.bib"),
            ("Model-Structured Learning Architectures", "physics-encoded/model-structured-architectures.bib"),
            ("Neural ODEs and Variational Integrator Networks", "physics-encoded/neural-odes-and-variational-integrators.bib"),
            ("Hybrid Physics-Learning Architectures", "physics-encoded/hybrid-physics-learning.bib"),
            ("Physics-Encoded Topology Learning", "physics-encoded/topology-learning.bib"),
            ("Physics-Encoded Neural Operators", "physics-encoded/neural-operators.bib"),
            ("Other Types of Physics-Encoded Architectures", "physics-encoded/other-architectures.bib"),
        ],
    ),
    (
        "Physics-Informed Loss Functions",
        "informed",
        "Physics-informed approaches provide a flexible and data-efficient framework for "
        "solving forward and inverse problems governed by differential equations, by embedding "
        "physical laws as soft constraints in the training loss functions. Physics-informed "
        "components are active **only during training**: they are part of neither the "
        "architecture nor the inputs.",
        [
            ("Physics-Informed Neural Networks", "physics-informed/neural-networks.bib"),
            ("Physics-Informed Neural Operators", "physics-informed/neural-operators.bib"),
            ("Other Types of Loss and Reward Functions", "physics-informed/other-loss-and-reward-functions.bib"),
        ],
    ),
    (
        "Physics-Guided Inputs, Data, and Representations",
        "guided",
        "Physics-guided learning exploits physics priors to transform, enrich, curate, select, "
        "or correct input features, training data, and learned representations. Rather than "
        "modifying the model architecture or training objective, these methods embed physical "
        "knowledge into the inputs, data, or representations before training or as pre- or "
        "post-processing guidance at inference, while preserving the flexibility of standard "
        "ML models.",
        [
            ("Physical Models as Structured Inputs to Learning Algorithms", "physics-guided/structured-inputs.bib"),
            ("Physics-Guided Features & Training Data", "physics-guided/features-and-data.bib"),
            ("Geometric Learning", "physics-guided/geometric-learning.bib"),
            ("Frequency-Domain Learning", "physics-guided/frequency-domain-learning.bib"),
            ("Physically Consistent World Representations", "physics-guided/world-representations.bib"),
            ("Physics-Guided Diffusion-based Generation", "physics-guided/diffusion.bib"),
            ("Physics-Guided Neural Operators", "physics-guided/neural-operators.bib"),
        ],
    ),
    (
        "Software Tools",
        "software",
        "Open-source tools used to build physics-embedded robot-learning models.",
        # The survey splits this section into five subsections; the catalog keeps
        # them in one table, since the entries are tools rather than papers.
        [
            ("Libraries, Frameworks, and Differentiable Simulators", "software.bib"),
        ],
    ),
]

UNLISTED_BIB = ("surveys.bib", "background.bib")

SEARCH_KEYWORDS = {
    "Core physics-embedding terms": [
        "physics-informed", "physics-encoded", "physics-guided", "physics-embedded",
        "physics-constrained", "physics-enhanced", "physics-driven", "physics-inspired",
        "physics-aware", "physics-based prior", "physics prior", "physical prior",
        "physical constraint", "physically consistent", "physically plausible",
        "physically native", "physical consistency", "inductive bias",
        "structured neural network", "structure-preserving learning",
        "structured learning mechanical system", "model-structured neural network",
        "hybrid physics-learning", "hybrid model", "grey-box model", "residual physics",
        "residual dynamics learning", "knowledge-based neural network",
        "combining physics and deep learning", "intuitive physics",
    ],
    "Governing equations & analytical mechanics": [
        "Lagrangian neural network", "deep Lagrangian network", "DeLaN",
        "Hamiltonian neural network", "Hamiltonian dynamics learning",
        "port-Hamiltonian learning", "symplectic network", "symplectic ODE",
        "Euler-Lagrange learning", "Newton-Euler algorithm", "differentiable Newton-Euler",
        "rigid-body dynamics learning", "energy-based control learning",
        "variational integrator network", "neural ODE robotics",
        "neural differential equation control", "Cosserat rod learning",
        "continuum mechanics neural network", "structured mechanical model",
        "mechanical system learning",
    ],
    "Conservation, symmetry & geometry": [
        "conservation law neural network", "energy-conserving network",
        "momentum-conserving network", "equivariant neural network", "SE(3)-equivariant",
        "SO(3)-equivariant", "equivariant diffusion policy", "symmetry-aware learning",
        "morphological symmetry", "discrete symmetry robotics", "Lie group learning",
        "Riemannian manifold learning", "geometric deep learning robotics",
        "geometric prior policy", "nonholonomic constraint learning",
        "explicit constraint neural network", "matrix sparsity bias",
    ],
    "Physics-informed losses": [
        "physics-informed neural network", "PINN robotics", "PINN control",
        "physics-informed loss", "PDE residual loss", "ODE residual loss",
        "physics regularization", "physics-based regularizer", "energy conservation loss",
        "power consistency loss", "physics-informed neural operator",
        "physics-informed reinforcement learning", "Eikonal equation neural network",
        "physics-informed motion planning",
    ],
    "Operators, identification & equation discovery": [
        "Koopman operator learning", "deep Koopman", "DeepONet", "Fourier neural operator",
        "neural operator", "SINDy", "sparse identification nonlinear dynamics",
        "symbolic regression dynamics", "equation learner network",
        "governing equation discovery", "topology learning neural network",
        "sparse Bayesian identification", "system identification neural network",
        "dynamic identification robot", "inertial parameter identification",
        "friction identification", "friction-aware learning",
    ],
    "Probabilistic & kernel methods": [
        "Gaussian process dynamics", "Gaussian process inverse dynamics",
        "physically consistent Gaussian process", "structured kernel dynamics",
        "RKHS dynamics learning", "dissipative Gaussian process",
        "uncertainty-aware model predictive control", "Bayesian dynamics learning",
        "neural stochastic differential equation", "uncertainty quantification dynamics",
    ],
    "Generative & foundation models": [
        "diffusion policy", "physics-guided diffusion", "diffusion model robot",
        "diffusion planning robot", "motion diffusion model",
        "dynamically admissible trajectory", "world model robotics", "video world model",
        "driving world model", "physics-grounded world model",
        "physically consistent world model", "vision-language-action model",
        "physics-aware foundation model", "differentiable physics simulation",
        "differentiable simulation learning", "differentiable rendering robot",
    ],
    "Applications": [
        "robot dynamics learning", "inverse dynamics learning", "forward dynamics learning",
        "friction model learning", "contact dynamics learning",
        "actuator dynamics identification", "trajectory planning neural network",
        "motion planning neural network", "time-optimal motion planning",
        "motion prediction physics", "trajectory tracking learning",
        "model predictive control learning", "feedforward control neural network",
        "state estimation neural network", "sideslip angle estimation",
        "vehicle state estimation", "tire force estimation", "tyre force estimation",
        "ground reaction force estimation", "disturbance observer learning",
        "contact force estimation", "sim-to-real gap dynamics", "fault diagnosis physics",
    ],
    "Platforms": [
        "robot manipulator learning", "robotic arm dynamics", "industrial robot dynamics",
        "parallel manipulator identification", "mobile robot dynamics learning",
        "vehicle dynamics neural network", "longitudinal vehicle dynamics",
        "autonomous racing learning", "race car control learning", "autonomous drifting",
        "anti-lock braking learning", "legged robot dynamics learning",
        "quadruped dynamics learning", "quadrupedal locomotion learning",
        "humanoid dynamics learning", "character controller physics",
        "quadrotor dynamics learning", "aerial robot dynamics",
        "underwater vehicle dynamics learning", "soft robot dynamics learning",
        "continuum robot learning", "exoskeleton control learning",
        "collaborative robot dynamics",
    ],
}

# Application categories used to group every summary table in the survey.
APPLICATIONS = list(classify.APPLICATIONS)
# Longer wording used when the applications are named in a sentence.
PROSE_APPLICATION = {"Planning & Prediction": "trajectory planning & prediction"}

# Figures of the manuscript reproduced inside the catalog sections.
SECTION_FIGURES = {
    "Physics-Encoded Architectures": (
        "physics_encoded",
        "Sub-categories of physics-encoded robot learning architectures.",
    ),
}



# One- or two-sentence description per subsection, condensed from the survey
# section of the same name, so the catalog reads on its own.
SUBSECTION_INTRO = {
 "physics-encoded/lagrangian-learning-models":
   "Methods that build the Euler-Lagrange equations into the model, learning the "
   "Lagrangian (or its inertia and potential terms) rather than the dynamics directly. "
   "Energy conservation and a positive-definite inertia matrix hold by construction.",
 "physics-encoded/hamiltonian-learning-models":
   "The Hamiltonian counterpart: the model learns the total energy as a function of "
   "generalized coordinates and momenta, and symplectic or port-Hamiltonian structure "
   "supplies energy conservation, passivity, and interconnection with external ports.",
 "physics-encoded/model-structured-architectures":
   "Architectures whose layers, internal connections, or constraints are derived from "
   "physical principles, without committing to a full analytical-mechanics formalism. "
   "The family also covers non-network models built the same way.",
 "physics-encoded/neural-odes-and-variational-integrators":
   "Continuous-time models that treat the network as the right-hand side of an ODE, and "
   "discrete-time models whose update rule is a variational integrator, preserving the "
   "geometry of the underlying flow.",
 "physics-encoded/hybrid-physics-learning":
   "Modular combinations in which a physics-based model and a learned component remain "
   "separate: the learned part supplies a subsystem, a residual, or pre-processed sensor "
   "input, while the physics model is used unchanged.",
 "physics-encoded/topology-learning":
   "Methods that learn the *structure* of the model - which terms, operators, or "
   "connections appear - by assembling a library of candidate primitives under sparsity "
   "or physical constraints, as in SINDy and equation learners.",
 "physics-encoded/neural-operators":
   "Operators between function spaces, rather than fixed-dimensional maps, with governing "
   "equations or physical structure built into the operator itself (Koopman lifting, "
   "DeepONet, FNO).",
 "physics-encoded/other-architectures":
   "Architectures that embed physics or domain knowledge in ways the categories above do "
   "not cover: planning-specific output layers, bio-inspired structure, and symmetry "
   "groups as inductive biases.",
 "physics-informed/neural-networks":
   "Conventional architectures trained with a residual loss derived from the governing "
   "ODEs or PDEs. The physics constrains the optimization only: at inference the model is "
   "an ordinary network.",
 "physics-informed/neural-operators":
   "Neural operators trained with physics-based residual losses, used where measured data "
   "alone are too sparse to identify the operator.",
 "physics-informed/other-loss-and-reward-functions":
   "Objectives other than PDE residuals that encode physical requirements - contact and "
   "friction consistency, stability, dynamic admissibility - including physics-shaped "
   "rewards in reinforcement learning.",
 "physics-guided/structured-inputs":
   "A physics-based model computes features that are fed to a downstream learner, so the "
   "network sees physically meaningful quantities instead of raw signals.",
 "physics-guided/features-and-data":
   "Physics priors used to choose input features or to design and curate the training "
   "data itself, including excitation trajectories matched to the system's dynamics.",
 "physics-guided/geometric-learning":
   "Inputs and outputs mapped so that the non-Euclidean geometry of the data - rotations, "
   "manifolds, SPD matrices - is preserved through learning.",
 "physics-guided/frequency-domain-learning":
   "Transforming signals into the frequency domain, counted as physics-guided only when "
   "the retained components follow from known physical properties of the system.",
 "physics-guided/world-representations":
   "World and video models built with explicit mechanisms - occupancy, 3D structure, "
   "state conditioning - that keep the generated representation physically consistent.",
 "physics-guided/diffusion":
   "Diffusion-based generation steered by physics: analytical kinematics, dynamic "
   "feasibility, or contact constraints applied as guidance during sampling.",
 "physics-guided/neural-operators":
   "Koopman and related operators whose observables or lifted coordinates are constructed "
   "from first-principles knowledge rather than learned from scratch.",
 "software":
   "Libraries, frameworks, and differentiable simulators for building the methods reviewed "
   "above, covering model-structured and hybrid frameworks, neural differential equations, "
   "equation discovery and system identification, physics-informed machine learning, and "
   "differentiable simulation.",
}

# Descriptions for the subsubsections of the two subsections the survey splits.
GROUP_INTRO = {
 "learning-complex-subsystems":
   "A learned model replaces one hard-to-parameterize subsystem - tire forces, friction, "
   "contact - while the rest of the system keeps its analytical description.",
 "residual-learning":
   "A learned term is added on top of a physics-based model to absorb unmodeled dynamics, "
   "parameter error, and simplifying assumptions.",
 "sensor-pre-processing":
   "A network pre-processes raw sensor measurements, and its output feeds a physics-based "
   "estimator such as a Kalman filter.",
 "motion-planning":
   "Network architectures tailored to planning and prediction, with output layers that "
   "enforce dynamic feasibility or smoothness of the generated trajectories.",
 "bio-inspired":
   "Architectures that borrow structure from biological perception, action selection, and "
   "neural representation.",
 "symmetry-aware":
   "Architectures built around the symmetry groups of the robot, linking invariance to "
   "conservation laws through Noether's theorem.",
}


def table_row(p: dict) -> str:
    title = md_escape(p["title"])
    if p["link"]:
        paper = f"[{title}]({p['link']})"
    else:
        paper = title
    if p.get("added"):
        paper += " :new:"
    year = str(p["year"] or p["year_raw"] or "—")
    venue = md_escape(p["venue"])
    return f"| {paper} | {year} | {venue} |"


def _figure(name: str, alt: str, caption: str) -> list[str]:
    """Embed a figure's PNG preview and link its PDF (GitHub cannot inline PDFs)."""
    return [
        f"[![{alt}](figures/{name}.png)](figures/{name}.pdf)",
        "",
        f"*{caption} Vector version: [`{name}.pdf`](figures/{name}.pdf).*",
        "",
    ]


def _outside_timeline(figs: dict) -> str:
    """Name the methods the timeline leaves out, so its total adds up."""
    parts = []
    if figs["n_pre"]:
        parts.append(f"{figs['n_pre']} earlier")
    if figs.get("n_post"):
        parts.append(f"{figs['n_post']} dated {timeline.TIMELINE_END + 1} or later")
    return f" ({' and '.join(parts)} are listed in the tables below)" if parts else ""


def _partial_year_note() -> str:
    """Footnote for the timeline's final year, which is still being filled."""
    return (f"\\*{timeline.PDF_PARTIAL_YEAR} is still in progress; its count grows "
            f"as new papers are added to the catalog.")


def _timeline_md(figs: dict) -> str:
    """Yearly counts as a Markdown table (GitHub cannot render the PDF inline)."""
    head = "| Year | " + " | ".join(
        classify.ROUTE_LABELS[r] for r in classify.ROUTES) + " | Total | Cumulative |"
    rule = "|:---|" + "---:|" * (len(classify.ROUTES) + 2)
    rows = []
    for i, year in enumerate(figs["years"]):
        vals = [figs["series"][r][i] for r in classify.ROUTES]
        # The final year is incomplete; the figure caption above explains the marker.
        label = f"{year}\\*" if year == timeline.PDF_PARTIAL_YEAR else str(year)
        rows.append(f"| {label} | " + " | ".join(str(v) for v in vals)
                    + f" | **{sum(vals)}** | {figs['cumulative'][i]} |")
    return "\n".join([head, rule, *rows])


def _matrix_md(cells: dict[str, list[int]], row_title: str) -> str:
    """Render a route matrix as a Markdown table (screen-reader friendly)."""
    head = f"| {row_title} | " + " | ".join(
        classify.ROUTE_LABELS[r] for r in classify.ROUTES) + " | Total |"
    rule = "|:---|" + "---:|" * (len(classify.ROUTES) + 1)
    rows = [
        f"| {name} | " + " | ".join(str(v) for v in vals) + f" | **{sum(vals)}** |"
        for name, vals in cells.items()
    ]
    return "\n".join([head, rule, *rows])


def build_readme(all_papers: dict[str, list[dict]], figs: dict) -> str:
    total = sum(len(v) for v in all_papers.values())

    def count_route(route: str) -> int:
        n = 0
        for _title, r, _blurb, items in SECTIONS:
            if r != route:
                continue
            for _s, fname in items:
                n += len(all_papers.get(fname, []))
        return n

    n_encoded = count_route("encoded")
    n_informed = count_route("informed")
    n_guided = count_route("guided")
    n_gen = count_route("generative")
    n_soft = count_route("software")
    n_surv = count_route("surveys")
    n_oth = count_route("background")

    lines = []
    lines.append(f"# {SURVEY_TITLE}")
    lines.append("")
    lines.append(
        "This repository hosts the review paper "
        f"*{SURVEY_TITLE}*, with a living catalog of the reviewed papers, "
        "classification and search methods, summary tables, and open-source software list. \n"
        "\n"
        "We welcome contributions from the **whole community** to keep this survey up to date! "
        f"See [**how to contribute**](#{gh_anchor(CONTRIB_HEADING)}).  "
    )
    lines.append("")
    lines.append("The catalog mirrors the taxonomy of the survey: ")
    lines.append("- **physics-guided** inputs / data / representations,")
    lines.append("- **physics-encoded** model architectures,")
    lines.append("- **physics-informed** training losses. ")
    lines.append("")
    lines.append(
        "Within each route, the survey groups papers by application: "
        # "Planning & Prediction" reads better spelled out in prose.
        + ", ".join(f"*{PROSE_APPLICATION.get(a, a.lower())}*"
                    for a in APPLICATIONS if a != "Others")
        + "."
    )
    lines.append("")
    lines.append("## :fire: Updates")
    lines.append("")
    # Newest first: one bullet per month in which post-survey papers were added.
    every = [p for ps in all_papers.values() for p in ps]
    added = [p for p in every if p.get("added")]
    by_month = {}
    for p in added:
        by_month.setdefault(p["added"][:7], []).append(p)
    for ym in sorted(by_month, reverse=True):
        ps = by_month[ym]
        n_m = sum(1 for p in ps if p["is_method"])
        month = _dt.date(int(ym[:4]), int(ym[5:7]), 1).strftime("%b. %Y")
        lines.append(
            f"- **{month}** – Added **{len(ps)}** new papers ({n_m} methods), "
            f"marked :new: in the tables below."
        )
    lines.append(
        f"- **Sep. 2026** – Repository initialized from the survey bibliography: "
        f"all **{total - len(added)}** references cited in the manuscript."
    )
    lines.append(
        f"- The catalog now lists **{total}** references, of which **{figs['n_method']}** are "
        f"physics-embedded robot learning methods (the rest are related surveys, software, "
        f"and background references)."
    )
    prim = figs["primary"]
    n_prim = sum(prim.values()) or 1
    lines.append(
        "- By taxonomy route (each method counted once, under its primary route): "
        + ", ".join(
            f"**{100 * prim[r] / n_prim:.0f}%** {classify.ROUTE_LABELS[r].lower()} ({prim[r]})"
            for r in classify.ROUTES
        )
        + "."
    )
    lines.append("")
    lines.append("## :page_with_curl: Introduction")
    lines.append("")
    lines.append(
        "Robot learning is constrained by scarce real-world data, complex contact dynamics, "
        "and safety requirements. **Physics priors** can act as robotics-specific inductive biases "
        "that complement rather than replace data-driven learning. This repository collects the "
        "papers reviewed in the survey, grouped by *how* physics is embedded."
    )
    lines.append("")
    lines.append("### Types of physics priors")
    lines.append("")
    lines.append(
        "The survey considers the following non-mutually-exclusive families of "
        "physics priors:"
    )
    lines.append("")
    lines.append(
        "1. **Governing equations** — Newton–Euler, Euler–Lagrange, Hamiltonian and "
        "port-Hamiltonian formulations, together with the ODEs and PDEs describing rigid-body "
        "and continuum systems."
    )
    lines.append(
        "2. **Conservation laws, symmetries, and invariances** — conservation of energy, "
        "momentum, and power, together with symmetry, invariance, and equivariance principles "
        "(e.g. SE(3), SO(3), and morphological symmetries)."
    )
    lines.append(
        "3. **Geometric and kinematic structure** — manifolds and Lie groups, kinematic trees, "
        "subsystem decompositions, connectivity and modularity of multi-body systems, and "
        "holonomic and nonholonomic constraints."
    )
    lines.append(
        "4. **Constitutive and interaction models** — friction, contact and impact laws, "
        "stiffness, damping, material behavior, and actuator and drivetrain dynamics."
    )
    lines.append(
        "5. **Physical consistency and admissibility** — positive definiteness of inertia "
        "matrices, positive semi-definiteness of damping matrices, physically meaningful "
        "parameter bounds and sign constraints, passivity, dissipativity, stability properties, "
        "actuator limits, and boundary conditions."
    )
    lines.append("")
    lines.append(
        "> Generic mathematical representations alone are not considered physics priors unless "
        "they explicitly encode physical knowledge."
    )
    lines.append("")
    lines.append("### Robotics applications and platforms")
    lines.append("")
    lines.append(
        "The survey groups the reviewed methods into four application categories:"
    )
    lines.append("")
    lines.append(
        "1. **Dynamics learning** — forward and inverse dynamics, rigid-, soft- and "
        "multi-body system identification, friction and contact modelling, continuum-robot "
        "shape learning, and equation or governing-law discovery."
    )
    lines.append(
        "2. **Trajectory planning and prediction** — path and motion planning, motion and "
        "video prediction, trajectory imitation, planning-oriented policy generation, "
        "geometric planning on manifolds, and generative action prediction."
    )
    lines.append(
        "3. **Control** — trajectory and path tracking, inverse-dynamics control, and "
        "energy-shaping and passivity-based control."
    )
    lines.append(
        "4. **Estimation** — state and parameter estimation, localization, disturbance and "
        "force estimation, fault detection, and condition monitoring."
    )
    lines.append("")
    lines.append(
        "Robot platforms include manipulators, mobile robots, vehicles, legged robots "
        "(quadrupeds and humanoids), soft and continuum robots, collaborative robots, and "
        "underwater and aerial robots. *Canonical mechanical systems* (including pendulums, "
        "cart-poles, acrobots and mechanical oscillators) are reported separately."
    )
    lines.append("")
    lines.append("### Machine learning models and methods")
    lines.append("")
    lines.append(
        "While many reviewed works employ **neural networks**, our survey also covers **Gaussian "
        "process regression**, **kernel methods**, **sparse identification** and **symbolic "
        "regression**, **equation learning**, **Koopman models**, **neural operators**, "
        "**variational integrator networks**, and **generative models** (diffusion models, "
        "vision-language-action models, and video world models), whenever they employ "
        "mechanisms to embed physics priors."
    )
    lines.append("")
    lines.append(
        "**Reinforcement learning** is *excluded* when physics is incorporated exclusively "
        "through RL-specific mechanisms (state or action space design, exploration strategies, "
        "safety constraints, and simulator or environment augmentation), which are reviewed by "
        "Banerjee et al. RL methods are *included* whenever physics is embedded through one of "
        "the three taxonomy routes below."
    )
    lines.append("")
    lines.append("## :compass: Taxonomy")
    lines.append("")
    lines.append(
        "Three complementary routes (adapted from Faroughi et al., 2024, specialised to robot learning):"
    )
    lines.append("")
    lines.extend(_figure(
        "overview_physics_injection", "Levels of embedding physics priors",
        "The three levels at which physics priors enter a learning pipeline: "
        "(a) physics-guided inputs, data, and representations; (b) physics-encoded "
        "architectures; (c) physics-informed loss functions.",
    ))
    lines.append(
        "1. **Physics-guided** — physics priors select, pre-process, or compute input features, "
        "generate or curate training data, or enforce physically consistent representations. "
        "Applied at data curation, or as a pre-processing module whose learnable parts are "
        "pre-trained or frozen; may stay in the pipeline at training and inference."
    )
    lines.append(
        "2. **Physics-encoded** — the model architecture itself enforces physics via tailored "
        "structures, layers, topologies, energy or conservation principles, symmetries, or "
        "architectural constraints. Active during both training and inference."
    )
    lines.append(
        "3. **Physics-informed** — the training objective penalises violations of governing "
        "equations, typically through residual or regularization terms. Formally active only "
        "during training: no effect at inference, since it is part of neither the architecture nor "
        "the inputs."
    )
    lines.append("")
    lines.append(
        "Most existing works use a single route. Jointly using complementary routes may enable a "
        "richer exploitation of prior physical knowledge, but systematic comparisons remain limited."
    )
    lines.append("")
    lines.append("### Lifecycle of physics priors")
    lines.append("")
    lines.extend(_figure(
        "lifecycle", "Lifecycle of physics priors",
        "Physics-guided components act during data curation or as pre-processing modules; "
        "physics-encoded priors stay active at training and inference; physics-informed "
        "losses act only during training.",
    ))
    lines.append(f"## {FLOW_HEADING}")
    lines.append("")
    lines.append(
        "The decision flow below mirrors the one in the survey "
        "(Fig. *Decision flow to classify physics-embedded robot learning approaches*). "
        "A **scope gate** comes first: a method that embeds only generic mathematical "
        "structure, or that is not applied to a robotic system, falls outside the survey. "
        "The three labels are then **not mutually exclusive** — every criterion is "
        "evaluated in sequence and each *Yes* is kept, so a paper may be physics-guided "
        "**and** physics-encoded **and** physics-informed."
    )
    lines.append("")
    lines.append("```mermaid")
    lines.append("flowchart TD")
    lines.append(
        '  Q0["Does the method embed physics priors that express specific physical'
        ' knowledge of a robotic system, rather than generic mathematical structure?"]'
    )
    lines.append('  OUT["Outside the scope of this survey"]')
    lines.append(
        '  Q1["Are any physics priors used to transform, enrich, curate, select, or correct'
        ' the inputs, data, or representations provided to/by the learning model, either'
        ' before training or as pre- or post-processing guidance at inference?"]'
    )
    lines.append('  PG["Physics-Guided"]')
    lines.append(
        '  Q2["Are any physics priors encoded in learning model architectures,'
        ' remaining active during inference?"]'
    )
    lines.append('  PE["Physics-Encoded"]')
    lines.append(
        '  Q3["Are any physics priors incorporated into the training loss,'
        ' and only active during training?"]'
    )
    lines.append('  PI["Physics-Informed"]')
    lines.append(
        '  F["Final classification: Physics-Guided, Physics-Encoded, and/or Physics-Informed"]'
    )
    lines.append("  Q0 -->|Yes| Q1")
    lines.append("  Q0 -->|No| OUT")
    lines.append("  Q1 -->|Yes| PG")
    lines.append("  PG -->|Continue| Q2")
    lines.append("  Q1 -->|No| Q2")
    lines.append("  Q2 -->|Yes| PE")
    lines.append("  PE -->|Continue| Q3")
    lines.append("  Q2 -->|No| Q3")
    lines.append("  Q3 -->|Yes| PI")
    lines.append("  PI -->|Continue| F")
    lines.append("  Q3 -->|No| F")
    # Route colours match the survey figure and every generated plot.
    lines.append(
        f'  classDef guided fill:{classify.ROUTE_FILLS["guided"]},'
        f'stroke:{classify.ROUTE_COLORS["guided"]},'
        f'color:{classify.ROUTE_COLORS["guided"]},stroke-width:2px;'
    )
    lines.append(
        f'  classDef encoded fill:{classify.ROUTE_FILLS["encoded"]},'
        f'stroke:{classify.ROUTE_COLORS["encoded"]},'
        f'color:#7a3200,stroke-width:2px;'
    )
    lines.append(
        f'  classDef informed fill:{classify.ROUTE_FILLS["informed"]},'
        f'stroke:{classify.ROUTE_COLORS["informed"]},'
        f'color:{classify.ROUTE_COLORS["informed"]},stroke-width:2px;'
    )
    lines.append("  classDef out fill:#f2f2f2,stroke:#999,color:#555,stroke-dasharray:4 3;")
    lines.append("  class PG guided;")
    lines.append("  class PE encoded;")
    lines.append("  class PI informed;")
    lines.append("  class OUT out;")
    lines.append("```")
    lines.append("")
    lines.append("## :chart_with_upwards_trend: Publication Timeline")
    lines.append("")
    lines.append("How the reviewed literature evolved over time, by taxonomy route.")
    lines.append("")
    lines.extend(_figure(
        "paper_timeline", "Paper counts by year and route",
        f"{timeline.TIMELINE_START}–{timeline.TIMELINE_END}, "
        f"{figs['n_timeline']} of the {figs['n_method']} reviewed methods"
        + _outside_timeline(figs)
        + ". Each paper is counted once, under its primary route. "
        + _partial_year_note(),
    ))
    lines.append(_timeline_md(figs))
    lines.append("")
    lines.append("## :bar_chart: Coverage by application and platform")
    lines.append("")
    lines.append(
        f"The tables below break the {figs['n_method']} reviewed methods down by "
        "application category and by robot platform. Unlike the timeline, a paper that embeds "
        "physics through several routes is counted in **each** matching column, which is why "
        "row totals can exceed the number of distinct papers."
    )
    lines.append("")
    lines.extend(_figure(
        "papers_by_application_and_robot", "Papers by application and robot platform",
        "Distribution of the reviewed methods by application (left) and robot platform "
        "(right), split by embedding route.",
    ))
    lines.append(_matrix_md(figs["applications"], "Application"))
    lines.append("")
    lines.append(_matrix_md(figs["robots"], "Robot platform"))
    lines.append("")
    lines.append(
        "*__Canonical mechanical systems__ include pendulum, double pendulum, cart-pole, "
        "cart-pendulum, acrobot, inverted pendulum, and mechanical oscillators, which can be "
        "used to model simple robotic systems. "
        "__Other__ covers platforms outside every listed class: "
        "linear-motor and stepper-motor stages, slider-crank mechanisms, generic rigid multi-body "
        "systems, human motion, lower-limb prosthetics, and PDE-solving benchmarks.*"
    )
    lines.append("")
    lines.append(
        "*The two panels are also available separately as "
        "[`papers_by_application.pdf`](figures/papers_by_application.pdf) and "
        "[`papers_by_robot.pdf`](figures/papers_by_robot.pdf). Every generated figure has a "
        "matching `\\input`-able `.tex` fragment for the manuscript.*"
    )
    lines.append("")
    lines.append("## :mag: Search Terms")
    lines.append("")
    lines.append(
        f"The literature on physics-embedded robot learning does not follow a unified "
        f"terminology, so no single query retrieves it. Papers were collected "
        f"through keyword searches on Google Scholar across the categories of "
        f"physics embedding, complemented by backward and forward citation tracking from "
        f"the works found and by the authors' knowledge of the field. The catalog is "
        f"continuously updated with new papers (see [Updates](#fire-updates)). We include "
        f"peer-reviewed journal and conference contributions, plus a few arXiv preprints "
        f"that may not yet be peer-reviewed but contribute significantly to the state of the art."
    )
    lines.append("")
    lines.append(
        "The terms and keywords below are grouped by the aspect of physics embedding they "
        "target. They are the vocabulary of this literature, and are published here so that "
        "the search can be reproduced and extended. Combine them "
        "with a platform or application term to narrow a query."
    )
    lines.append("")
    for group, terms in SEARCH_KEYWORDS.items():
        lines.append(f"<details><summary><b>{group}</b> ({len(terms)} terms)</summary>")
        lines.append("")
        lines.append("".join(f"`{t}` &nbsp; " for t in terms))
        lines.append("")
        lines.append("</details>")
    lines.append("")
    lines.append(
        f"*{sum(len(v) for v in SEARCH_KEYWORDS.values())} terms in "
        f"{len(SEARCH_KEYWORDS)} groups.*"
    )
    lines.append("")
    lines.append(
        f"To classify a new paper, walk the [classification flow](#{gh_anchor(FLOW_HEADING)}) "
        "above. First the scope gate: does the method embed physics priors specific to a "
        "robotic system, rather than generic mathematical structure? If so, does physics "
        "enter via **inputs/data**, via **architecture**, via **loss**, or a combination? "
        "Then **open a pull request** with the `.bib` entry in the matching file under "
        "[`bib/`](bib/)."
    )
    lines.append("")
    lines.append("## Table of contents")
    lines.append("")
    for title, _route, _blurb, items in SECTIONS:
        anchor = gh_anchor(title)
        n = sum(len(all_papers.get(f, [])) for _, f in items)
        lines.append(f"- [{title}](#{anchor}) ({n})")
        for subtitle, fname in items:
            sa = gh_anchor(subtitle)
            lines.append(f"  - [{subtitle}](#{sa}) ({len(all_papers.get(fname, []))})")
    lines.append("")
    lines.append(
        "> [!TIP]\n"
        "> Every paper table below starts expanded. Click the :arrow_forward: arrow "
        "next to a table to fold it away to its heading, which makes scrolling "
        "through the catalog much easier."
    )
    lines.append("")

    for title, _route, blurb, items in SECTIONS:
        lines.append(f"## {title}")
        lines.append("")
        lines.append(blurb)
        lines.append("")
        if title in SECTION_FIGURES:
            name, caption = SECTION_FIGURES[title]
            lines.extend(_figure(name, "Physics-encoded architecture map", caption))
        for subtitle, fname in items:
            papers = all_papers.get(fname, [])
            family = fname[:-4]
            lines.append(f"### {subtitle}")
            lines.append("")
            if SUBSECTION_INTRO.get(family):
                lines.append(SUBSECTION_INTRO[family])
                lines.append("")

            def table(rows: list[dict], label: str, source: str) -> None:
                # Open by default, so the catalog reads normally; the arrow folds
                # the table away to its heading, keeping the README scrollable.
                lines.append("<details open>")
                lines.append(
                    f"<summary><b>{len(rows)} entries</b> from "
                    f"<code>{label}</code> &nbsp;<sub>(click to collapse)</sub></summary>"
                )
                lines.append("")
                lines.append(source)
                lines.append("")
                lines.append("| Paper | Year | Venue |")
                lines.append("|:------|:-----|:------|")
                for row in rows:
                    lines.append(table_row(row))
                lines.append("")
                lines.append("</details>")
                lines.append("")

            src = f"_Source: [`bib/{fname}`](bib/{fname})._"
            groups = classify.GROUPS.get(family)
            if not groups:
                table(papers, f"bib/{fname}", src)
                continue
            # The survey splits this subsection further; mirror its subsubsections.
            # They are h4 so the table of contents, which lists h2/h3, stays short.
            for slug, heading in groups:
                rows = [x for x in papers if x.get("group") == slug]
                lines.append(f"#### {heading}")
                lines.append("")
                if GROUP_INTRO.get(slug):
                    lines.append(GROUP_INTRO[slug])
                    lines.append("")
                if rows:
                    table(rows, f"bib/{fname} &middot; {heading}", src)
                else:
                    lines.append(
                        "_No catalogued papers: the works discussed here are cited in the "
                        "survey narrative and listed under background references._")
                    lines.append("")
            leftover = [x for x in papers if not x.get("group")]
            if leftover:
                lines.append("#### Other")
                lines.append("")
                table(leftover, f"bib/{fname} &middot; other", src)

    lines.append(f"## {CONTRIB_HEADING}")
    lines.append("")
    lines.append(
        "**New papers are very welcome**! You do not need to "
        "install anything, and you do not need to understand the tooling."
    )
    lines.append("")
    lines.append(
        "- **Easiest:** [open an *Add a paper* issue]"
        f"({REPO_URL}/issues/new?template=add_paper.yml) and fill in the form. "
        "A maintainer takes it from there."
    )
    lines.append(
        "- **Pull request:** add one BibTeX entry to the matching file in "
        "[`bib/`](bib/), with the four `survey_*` annotation fields. "
        "[CONTRIBUTING.md](CONTRIBUTING.md) shows a copy-paste template and lists "
        "every allowed label; automated checks then tell you if anything is off."
    )
    lines.append("")
    lines.append(
        "```bibtex\n"
        "@inproceedings{lastname2026keyword,\n"
        "  title   = {A physics-encoded network for contact-rich manipulation},\n"
        "  author  = {Lastname, First and Other, Second},\n"
        "  booktitle = {Conference on Robot Learning (CoRL)},\n"
        "  year    = {2026},\n"
        "  doi     = {10.0000/example},\n"
        "  survey_kind        = {method},\n"
        "  survey_family      = {physics-encoded/model-structured-architectures},\n"
        "  survey_route       = {physics-encoded},\n"
        "  survey_application = {dynamics-learning, control},\n"
        "  survey_robot       = {manipulators},\n"
        "  survey_code        = {https://github.com/example/repo},\n"
        "}\n"
        "```"
    )
    lines.append("")
    lines.append(
        "Use the [classification flow]"
        f"(#{gh_anchor(FLOW_HEADING)}) above to choose the route; a paper may carry "
        "more than one. `bib/*.bib` is the **only** source of truth: this README, "
        "`exports/papers.csv`, and the figures are all generated, so please do not "
        "edit them by hand."
    )
    lines.append("")
    lines.append("Maintainers regenerate everything with:")
    lines.append("")
    lines.append(
        "```bash\n"
        "python3 scripts/validate.py           # check the catalog\n"
        "python3 scripts/build.py              # rebuild README.md + exports/papers.csv\n"
        "python3 scripts/build.py --figures    # ... and the figures (needs pdflatex)\n"
        "```"
    )
    lines.append("")
    lines.append("## License")
    lines.append("")
    lines.append(
        "This repository is released under the [Apache 2.0 license](LICENSE)."
    )
    lines.append("")
    lines.append("## 🤝 Citation")
    lines.append("")
    lines.append(
        f"The survey manuscript *{SURVEY_TITLE}* is under submission. "
        "If you use this catalog, please cite:"
    )
    lines.append("")
    lines.append("```BibTeX")
    lines.append("@article{piccinini2026physicspriors,")
    lines.append("  title   = {Embedding Physics Priors in Robot Learning: A Survey},")
    lines.append("  author  = {Piccinini, Mattia and Schulze, Lucas and Plebe, Alice")
    lines.append("             and Saveriano, Matteo and Beckers, Thomas and Gao, Yuan")
    lines.append("             and Arenz, Oleg and Zarrouki, Baha and Wang, Dingrui")
    lines.append("             and Sch{\\\"a}fer, Finn Rasmus and Peters, Jan and Betz, Johannes")
    lines.append("             and Rosati Papini, Gastone Pietro},")
    lines.append("  year    = {2026},")
    lines.append("  note    = {Under review},")
    lines.append(f"  url     = {{{REPO_URL}}}")
    lines.append("}")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def write_csv(all_papers: dict[str, list[dict]]) -> int:
    """A flat, spreadsheet-friendly view of the catalog."""
    CSV_OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(
        (p for entries in all_papers.values() for p in entries),
        key=lambda p: (p["year"] or 0, p["title"].lower()),
    )
    with CSV_OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["key", "title", "year", "venue", "kind", "family",
                    "routes", "applications", "robots", "link", "code"])
        for p in rows:
            w.writerow([
                p["key"], p["title"], p["year"] or "", p["venue"], p["kind"], p["family"],
                "; ".join(classify.SLUG_FOR_ROUTE[r] for r in classify.ROUTES if r in p["routes"]),
                "; ".join(classify.SLUG_FOR_APPLICATION[a] for a in classify.APPLICATIONS if a in p["apps"]),
                "; ".join(classify.SLUG_FOR_ROBOT[r] for r in classify.ROBOTS if r in p["robots"]),
                p["link"] or "", p["code"] or "",
            ])
    return len(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--figures", action="store_true",
                    help="also regenerate figures/ (requires pdflatex)")
    ap.add_argument("--figures-out", type=Path, default=None, metavar="DIR",
                    help="write the figures somewhere else too, e.g. the manuscript's "
                         "figures/ directory")
    ap.add_argument("--check", action="store_true",
                    help="exit non-zero if README.md is out of date instead of "
                         "rewriting it (used by CI)")
    args = ap.parse_args()

    all_papers, problems = catalog.load(BIB_DIR)
    if problems:
        print("Catalog problems found -- run `python3 scripts/validate.py` for details:")
        for problem in problems[:10]:
            print(f"  - {problem}")
        if len(problems) > 10:
            print(f"  ... and {len(problems) - 10} more")
        return 1

    unlisted = sorted(set(all_papers) - {f for _t, _r, _b, it in SECTIONS for _s, f in it}
                      - set(UNLISTED_BIB))
    if unlisted:
        print("WARNING: bib files with no README section (add them to SECTIONS):")
        for fname in unlisted:
            print(f"  - bib/{fname}")

    figs = timeline.write_all(all_papers, ROOT, compile_pdfs=args.figures)

    text = build_readme(all_papers, figs)
    if args.check:
        current = README.read_text(encoding="utf-8") if README.exists() else ""
        if current != text:
            print("README.md is out of date. Run: python3 scripts/build.py")
            return 1
        print("README.md is up to date.")
        return 0

    README.write_text(text, encoding="utf-8")
    make_contributing.main()
    n_csv = write_csv(all_papers)
    total = sum(len(v) for v in all_papers.values())
    methods = catalog.methods(all_papers)

    print(f"Wrote {README.relative_to(ROOT)} ({total} references, {len(methods)} methods)")
    print(f"Wrote {CSV_OUT.relative_to(ROOT)} ({n_csv} rows)")
    if args.figures:
        for name in (timeline.FIG_TIMELINE, timeline.FIG_APPLICATION,
                     timeline.FIG_ROBOT, timeline.FIG_COMBINED):
            ok = "tex + pdf" if name in figs["pdfs"] else "tex only (pdflatex failed)"
            print(f"  figures/{name}: {ok}")
        if args.figures_out:
            args.figures_out.mkdir(parents=True, exist_ok=True)
            for name in figs["pdfs"]:
                dest = args.figures_out / f"{name}.pdf"
                dest.write_bytes((ROOT / "figures" / f"{name}.pdf").read_bytes())
            print(f"  copied {len(figs['pdfs'])} PDF(s) to {args.figures_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
