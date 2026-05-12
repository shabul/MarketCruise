# Troubleshooting

## Gemini Key Looks Updated But Calls Still Fail

- Symptom: Gemini rejects a valid-looking key.
- Likely cause: a stale shell-exported key shadows `.env`.
- Fix: use `load_dotenv(override=True)` in the entrypoint or script.

## Model Name 404

- Symptom: Gemini returns model not found.
- Likely cause: deprecated model name.
- Fix: check `config.yaml` and keep to current names used by this repo:
  `gemini-2.0-flash`, `gemini-2.5-flash`, `gemini-2.5-pro`.

## `/api/portfolio` Import Errors

- Symptom: module import failure from a route.
- Likely cause: wrong relative import depth from `src/server/routes/`.
- Fix: imports targeting `src.tools` need `from ...tools...`.

## Accuracy Looks Empty Or Wrong

- Symptom: `GET /api/accuracy` or weekly feedback shows sparse data.
- Likely cause: evening actuals were not parsed from the technical analysis output.
- Fix: inspect the regex path in `src/graphs/daily_graph.py` and confirm the technical output still includes `C=₹... (+/-x.xx%)`.

## SSE History Disappears

- Symptom: active run stream or event backlog vanishes after restart.
- Cause: `_runs` in `src/server/routes/runs.py` is process memory only.
- Fix: restart the run or persist events if durable history becomes necessary.
