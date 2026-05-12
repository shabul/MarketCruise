---
description: Verify Gemini API connectivity and diagnose quota/auth issues
---

Diagnose Gemini API problems on this project.

## Step 1 — Verify the key is reaching Python

```bash
uv run python -c "
import os
from dotenv import load_dotenv
load_dotenv(override=True)
key = os.environ.get('GEMINI_API_KEY', '')
print('length:', len(key), 'last 6:', key[-6:] if key else '<empty>')
"
```

A valid key is 39 characters and starts with `AIza`.

## Step 2 — Direct HTTP call (bypasses LangChain)

```bash
uv run python -c "
import os, urllib.request, json
from dotenv import load_dotenv
load_dotenv(override=True)
key = os.environ['GEMINI_API_KEY']
url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}'
body = json.dumps({'contents': [{'parts': [{'text': 'hi'}]}]}).encode()
req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})
try:
    with urllib.request.urlopen(req, timeout=15) as r: print('HTTP', r.status, 'OK')
except urllib.error.HTTPError as e:
    print('HTTP', e.code, e.read().decode()[:400])
"
```

## Step 3 — List actually-available models

```bash
uv run python -c "
import os
from dotenv import load_dotenv
load_dotenv(override=True)
import google.genai as genai
client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
for m in client.models.list():
    if 'flash' in m.name or 'pro' in m.name:
        print(m.name)
" | head -30
```

If a model in `config.yaml` is missing from this list, update the config — model names change.

## Interpreting errors

| Error | Likely cause | Action |
|-------|--------------|--------|
| `400 INVALID_ARGUMENT — API key expired` | Key revoked or never valid | Regenerate at [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| `400 API key not valid` | Key has trailing whitespace / quote chars | Check `.env` for stray quotes around the value |
| `404 NOT_FOUND — models/X is not found` | Deprecated model name | Update `config.yaml` from the Step 3 list |
| `404 — no longer available to new users` | Old model retired | Same — pick a current one |
| `429 RESOURCE_EXHAUSTED` | Project quota hit (even on Tier 1, per-model RPM applies) | Check [GCP quotas console](https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/quotas) |
| "Both GOOGLE_API_KEY and GEMINI_API_KEY are set" warning | Harmless — `_api_key()` in `base.py` does this sync intentionally | Ignore |

## Known gotchas

- `load_dotenv()` without `override=True` will leave a stale shell `GEMINI_API_KEY` shadowing the `.env` value. We use `override=True` everywhere in this codebase.
- `langchain-google-genai` ≥ 4 prefers `GOOGLE_API_KEY` over `GEMINI_API_KEY`. The `_api_key()` helper in `src/agents/base.py` keeps them in sync.
- The error message for 429 links to Vertex AI docs even though we use the Gemini API endpoint — confusing but normal.
