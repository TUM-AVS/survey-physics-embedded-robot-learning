#!/usr/bin/env python3
"""The survey's controlled vocabulary.

Every value a contributor may put in a ``survey_*`` BibTeX field is listed here.
`validate.py` rejects anything else, so this file is the single place to look up
(or extend) the allowed labels.

Adding a label is a deliberate act: it changes the survey's taxonomy, so open an
issue first rather than inventing a value in a pull request.
"""
from __future__ import annotations

# --------------------------------------------------------------- embedding routes ---
# How the physics prior enters the learning algorithm.  A paper may use more
# than one route; `primary_route` picks one where the counts must not double.
ROUTES = ("guided", "encoded", "informed")

ROUTE_SLUG = {
    "physics-guided": "guided",
    "physics-encoded": "encoded",
    "physics-informed": "informed",
}
SLUG_FOR_ROUTE = {v: k for k, v in ROUTE_SLUG.items()}

ROUTE_LABELS = {
    "guided": "Physics-guided",
    "encoded": "Physics-encoded",
    "informed": "Physics-informed",
}

# Colours shared by every generated figure: a saturated outline plus a light fill.
ROUTE_COLORS = {"guided": "#008000", "encoded": "#d45500", "informed": "#0000ff"}
ROUTE_FILLS = {"guided": "#87e087", "encoded": "#f2a97c", "informed": "#9aa8f5"}

ROUTE_HELP = {
    "guided": "Physics shapes the inputs, data, or representations the model sees "
              "(structured features, geometric coordinates, spectra, curated or "
              "simulated data, frozen physics pre-processing, inference-time guidance).",
    "encoded": "Physics is built into the function class itself: layers, energies, "
               "kernels, topologies, or integrators that stay active during both "
               "training and inference.",
    "informed": "Physics enters only through the training objective, as a residual, "
                "energy, or consistency penalty. The architecture and inputs stay generic.",
}

# ----------------------------------------------------------------- applications ---
APPLICATIONS = (
    "Dynamics Learning",
    "Planning & Prediction",
    "Control",
    "Estimation",
    "Others",
)

APPLICATION_SLUG = {
    "dynamics-learning": "Dynamics Learning",
    "planning-and-prediction": "Planning & Prediction",
    "control": "Control",
    "estimation": "Estimation",
    "other": "Others",
}
SLUG_FOR_APPLICATION = {v: k for k, v in APPLICATION_SLUG.items()}

APPLICATION_HELP = {
    "dynamics-learning": "Forward/inverse dynamics, rigid-, soft-, and multi-body models, "
                         "contact and friction, residual dynamics, system identification.",
    "planning-and-prediction": "Motion and trajectory planning, motion primitives, "
                               "trajectory forecasting, world models, generative planning.",
    "control": "Model-based and learning-based control, MPC, policy learning, "
               "stability- and passivity-aware control.",
    "estimation": "State and parameter estimation, filtering, observers, "
                  "sensor fusion, virtual sensing.",
    "other": "Anything the four categories above do not cover.",
}

# ------------------------------------------------------------------ robot classes ---
ROBOTS = (
    "Manipulators",
    "Mobile robots",
    "Vehicles",
    "Legged robots",
    "Aerial robots",
    "Underwater robots",
    "Soft & continuum robots",
    "Collaborative robots",
    "Canonical mechanical systems",
    "Other",
)

ROBOT_SLUG = {
    "manipulators": "Manipulators",
    "mobile-robots": "Mobile robots",
    "vehicles": "Vehicles",
    "legged-robots": "Legged robots",
    "aerial-robots": "Aerial robots",
    "underwater-robots": "Underwater robots",
    "soft-and-continuum-robots": "Soft & continuum robots",
    "collaborative-robots": "Collaborative robots",
    "canonical-mechanical-systems": "Canonical mechanical systems",
    "other": "Other",
}
SLUG_FOR_ROBOT = {v: k for k, v in ROBOT_SLUG.items()}

ROBOT_HELP = {
    "manipulators": "Fixed-base robot arms.",
    "mobile-robots": "Wheeled or tracked ground robots, excluding road vehicles.",
    "vehicles": "Cars, trucks, and other road or racing vehicles.",
    "legged-robots": "Quadrupeds, bipeds, and humanoids.",
    "aerial-robots": "Quadrotors, fixed-wing, and other UAVs.",
    "underwater-robots": "AUVs, ROVs, and other marine platforms.",
    "soft-and-continuum-robots": "Soft actuators, continuum arms, deformable bodies.",
    "collaborative-robots": "Human-robot interaction and collaboration setups.",
    "canonical-mechanical-systems": "Pendulums, double pendulums, cart-poles, acrobots, "
                                    "mass-spring-damper and similar benchmark systems.",
    "other": "Motors, drivetrains, and any platform the classes above do not cover.",
    "none": "Methodology paper validated on no specific platform.",
}

# ----------------------------------------------------------------- entry kinds ---
# What role the reference plays in the survey.  Only `method` entries are
# counted in the statistics and figures.
KINDS = ("method", "software", "survey", "background")

KIND_HELP = {
    "method": "A physics-embedded robot-learning method reviewed by the survey. "
              "Requires survey_route and survey_application.",
    "software": "An open-source library, framework, or differentiable simulator.",
    "survey": "A related survey or review.",
    "background": "A foundational or historical reference cited for context, "
                  "not itself a reviewed method.",
}

# ------------------------------------------------------------------- families ---
# One file per family under bib/.  The family fixes which file an entry lives in
# and which survey subsection it belongs to; it does NOT fix the route, which is
# stated per entry.
FAMILIES = {
    "lagrangian": "Lagrangian Learning Models (DeLaN / LNN)",
    "hamiltonian": "Hamiltonian Learning Models (HNN / port-Hamiltonian)",
    "model-structured": "Model-Structured Learning Architectures (MSNNs)",
    "neural-ode": "Neural ODEs and Variational Integrator Networks",
    "non-nn": "Non-NN Physics-Structured Models (GPR / RKHS / kernels)",
    "hybrid-physics": "Hybrid Physics-Learning Architectures",
    "topology-learning": "Physics-Encoded Topology Learning (SINDy / equation learners)",
    "neural-operators": "Neural Operators (Koopman / DeepONet / FNO / PINO)",
    "other-encoded": "Other Types of Physics-Encoded Architectures",
    "physics-informed-losses": "Physics-Informed Neural Networks and Losses",
    "physics-guided-inputs": "Structured Inputs, Geometry, Frequency Domain, World Models",
    "generative-models": "Diffusion Models, World Models, and VLAs",
    "software": "Libraries and Differentiable Simulators",
    "surveys": "Related Surveys",
    "background": "Background and Historical References",
}


def primary_route(paper: dict) -> str | None:
    """Single route per paper, for counts whose parts must sum to the total.

    Precedence follows how strongly the prior constrains the model: a paper that
    both encodes physics in its architecture and adds a physics loss is counted
    as physics-encoded.
    """
    for route in ("encoded", "informed", "guided"):
        if route in paper.get("routes", ()):
            return route
    return None


def matrix(papers, rows: tuple[str, ...], field: str) -> dict[str, list[int]]:
    """rows x routes count matrix, e.g. applications against embedding routes."""
    cells = {r: [0, 0, 0] for r in rows}
    for paper in papers:
        for value in paper.get(field, ()):
            if value not in cells:
                continue
            for i, route in enumerate(ROUTES):
                if route in paper.get("routes", ()):
                    cells[value][i] += 1
    return cells
