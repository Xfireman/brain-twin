# Security boundaries

Brain Twin is a local single-user alpha. Bind it only to loopback; do not expose it through a public tunnel, reverse proxy or shared server. It has no login or tenant isolation. Any process with access to your account and local data directory can read the library. Source text is not encrypted at rest.

## What the application does

- Accepts text and JSON supplied by the user. It never fetches source URLs or loads paths embedded in imported data.
- Restricts the browser Host to localhost and loopback IP addresses to reduce DNS rebinding exposure.
- Requires a session CSRF token on JSON writes and rejects mismatched Origin and cross-site Fetch Metadata. Its `brain_twin_session` cookie is distinct from the default Flask session cookie used by neighboring local applications; browser cookies are not isolated by port.
- Uses text nodes for user and model output, Jinja autoescaping, a nonce-based Content Security Policy, `nosniff`, strict same-site cookies and no external browser resources.
- Reads model configuration at startup. A request cannot choose the upstream URL. Remote providers require HTTPS; HTTP is limited to loopback addresses. URL userinfo, query strings and fragments are rejected. Redirects are refused so credentials are not forwarded to another address.
- Keeps model keys server-side. It never stores or exports them and never shows provider error response bodies. Do not configure verbose HTTP/proxy logging that could record credentials.
- Validates profile structure, source identifiers and sizes before writing. Imported IDs are replaced with a new profile ID. Shared JSON includes only the allowed profile fields and selected full source texts.
- Limits retained jobs and input/output sizes. Questions and answers are process memory only; they expire and are lost on restart.

## What it cannot guarantee

A source can contain instructions aimed at a model. The prompt treats sources as untrusted, but prompt injection resistance is not a security boundary. Models have no tools here, but may still produce misleading text. Citation checks establish ID membership and exact quote presence only; they do not establish relevance, entailment or truth.

A user can paste a password into a source or answer-style preference. Such text may be sent to a configured provider or included in an explicitly previewed export. There is no automatic secret classifier or redaction guarantee. Review the exact preview before sharing.

The JSON store coordinates threads in one process only. It does not support multiple server processes or simultaneous editing across tabs. A local browser extension or malicious local process is outside the threat model. Provider socket timeouts and job capacity limits mitigate stalls; they do not replace an operating-system process limit.

## Reporting a problem

Use the repository's private vulnerability reporting feature if available. Do not put real credentials, private notes or provider request dumps into a public issue. Include a synthetic reproduction, affected version and the observable impact. For a non-sensitive bug, a normal issue with synthetic data is appropriate.
