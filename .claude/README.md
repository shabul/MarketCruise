# `.claude/` — Future-session context

Read this whole folder at the start of any new MarketCruise session. It's curated to be small and high-signal — no fluff.

## Layout

```
.claude/
├── README.md                    # this file
├── settings.json                # tool permissions (no need to prompt for safe ops)
├── commands/                    # custom /commands
│   ├── test.md                  # /test [unit|integration|functional|e2e|all]
│   ├── server.md                # /server — manage FastAPI server + trigger runs via curl
│   ├── check-gemini.md          # /check-gemini — diagnose key / quota / model issues
│   └── refresh-kite.md          # /refresh-kite — daily Zerodha access-token refresh
├── agents/
│   └── market-analyst.md        # read-only specialist for ad-hoc market data questions
└── context/                     # background reading
    ├── conventions.md           # patterns the codebase relies on — don't break
    ├── troubleshooting.md       # actual bugs encountered + their fixes
    ├── quick-reference.md       # file map, tool signatures, schemas, endpoints
    └── session-log.md           # append-only diary of notable decisions / journeys
```

## Reading order for a fresh session

1. `CLAUDE.md` (project root) — high-level conventions, loaded automatically
2. `.claude/context/quick-reference.md` — where everything lives
3. `.claude/context/conventions.md` — what NOT to break
4. `.claude/context/troubleshooting.md` — only if something fails
5. `.claude/context/session-log.md` — to learn from past sessions

## Maintenance rules

- **`session-log.md`** is append-only. Add a dated entry only for surprises, debugging journeys, and decisions a future session would benefit from knowing. Don't log routine work.
- **`troubleshooting.md`** grows by problem encountered. Each entry is symptom → cause → fix. Never delete an entry — even old issues teach how the code thinks.
- **`conventions.md`** and **`quick-reference.md`** should stay current. If you rename a function or move a file, update these.
- **`settings.json`** — only add `allow` entries for genuinely safe ops. Anything that writes outside the working tree, talks to external services with side effects, or could destroy work goes through normal prompts.

## Companion: user-scope memory

There's also a user-scoped memory store at:
```
/Users/Shabul/.claude/projects/-Users-Shabul-Documents-code-trials-MarketCruise/memory/
```

That's for user-specific stuff (preferences, role context). This `.claude/` folder is for project-specific stuff (conventions, debugging, commands). Both get loaded — don't duplicate between them.
