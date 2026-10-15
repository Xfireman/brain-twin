# Contributing

Use synthetic text in tests, examples, screenshots and issue reports. Never include personal notes, private conversations, credentials or provider response dumps.

Install `.[test]`, run `python -m pytest`, and run `python scripts/browser_smoke.py` for UI changes. See `DESIGN.md` before touching templates or styles. Behavior changes should include a regression test that fails for the bug it fixes. Keep English and Chinese UI dictionaries and READMEs in sync.

Preserve the local, single-process operating model and explicit export preview. Do not silently switch provider failures into demo or excerpt success. Citation validity is not semantic truth; keep that distinction visible. New data ingestion or network features need a documented privacy and security design before implementation.
