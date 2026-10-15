# Architecture and API

The installed `brain_twin` package contains a Flask application, Jinja templates and plain JavaScript/CSS. There is no front-end build step. `app.py` assembles the app; `storage.py` owns JSON persistence, `retrieval.py` handles lexical lookup, `twin.py` validates contracts, `model_client.py` handles the configured HTTP provider, and `jobs.py` bounds asynchronous work.

## Ask flow

A browser sends `{profile_id, question, lang}` to `POST /api/ask` with the session CSRF token. The server takes a saved profile snapshot and returns HTTP 202 with `task_id`. A bounded worker searches Chinese bigrams / Latin words, ranks overlapping source chunks, and keeps up to four excerpts of 900 characters.

No hits produce an explicit insufficient-evidence result without a model request. With no configured provider, the result is labeled `mode: "extracts"` and `status: "excerpts"`. A configured provider receives only the question, preferences and retrieved excerpts. Its JSON answer must pass source ID and exact-quote validation. Provider failure is a failed job, never a fallback success. A profile change during execution invalidates the result.

The browser polls `GET /api/jobs/<task_id>` until `succeeded` or `failed`. Jobs carry no artificial completion percentage. Results expire after 15 minutes. A client that stops polling does not cancel the server task; no cancellation UI claims otherwise.

## Profile schema

```json
{
  "schema_version": 1,
  "id": "portable-id",
  "name": "Field Notes",
  "description": "Synthetic example",
  "instructions": "Be concise.",
  "sources": [
    {"id": "source-1", "title": "Meeting notes", "text": "Record a decision owner."}
  ]
}
```

Only these fields are accepted. Profile/source IDs use 1–64 letters, digits, underscores or hyphens. Source IDs are unique within a profile. The import route assigns a new profile ID; source IDs and text are retained. Export takes an explicit list of source IDs and returns the exact package displayed by the browser before download. The server does not perform a hidden secondary export operation.

## Routes

- `GET /` — workspace.
- `GET /styleguide` — live components in both themes.
- `GET /health` — local health response.
- `GET /api/bootstrap` — saved profiles, mode and session `csrf_token`.
- `POST /api/profiles` — create a profile; server assigns `id` and `schema_version`.
- `PUT /api/profiles/<id>` — validate and replace one complete profile.
- `DELETE /api/profiles/<id>` — delete one profile. The UI confirms the consequence.
- `POST /api/import` — validate a profile and save under a new ID; returns 201.
- `POST /api/export` — `{profile_id, source_ids}`; returns the previewable package.
- `POST /api/ask` — `{profile_id, question, lang: "en" | "zh"}`; returns 202 and `task_id`.
- `GET /api/jobs/<id>` — `queued`, `running`, `succeeded` with `result`, or `failed` with `error`.

Writes require `Content-Type: application/json` and `X-CSRF-Token` from the same browser session. `Origin`, when present, must match the app; cross-site Fetch Metadata is rejected. Trusted Host validation is enabled. Validation errors return 400, missing resources 404, CSRF/Origin failures 403, request-size failures 413, non-JSON writes 415, and a full job queue 503 with `Retry-After`.

## Operating model

The data file is replaced atomically after validation and fsync. A thread lock protects writes in one process. Invalid existing JSON is never silently replaced with a sample. The first start alone seeds the fictional example; an intentionally emptied library stays empty on restart.

Model credentials are configuration, not profile data. No credentials, original conversation history, telemetry or third-party browser assets are bundled. A generic chat-completions client is used instead of a provider SDK. The remote endpoint must support the structured JSON contract; failures remain explicit.

This alpha intentionally has no vector database, file crawler, URL importer, user accounts or deployment automation. Those features would change the privacy and operating model and are outside this version.
