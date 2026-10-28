# Generation review, 2026-10-28

Rendered one sample per profile through `RendererRegistry` (herdr-engineering
working tree, uncommitted) and screenshotted the HTML with headless Chrome.

| Input | Result | Verdict |
|---|---|---|
| document (markdown with list, table, code, link) | `<p>` per line; only `# h1` and `**bold**` handled | Poor: `##`, lists, tables, fences, links, inline code render as raw text |
| web (HTML with remote script and image) | passes through verbatim; check is only "has `<html>`" | Works, but validation says "passed" for active content |
| visualization (JSON) | emitted as `data.json`, no chart | Not a visualization, just a JSON check |
| diagram (Mermaid) | raw source in `<pre>` | Shows source, no diagram |
| presentation | `unsupported artifact profile` (ValueError) | SKILL.md lists it; no structured `unsupported_format` result |
| report (benchmark, incident-audit descriptors) | styled, readable preview with linked findings | Best output; figures and evidence are links only |
| report (plain markdown) | falls back to the weak markdown path | Same gaps as document |
| invalid visualization / web | clear error | Fine |

## Improvements, by priority
1. Replace the hand-rolled markdown renderer with a real one (sanitised); add the same page CSS the report preview uses.
2. Return `{"status":"unsupported_format"}` as SKILL.md promises, instead of raising.
3. Diagram: render Mermaid to SVG in the sandboxed worker; visualization: render a chart from a small spec.
4. Web validation should report external-resource/script findings rather than a flat pass.
5. Implement or drop `presentation` in SKILL.md.
6. The runtime (`artifact_*` modules, `artifact_reports_client.py`, migrations 0003-0008) is untracked in herdr-engineering and origin/main has renumbered migrations; land it before the skill's report commands can work.

## Update (same day)
Runtime port: report layer ported onto origin/main in herdr-engineering branch
`feat/artifact-reports-port` (worktree `.worktrees/artifact-reports-port`, not pushed).
Items 1, 2 and 4 are done there: stdlib markdown renderer (headings, lists, tables,
fences, links, inline code; raw HTML escaped; unsafe link schemes left as text),
`ArtifactRendererError.code == "unsupported_format"` recorded in job errors, and web
`validation.findings` for scripts and external resources. Still open: Mermaid-to-SVG,
chart rendering, the presentation profile, and porting the web client (`client.js`,
`artifacts-view.js`) and Playwright tests.

## Update 2 (same day)
Charts (bar/line spec), Mermaid flowcharts and markdown slide decks now render in
`feat/artifact-renderers-svg` (herdr-engineering PR stacked on #348); `presentation`
is supported. Remaining gaps: non-flowchart Mermaid, multi-series charts, edge routing
around nodes, and a dark-mode palette for the SVG output.
