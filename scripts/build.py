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
# Literature cut-off stated in Sec. "Scope of the Considered Literature".
CUTOFF = "August 2026"

# Heading of the decision-flow section, which the survey (Sec. "Classification
# Flow" and Sec. "Scope of the Considered Literature") promises this repo hosts.
FLOW_HEADING = ":twisted_rightwards_arrows: Classification flow"

SECTIONS = [
    (
        "Physics-Encoded Architectures",
        "encoded",
        "Physics enters through the *function class*: layers, energies, kernels, topologies, "
        "or integrators that enforce physical structure. Physics-encoded components stay active "
        "during **both training and inference**. Survey Sec. *Physics-Encoded Architectures* — "
        "the largest body of work, and therefore reviewed first.",
        [
            ("Lagrangian Learning Models (DeLaN / LNN)", "lagrangian.bib"),
            ("Hamiltonian Learning Models (HNN / port-Hamiltonian / symplectic)", "hamiltonian.bib"),
            ("Model-Structured Learning Architectures (MSNNs)", "model-structured.bib"),
            ("Neural ODEs and Variational Integrator Networks", "neural-ode.bib"),
            ("Non-NN Physics-Structured Models (GPR / RKHS / kernels)", "non-nn.bib"),
            ("Hybrid Physics-Learning Architectures", "hybrid-physics.bib"),
            ("Physics-Encoded Topology Learning (SINDy / equation learners)", "topology-learning.bib"),
            ("Neural Operators (Koopman / DeepONet / FNO / PINO)", "neural-operators.bib"),
            ("Other Types of Physics-Encoded Architectures", "other-encoded.bib"),
        ],
    ),
    (
        "Physics-Informed Loss Functions",
        "informed",
        "A generic model is trained with a residual / energy / consistency penalty derived from "
        "governing equations. Physics-informed components are active **only during training**: "
        "they are part of neither the architecture nor the inputs. Survey Sec. "
        "*Physics-Informed Loss Functions* (PINNs, physics-informed neural operators, "
        "other loss and reward functions).",
        [
            ("Physics-Informed Neural Networks and Losses", "physics-informed-losses.bib"),
        ],
    ),
    (
        "Physics-Guided Inputs, Data, and Representations",
        "guided",
        "Physics shapes the features, coordinates, spectra, representations, or training data that "
        "the model sees — either at data curation, or as a pre-trained / frozen pre-processing module. "
        "Survey Sec. *Physics-Guided Inputs, Data, and Representations* (structured inputs, "
        "physics-guided features and data, geometric learning, frequency-domain learning, "
        "physically consistent world representations, diffusion-based generation, neural operators).",
        [
            ("Structured Inputs, Geometric, Frequency-Domain, and World Representations", "physics-guided-inputs.bib"),
        ],
    ),
    (
        "Generative Models with Physics Priors (Cross-Cutting)",
        "generative",
        "Diffusion policies, video world models, and VLAs are **not a fourth route**: they are "
        "reviewed throughout the survey and may embed physics via any of the three routes. "
        "See the survey table *Summary of generative-model approaches*, which marks P.E. / P.I. / P.G. "
        "per paper.",
        [
            ("Diffusion, World Models, and VLAs", "generative-models.bib"),
        ],
    ),
    (
        "Software, Simulators, and Libraries",
        "software",
        "Open-source tools used to build physics-embedded robot-learning models. "
        "Survey Sec. *Software Tools* (physics-informed ML frameworks, neural differential "
        "equations, equation discovery and system identification, differentiable simulators, "
        "model-structured and hybrid physics-neural frameworks).",
        [
            ("Libraries and Differentiable Simulators", "software.bib"),
        ],
    ),
    (
        "Related Surveys",
        "surveys",
        "Neighbouring reviews (physics-informed ML, structured models, world models, PI-RL), "
        "compared against this survey in Sec. *Related Surveys*.",
        [
            ("Surveys", "surveys.bib"),
        ],
    ),
    (
        "Background and Historical References",
        "background",
        "Textbooks, deep-learning primers, and historical NN/robotics citations used in the survey "
        "narrative and in Sec. *Historical Perspective: From Analytical Models to "
        "Physics-Embedded Learning*.",
        [
            ("Other references", "background.bib"),
        ],
    ),
]

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
        "Sub-categories of physics-encoded robot learning architectures "
        "(Fig. 4 of the survey).",
    ),
}



