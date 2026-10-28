# Evidence-based report workflow

Use this workflow for a report whose purpose is to help a reader understand an
investigation and choose what to do next. It applies to quantitative comparisons,
qualitative audits, simulations, operational investigations, and mixed evidence.
It does not prescribe a scientific domain, a particular scorer, or a fixed layout.

## Establish the question and preserve the evidence

Identify the intended reader, the question or decision, the available evidence,
and what remains untested. Reuse context already supplied by the user. Ask only
when a missing decision materially affects the result.

Distinguish observed measurements, derived quantities, interpretations, and
proposed actions. Domain analysis code or an explicitly recorded method computes
the quantities. Do not infer absent measurements, units, identity labels,
uncertainty, or success criteria from a convenient presentation template.

For comparisons, record the baseline, alternatives, evaluation population, units,
denominators, selection rules, and relevant configuration. Declare the reference
comparison before interpreting a parameter sweep. If the same evidence selected
the candidate and evaluated it, describe the finding as exploratory; propose a
separate evaluation where appropriate. Show unfavorable and unavailable outcomes
alongside favorable ones. Different populations or evaluation conditions need an
explicit qualification, not an unexplained score subtraction.

For a qualitative investigation, cite the observations or examples supporting a
claim and describe coverage and competing explanations. Do not add numeric
confidence or a significance test merely to fill a quantitative report section.

## Make the report understandable and useful

Scale the detail to the investigation. A useful report usually includes:

- A short account of the question, findings, and unresolved decision.
- A reading order and definitions for terms or metrics the audience may not know.
- An explanation of methods, data coverage, comparisons, and missing evidence.
- Findings linked to specific figures, tables, records, or computation runs.
- Limitations and plausible competing explanations.
- Concrete next checks or experiments, with the evidence that would distinguish
  explanations or justify changing the current approach.

For each substantive finding, make these relationships explicit:

**Observation → supporting evidence → interpretation and limits → next check.**

A next check might request missing data, inspect named records, compare controls,
repeat a measurement, or validate a frozen candidate on fresh observations. It
is not authorization to execute an operational change, alter source data, deploy
software, or make the artifact public. A recommendation should make clear which
of those steps is proposed and which, if any, has actually happened.

Explain each important visualization near the figure:

- What question it addresses and what its axes, units, colors, and symbols mean.
- Which observations are included, sampled, omitted, or capped for display.
- How missing values differ from measured zero, failure, or an untested case.
- What the reader can conclude, what they cannot conclude, and what to inspect next.

Keep source identifiers available so readers can investigate particular changes.
Include a current/baseline reference in a comparison plot when readers need it,
even if it would fall outside a highest-value display subset. State normalization
and transformations so display scaling is not mistaken for measured magnitude.
Do not invent error bars, distributions, or causal explanations from aggregate
summaries. A descriptive difference is not automatically practically meaningful,
statistically established, or evidence that a proposed action is safe.

## Preserve an editable, reproducible package

Organize the following roles using the manifest and blob-reference features the
installed artifact API actually supports. These are logical roles, not a new wire
schema or a requirement that every report use the same filenames:

| Role | Preserve when applicable |
| --- | --- |
| Reader entry point | Rendered HTML/document and its required assets |
| Editable source | Templates, narrative source, analysis adapter, relevant dependency/toolchain information |
| Evidence | Authorized input snapshots or pinned references, result tables, data behind figures |
| Interpretation | Findings, evidence references, caveats, and proposed follow-up |
| Provenance | Input hashes/versions, configuration, code revision or source hashes, execution and rendering context |
| Validation | Checks performed, outcomes, limitations, and any visual review evidence |

Keep large data, figures, and source as separately referenced blobs or pinned
artifact dependencies when supported. Do not inline a large dataset into job JSON
or event messages to work around a missing import feature. Preserve complete
supporting evidence separately from bounded previews, and report coverage limits.
Exclude unrelated files and credentials rather than recursively uploading a
worktree. Preserve only source/input material authorized for this artifact.

When updating explanations without rerunning the analysis, preserve the original
measurements, results, configuration, and analysis provenance. Record the new
explanation/render source and any newly computed descriptive summaries separately.
Do not imply that analysis or independent validation ran again. A later analysis
run or revised dataset is new evidence and must be identified as such.

## Use the registry through verified capabilities

For the native descriptor implementation, follow the
[report command reference](report-commands.md), including its bundled schema and
cross-domain examples. Existing rich reports may require a different supported
import path: a descriptor preview preserves interpretation and links, while full
figures, evidence, and source remain separate assets.

1. Search for an existing logical artifact before creating a duplicate. Distinct
   reports may be separate artifacts in a collection; revisions of the same report
   should retain its logical identity and immutable history.
2. Resolve available authenticated principal and harness context. Omit unknown
   optional context; if the API requires unavailable identity or authorization,
   report the blocker. Do not infer IDs from directory names or titles.
3. Check actual upload limits, linked-asset/import support, profile behavior,
   validation, and private preview capabilities. A `report` profile name alone
   does not establish that it accepts HTML or preserves a multi-file package.
4. Import authorized existing source/output through the supported authenticated
   path, or submit a build job to the supported worker. Keep registry rendering
   and analysis execution at the worker/sandbox boundary; a skill is not a license
   to execute arbitrary source in the browser or control-plane request handler.
5. Commit a revision with the exact base version and idempotency key. Preserve
   input dependencies, source, outputs, and validation evidence in the version.
6. Return the actual artifact/version IDs and an authorized private view/reference
   only after the registry confirms them. If only a local package is prepared,
   report that status and the missing capability; do not call it registered,
   validated, viewable in the dashboard, or publicly shared.

Use another supported renderer only when it preserves the user's requested
format and package semantics, and explain the choice. Do not silently turn a rich
report into a Markdown document or treat an uploaded archive as a working browser
preview. Unsupported capabilities need a bounded handoff to the artifact runtime,
not fabricated CLI commands or an alternate public hosting service.

## Validate for the intended use

Validate what is relevant to the artifact: manifest/blob integrity, source and
output hashes, referenced assets, figure/table reconciliation, traceable findings,
comparison denominators, missing-data handling, and rendering/interaction checks.
Inspect representative output visually where layout or chart legibility matters.
Distinguish a format/schema check from verification of the analysis or its claims.
Retain the actual evidence; do not mark unperformed checks as passed.

For example, an investigation comparing two processing methods might package the
data, methods, baseline/alternative results, explanatory figures, and a proposal
for a fresh evaluation. A qualitative incident review might instead package a
timeline, cited observations, competing causes, and diagnostic follow-ups. Their
artifact lifecycle is shared; their calculations and decision policies are not.
