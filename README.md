# Brain Twin

## Turn what you know into something people can ask.

You have written down how you run meetings, review drafts or make decisions. The useful advice is there—spread across notes people have to find and read.

**Brain Twin turns selected text into a local experience library: ask a question, find the relevant passages and open the source behind them.** Connect a model to generate answers from those passages.

[Try the example](#try-the-example) · [Download Alpha](https://github.com/Xfireman/brain-twin/releases/tag/v0.1.0-alpha.1) · [中文](README.zh-CN.md)

Local app · English / 中文 · MIT · Alpha

### Start with a question someone actually asks you

“What should we record before a meeting ends?”

The included fictional **Field Notes** library contains this advice:

> Reserve the final five minutes of a remote meeting to record decisions. Each decision needs an owner, a due date and its reason.

Ask about recording decisions and Twin retrieves that passage. Open the source to read the rest, including what to do with unresolved questions. Ask about a subject the example does not cover to try the insufficient-sources response.

No API key is needed to explore this source-excerpt workflow. With a configured model, Twin can compose an answer and attach references to retrieved passages. You can still inspect the original text; a matching citation alone does not prove the conclusion.

![A question and matching source passages from the fictional Field Notes library](docs/screenshots/desktop-light.png)

*The default mode displays source excerpts. The example and screenshot use fictional material.*

### Build a library around experience worth reusing

- **Your working methods:** notes on meetings, writing, experiments or project decisions.
- **A guide people keep asking for:** collect the explanations you want them to be able to find again.
- **A curated set of advice:** keep a focused library around one topic, with each source available for inspection.

Paste the text you choose, give each source a title, and save. Ordinary forms let you edit the profile and source material. This Alpha accepts pasted text; document uploads, URL fetching and automatic account imports are outside this release.

### Share a chosen part of your knowledge

Choose the sources, preview their full contents, then download a profile package. Another user imports it into their local Twin and can ask their own questions or adapt the library.

The package includes the full text of selected sources and profile settings. Questions, answers and configured credentials are excluded. Sharing is a file transfer, and the text you choose needs your privacy review.

## Try the example

Requires Python 3.10+ and Git. On macOS or Linux:

```sh
git clone https://github.com/Xfireman/brain-twin.git
cd brain-twin
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
brain-twin
```

Open **http://127.0.0.1:5043**, then:

1. In **Field Notes**, click **Try: recording decisions**, then **Find evidence**.
2. Open the source to inspect the complete note.
3. Ask “How many moons does Jupiter have?” to try an uncovered topic.
4. Open **Shape the library**, add a short note of your own and save. Ask a question using words from that note.

You have now tried both a useful match and a missing-source case. To generate an answer from the retrieved passages, [connect a model](#optional-model-answers).

On Windows, use `py -m venv .venv` and `.venv\Scripts\activate`. You can also [download the source archive](https://github.com/Xfireman/brain-twin/releases/tag/v0.1.0-alpha.1) and install from the extracted directory. After installation, `brain-twin` works from any directory; `--port 5053` changes the port.

### Keep it focused

Twin is most useful with **a small, deliberate collection of notes whose sources you want to inspect**. Local search matches words and Chinese character pairs, so paraphrases and synonyms can miss. Source selection and your own judgment still matter.

For a repeatable method, see [Brain Recipes](https://github.com/Xfireman/brain-recipes). To continue an unfinished task in another conversation, see [Brain Relay](https://github.com/Xfireman/brain-relay).

## Optional model answers

<details>
<summary>Provider setup and the answer/citation contract</summary>

Set the following **in the shell before starting**. `BRAIN_MODEL_URL` is the full chat-completions endpoint, not a base URL:

```sh
export BRAIN_MODEL_URL='http://127.0.0.1:1234/v1/chat/completions'
export BRAIN_MODEL_NAME='your-local-model'
brain-twin
```

For a remote provider, use an HTTPS endpoint and configure `BRAIN_MODEL_KEY` in the process environment through your usual secret manager. Do not put a real key in source files, source notes, shared packages or browser code. A key is optional for local servers. A partial URL/name configuration fails at startup.

The provider must accept `messages`, `model`, `stream: false`, `temperature`, `max_tokens`, and `response_format: {"type": "json_object"}`. It must return a JSON object as `choices[0].message.content`:

```json
{
  "status": "answered",
  "answer": "Record the owner of each decision.",
  "citations": [
    {"source_id": "meeting-notes", "quote": "Each decision needs an owner"}
  ]
}
```

If evidence is insufficient, return `status: "insufficient"` with an empty `citations` list. Invalid JSON, invented IDs, non-verbatim quotes, HTTP errors and timeouts are visible failures. They never silently fall back to excerpt mode. The app sends the question, answer preferences and at most four retrieved excerpts to the configured provider; it does not send other profiles or the complete library. Endpoint redirects are refused, and provider response bodies are not shown in errors.

No real or paid model was used to test this alpha. Provider compatibility and answer quality remain your responsibility; the tests use an HTTP service on the loopback interface.

</details>

## Storage and limits

<details>
<summary>Local files, data limits and deployment scope</summary>

- Default data directory: `~/.local/share/brain-twin`. Override with `BRAIN_TWIN_DATA_DIR` before launch.
- `profiles.json` is saved by atomic replacement with a single-process lock. Corrupt data causes a startup error instead of being replaced. Back up this file when the app is stopped.
- One process only. There is no account system, multi-process coordination, encryption at rest or collaborative editing. Two open tabs can overwrite each other's profile edits; save carefully.
- Questions and results remain in process memory only. Jobs expire after 15 minutes and are lost on restart. They are never included in shared packages.
- At most 30 profiles, 50 sources per profile, 30,000 characters per source and 200,000 source characters per profile. Request bodies are limited to 2 MiB.
- Questions are limited to 4,000 characters. Retrieval returns at most four passages, each up to 900 characters. The model receives only these passages; other material can be missed.
- Two workers, at most four queued/running jobs, and at most 64 retained jobs. Full queues return HTTP 503. Each provider socket operation has a 25-second timeout and responses are capped at 128 KiB.

`brain-twin --port 5053` changes the port. The server always binds to `127.0.0.1`. This is a personal local tool: do not expose the Flask development server to the Internet or use it for shared hosting.

</details>

## Retrieval and truthfulness

<details>
<summary>How matching works and what citations do not prove</summary>

Retrieval uses Chinese character bigrams and Latin word tokens with lexical overlap. It is offline and deterministic, but does not understand meaning or reliably match synonyms. Short or ambiguous questions can miss relevant material or match the wrong passage. Excerpts make no claim to answer the question. Model mode rejects unknown source IDs and quotes absent from retrieved excerpts, but a real quote can still be used misleadingly. Check the original text before relying on an answer. Source content is untrusted input; prompt injection resistance is not guaranteed.

Changing the selected profile, editing sources or changing the question clears the previous answer. Starting another request also clears it, including when that request fails. Results are tied to the exact saved profile version, question and request; a late response cannot replace a newer answer, even if you switch away and back. If another tab saved different data, reload the page before asking again. Discarding a browser result does not cancel work already running on the server.

</details>

## Development

<details>
<summary>Tests, browser checks and development setup</summary>

```sh
python -m pip install '.[test]'
python -m pytest
python -m pip install build
python -m build
```

Tests cover Chinese retrieval, insufficient evidence, source edits/deletion, atomic persistence, export selection, import roundtrip, CSRF/Origin/Host defenses, XSS-safe rendering contracts, bounded jobs, model wire fields, invalid citations, provider errors, redirect rejection, and UI token/contrast invariants. HTTP tests bind only loopback and require permission to open a local listening socket. CI tests Python 3.10 and 3.14 and builds a wheel.

For the real browser flow (Chromium):

```sh
python -m pip install playwright
python -m playwright install chromium
python scripts/browser_smoke.py
python scripts/browser_regressions.py
```

The regression script covers answer invalidation, late-response races and session coexistence with another app on a different local port. Both browser scripts run in CI. `/styleguide` renders the actual components in both themes. [Screenshots](docs/screenshots) include desktop, mobile, source evidence and sharing. No front-end build step, CDN or external font is needed.

</details>