def table_row(p: dict) -> str:
    title = md_escape(p["title"])
    if p["link"]:
        paper = f"[{title}]({p['link']})"
    else:
        paper = title
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


def _timeline_md(figs: dict) -> str:
    """Yearly counts as a Markdown table (GitHub cannot render the PDF inline)."""
    head = "| Year | " + " | ".join(
        classify.ROUTE_LABELS[r] for r in classify.ROUTES) + " | Total | Cumulative |"
    rule = "|:---|" + "---:|" * (len(classify.ROUTES) + 2)
    rows = []
    for i, year in enumerate(figs["years"]):
        vals = [figs["series"][r][i] for r in classify.ROUTES]
        rows.append(f"| {year} | " + " | ".join(str(v) for v in vals)
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
        f"This repository ([{REPO_URL.replace('https://', '')}]({REPO_URL})) hosts the survey "
        f"*{SURVEY_TITLE}*, with a living catalog of the reviewed papers, "
        "classification and search methods, summary tables, and open-source software list. \n"
        "We welcome contributions from the **whole community** to keep this survey up to date!  "
    )
    lines.append("")
    lines.append(
        "The catalog mirrors the taxonomy of the survey: "
        "**physics-guided** inputs / data / representations, "
        "**physics-encoded** model architectures, and "
        "**physics-informed** training losses. "
        "Within each route, the survey groups papers by application: "
        # "Planning & Prediction" reads better spelled out in prose.
        + ", ".join(f"*{PROSE_APPLICATION.get(a, a.lower())}*"
                    for a in APPLICATIONS if a != "Others")
        + "."
    )
    lines.append("")
    lines.append("## :fire: Updates")
    lines.append("")
    lines.append(
        f"- **Sep. 2026** – Repository initialized from the survey bibliography: "
        f"all **{total}** references cited in the manuscript."
    )
    lines.append(
        f"- Of these, **{figs['n_method']}** are physics-embedded robot learning methods "
        f"(the rest are related surveys, software, and background references)."
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
    lines.append(
        f"- By bibliography group: {n_encoded} physics-encoded, {n_informed} physics-informed loss, "
        f"{n_guided} physics-guided inputs/data, {n_gen} generative models, "
        f"{n_soft} software, {n_surv} related surveys, {n_oth} background."
    )
    lines.append("")
    lines.append("## :page_with_curl: Introduction")
    lines.append("")
    lines.append(
        "Robot learning is constrained by scarce real-world data, complex contact dynamics, "
        "and safety requirements. **Physics priors** act as robotics-specific inductive biases "
        "that complement rather than replace data-driven learning. This repository collects the "
        "papers reviewed in the survey, grouped by *how* physics is embedded."
    )
    lines.append("")
    lines.append("### Types of physics priors")
    lines.append("")
    lines.append(
        "The survey considers five non-mutually-exclusive families of physics priors "
        "(Sec. *Scope of the Considered Literature*):"
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
        "The survey groups the reviewed methods into four application categories "
        "(Sec. *Scope of the Considered Literature*):"
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
        "underwater and aerial robots. *Canonical mechanical systems* — pendulums, "
        "cart-poles, acrobots and mechanical oscillators — are reported separately, since "
        "they are standard benchmarks rather than robot platforms."
    )
    lines.append("")
    lines.append("### Machine learning models and methods")
    lines.append("")
    lines.append(
        "Most reviewed works employ **neural networks**. The survey also covers **Gaussian "
        "process regression** and **kernel methods**, **sparse identification** and **symbolic "
        "regression**, **equation learning**, **Koopman models**, **neural operators**, "
        "**variational integrator networks**, and **generative models** (diffusion models, "
        "vision-language-action models, and video world models) — whenever they employ "
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
        "equations, typically through residual or regularization terms. Active **only during "
        "training**: no effect at inference, since it is part of neither the architecture nor "
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
        "physics-encoded priors stay active at training **and** inference; physics-informed "
        "losses act **only** during training.",
    ))
    lines.append(f"## {FLOW_HEADING}")
    lines.append("")
    lines.append(
        "The decision flow below is the one used in the survey. The three labels are "
        "**not mutually exclusive**: evaluate every criterion in sequence and keep each *Yes*, "
        "so a paper may be guided **and** encoded **and** informed."
    )
    lines.append("")
    lines.append("```mermaid")
    lines.append("flowchart TD")
    lines.append(
        '  Q1["Are physics priors used to transform, curate, enrich, or select input features,'
        ' data or representations, before training the main model?"]'
    )
    lines.append('  PG["Physics-Guided"]')
    lines.append(
        '  Q2["Are physics priors encoded in the learning model architecture,'
        ' remaining active during inference?"]'
    )
    lines.append('  PE["Physics-Encoded"]')
    lines.append(
        '  Q3["Are physics priors incorporated into the training loss,'
        ' and only active during training?"]'
    )
    lines.append('  PI["Physics-Informed"]')
    lines.append(
        '  F["Final classification: Physics-Guided, Physics-Encoded, and/or Physics-Informed"]'
    )
    lines.append("  Q1 -->|Yes| PG")
    lines.append("  PG -->|Continue| Q2")
    lines.append("  Q1 -->|No| Q2")
    lines.append("  Q2 -->|Yes| PE")
    lines.append("  PE -->|Continue| Q3")
    lines.append("  Q2 -->|No| Q3")
    lines.append("  Q3 -->|Yes| PI")
    lines.append("  PI -->|Continue| F")
    lines.append("  Q3 -->|No| F")
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
        + (f" ({figs['n_pre']} earlier ones are listed in the tables below)"
           if figs["n_pre"] else "")
        + ". Each paper is counted once, under its primary route. "
        "\\*2026 covers publications up to August 2026 only.",
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
        "*__Canonical mechanical systems__ are the low-DoF textbook testbeds used in place of a "
        "robot: pendulum, double pendulum, cart-pole, cart-pendulum, acrobot, inverted pendulum, "
        "and mechanical oscillators. __Other__ covers platforms outside every listed class: "
        "linear-motor and stepper-motor stages, slider-crank mechanisms, generic rigid multi-body "
        "systems, human motion, lower-limb prosthetics, and PDE-solving benchmarks. Methodology "
        "papers with no robot platform (`Brunton2016`, `Clawson2014`, `Chen2021_physics`, "
        "`Zolman2025`) are excluded from this figure but retained in the application figure.*"
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
        f"terminology, so no single query retrieves it. Papers were collected up to "
        f"**{CUTOFF}** through keyword searches on Google Scholar across the categories of "
        f"physics embedding, complemented by backward and forward citation tracking from "
        f"the works found and by the authors' knowledge of the field. We include "
        f"peer-reviewed journal and conference contributions, plus a few arXiv preprints "
        f"that are not yet peer-reviewed but contribute significantly to the state of the art."
    )
    lines.append("")
    lines.append(
        "The terms below are grouped by the aspect of physics embedding they target. They "
        "are the vocabulary of this literature, and are published here so that the search "
        "can be reproduced and extended: **they retrieve 74% of the reviewed methods by "
        "title alone**, and more once abstracts and full text are matched. Combine them "
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
        "**Out of scope:** reinforcement learning in which physics enters *only* through "
        "RL-specific mechanisms — state or action space design, exploration strategies, "
        "safety constraints, simulator or environment augmentation — which is reviewed by "
        "Banerjee et al.; and physics-embedded learning outside robotics (fluid, solid and "
        "continuum mechanics), which is covered by the related surveys below."
    )
    lines.append("")
    lines.append(
        f"To classify a new paper, walk the [classification flow](#{gh_anchor(FLOW_HEADING)}) "
        "above: does physics enter via **inputs/data**, via **architecture**, via **loss**, "
        "or a combination? Then open a pull request with the `.bib` entry in the matching "
        "file under [`bib/`](bib/)."
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
            lines.append(f"### {subtitle}")
            lines.append("")
            # Open by default, so the catalog reads normally; the arrow folds the
            # table away to its heading, which makes the README scrollable.
            lines.append("<details open>")
            lines.append(
                f"<summary><b>{len(papers)} entries</b> from "
                f"<code>bib/{fname}</code> &nbsp;<sub>(click to collapse)</sub></summary>"
            )
            lines.append("")
            lines.append(f"_Source: [`bib/{fname}`](bib/{fname})._")
            lines.append("")
            lines.append("| Paper | Year | Venue |")
            lines.append("|:------|:-----|:------|")
            for p in papers:
                lines.append(table_row(p))
            lines.append("")
            lines.append("</details>")
            lines.append("")

    lines.append("## Contributing")
    lines.append("")
    lines.append(
        "**New papers are very welcome** — including your own. You do not need to "
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
        "  survey_family      = {model-structured},\n"
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

    unlisted = sorted(set(all_papers) - {f for _t, _r, _b, it in SECTIONS for _s, f in it})
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
