# Contributing

Thanks for helping keep this catalog current. **Adding a paper is meant to take
two minutes**, and you do not need to install anything.

## Two ways to contribute

### 1. Open an issue (no git required)

Use the **[Add a paper](https://github.com/TUM-AVS/survey-physics-embedded-robot-learning/issues/new?template=add_paper.yml)** issue form. Paste the BibTeX, pick the labels
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
@inproceedings{lastname2026keyword,
  title   = {A physics-encoded network for contact-rich manipulation},
  author  = {Lastname, First and Other, Second},
  booktitle = {Conference on Robot Learning (CoRL)},
  year    = {2026},
  doi     = {10.0000/example},
  survey_kind        = {method},
  survey_family      = {model-structured},
  survey_route       = {physics-encoded},
  survey_application = {dynamics-learning, control},
  survey_robot       = {manipulators},
  survey_code        = {https://github.com/example/repo},
}
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
| `lagrangian.bib` | Lagrangian Learning Models (DeLaN / LNN) |
| `hamiltonian.bib` | Hamiltonian Learning Models (HNN / port-Hamiltonian) |
| `model-structured.bib` | Model-Structured Learning Architectures (MSNNs) |
| `neural-ode.bib` | Neural ODEs and Variational Integrator Networks |
| `non-nn.bib` | Non-NN Physics-Structured Models (GPR / RKHS / kernels) |
| `hybrid-physics.bib` | Hybrid Physics-Learning Architectures |
| `topology-learning.bib` | Physics-Encoded Topology Learning (SINDy / equation learners) |
| `neural-operators.bib` | Neural Operators (Koopman / DeepONet / FNO / PINO) |
| `other-encoded.bib` | Other Types of Physics-Encoded Architectures |
| `physics-informed-losses.bib` | Physics-Informed Neural Networks and Losses |
| `physics-guided-inputs.bib` | Structured Inputs, Geometry, Frequency Domain, World Models |
| `generative-models.bib` | Diffusion Models, World Models, and VLAs |
| `software.bib` | Libraries and Differentiable Simulators |
| `surveys.bib` | Related Surveys |
| `background.bib` | Background and Historical References |

## The `survey_*` fields

### `survey_kind` (required)

Only `method` entries are counted in the statistics and figures.

| value | meaning |
| --- | --- |
| `method` | A physics-embedded robot-learning method reviewed by the survey. Requires survey_route and survey_application. |
| `software` | An open-source library, framework, or differentiable simulator. |
| `survey` | A related survey or review. |
| `background` | A foundational or historical reference cited for context, not itself a reviewed method. |

### `survey_route` (required for methods)

**How** the physics prior enters the learning algorithm — the survey's central
question. List several, comma-separated, if the paper genuinely uses more than
one.

| value | meaning |
| --- | --- |
| `physics-guided` | Physics shapes the inputs, data, or representations the model sees (structured features, geometric coordinates, spectra, curated or simulated data, frozen physics pre-processing, inference-time guidance). |
| `physics-encoded` | Physics is built into the function class itself: layers, energies, kernels, topologies, or integrators that stay active during both training and inference. |
| `physics-informed` | Physics enters only through the training objective, as a residual, energy, or consistency penalty. The architecture and inputs stay generic. |

Not sure? A quick test: if you deleted the physics at test time and the network
still ran unchanged, it was physics-informed (loss only). If the inputs change
but the architecture does not, it is physics-guided. If the architecture itself
enforces the physics, it is physics-encoded.

### `survey_application` (required for methods)

What the method is *for*. Several values are allowed.

| value | meaning |
| --- | --- |
| `dynamics-learning` | Forward/inverse dynamics, rigid-, soft-, and multi-body models, contact and friction, residual dynamics, system identification. |
| `planning-and-prediction` | Motion and trajectory planning, motion primitives, trajectory forecasting, world models, generative planning. |
| `control` | Model-based and learning-based control, MPC, policy learning, stability- and passivity-aware control. |
| `estimation` | State and parameter estimation, filtering, observers, sensor fusion, virtual sensing. |
| `other` | Anything the four categories above do not cover. |

### `survey_robot` (required for methods)

Which platform the paper actually reports results on — not what it could apply
to in principle. Several values are allowed. Use `none` for a methodology paper
with no specific platform.

| value | meaning |
| --- | --- |
| `manipulators` | Fixed-base robot arms. |
| `mobile-robots` | Wheeled or tracked ground robots, excluding road vehicles. |
| `vehicles` | Cars, trucks, and other road or racing vehicles. |
| `legged-robots` | Quadrupeds, bipeds, and humanoids. |
| `aerial-robots` | Quadrotors, fixed-wing, and other UAVs. |
| `underwater-robots` | AUVs, ROVs, and other marine platforms. |
| `soft-and-continuum-robots` | Soft actuators, continuum arms, deformable bodies. |
| `collaborative-robots` | Human-robot interaction and collaboration setups. |
| `canonical-mechanical-systems` | Pendulums, double pendulums, cart-poles, acrobots, mass-spring-damper and similar benchmark systems. |
| `other` | Motors, drivetrains, and any platform the classes above do not cover. |
| `none` | Methodology paper validated on no specific platform. |

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
genuinely useful feedback on the taxonomy itself.

## Code of conduct

Be decent to each other. Discussions about whether a paper belongs in a category
are welcome and expected; the taxonomy is a proposal, not a verdict.
