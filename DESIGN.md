# Design contract

## 1. Tone and density

Brain Twin is a local experience library for a person collecting a small, deliberate set of source texts. Source evidence is the main content. The workspace is compact, quiet and equally usable in light and dark themes. Avoid decoration and invented progress indicators.

## 2. Tokens and color

`brain_twin/static/tokens.css` is the only literal color source, using `--bt-*`. Light values are defined for `:root` and light subtrees; dark values override the same names. Components reference tokens for color, spacing, type, radius and shadows. The light primary is `#076AAB` and hover is `#075F99` so button text meets 4.5:1; the lighter blue supplied by the base palette was unsuitable as a white-text button background. Main and muted text are checked across all local surfaces in both themes. `text-4` is reserved for non-informative decoration, not body copy.

No charts are present in this alpha. Reserved categorical, sequential, diverging and ordinal tokens do not imply that status colors can be used for chart series. Any future chart needs labels, fixed entity colors and separate axes/panels for different units.

## 3. Typography

Use system sans-serif fonts and the `--bt-fs-*` scale. IDs, counts and JSON use `--bt-mono`. Headings balance lines; paragraphs use pretty wrapping. Do not load external fonts.

## 4. Components

The live inventory is `/styleguide`. Stable classes include `bt-panel`, `bt-ph`, `bt-pb`, `bt-btn`, `bt-input`, `bt-badge`, `bt-chip`, `bt-note`, `bt-error`, `bt-source-card` and `bt-modal`. New pages reuse these components. Errors are shown beside the relevant action. Empty states explain the next action. Native dialogs support Escape, focus containment and focus return.

## 5. Layout

`templates/base.html` owns the page shell, theme/language controls, first-paint theme setup and asset version hashes. The reference page is `templates/index.html` with `static/app.js`. Multi-column grids align at start, and content never creates page-level horizontal scrolling. At 640px the sidebar becomes a compact stacked navigation row. Mobile height uses `dvh`.

## 6. Depth

Static panels use `shadow-1`; the source dialog uses `shadow-3`. Dark themes separate surfaces without card shadows. No gradients or animated layout properties are used.

## 7. Interaction

Only real buttons and links are interactive. Keyboard focus remains visible. Deleting a profile or source asks for confirmation with the consequence. Saving reports success only after the API succeeds. A query shows actual queued/running states and prevents repeat submission of that request. Changing the profile, sources or question invalidates the old answer; a new request and its failure never leave an earlier answer under the new context. Rendering requires matching request identity, question and saved profile version. Data remains plain text even when it contains HTML. Export is explicit: select, preview full contents, download.

## 8. Accessibility and verification

Both themes must meet WCAG 4.5:1 for information-bearing text and primary button text. `tests/test_design_system.py` verifies local contrast and rejects literal component colors, unsafe mobile viewport sizing, layout transitions and non-button click targets. Counterexamples prove the detectors can fail. Real browser smoke tests verify layout, keyboard Escape, XSS-safe text rendering and the main user flow. Screenshots are human-reviewed in desktop and mobile sizes. Reduced-motion preference is respected.

## 9. Contributor entry point

Read this file, the actual reference page and `/styleguide` before changing UI. Run `python -m pytest` and `python scripts/browser_smoke.py` after relevant changes. Update both dictionaries in `static/i18n.js`, both READMEs and screenshots if behavior or layout changes. Do not add a CDN, a front-end build system or a second token source.
