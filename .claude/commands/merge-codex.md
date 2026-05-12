---
description: Review and selectively merge progress from a sibling -codex branch into the current branch
argument-hint: optional source branch name override (defaults to <current>-codex)
---

The user worked on a parallel branch using the codex agent and wants to integrate that work into the current branch. Do NOT blindly merge — review, judge quality, cherry-pick the good parts, drop the bad parts, verify with tests, and only then commit and push.

## Step 0 — Establish context

Run these in parallel:

```bash
git branch --show-current                              # current branch name → $CURR
git status --short                                     # any uncommitted work?
git log --oneline -10                                  # recent commits on current
```

Determine the codex source branch:
- If the user passed an argument, use that as the source branch name.
- Otherwise default to `${CURR}-codex` (e.g., on `feature/init`, source is `feature/init-codex`).
- If the user is currently ON the `-codex` branch by mistake, stop and ask which branch should receive the merge.

Verify the source exists:
```bash
git rev-parse --verify <codex-branch>
git fetch origin <codex-branch>   # in case it's only on remote
```

If uncommitted changes exist on the current branch, STOP and ask the user whether to stash or commit them first. Never silently overwrite work in progress.

## Step 1 — Understand current branch progress

Read recent commits and the diff against the merge base with `main`:
```bash
git log --oneline main..HEAD
git diff --stat main..HEAD
```

Form a one-paragraph mental model of "what does this branch contain right now?" before looking at the codex side. This prevents anchoring bias when reviewing the codex work.

## Step 2 — Understand the -codex branch progress

```bash
git log --oneline <curr>..<codex-branch>              # commits codex has that current doesn't
git diff --stat <curr>..<codex-branch>                # files codex changed
git diff <curr>..<codex-branch>                       # full diff — READ THIS, don't just skim
```

For each meaningful change in the codex diff, judge:
- **Does it fit the conventions in `CLAUDE.md` and `.claude/context/conventions.md`?** (env loading, import depth, agent return shape, dual-write, UTC timestamps)
- **Does it duplicate or undo something the current branch already did?**
- **Is it self-contained or does it pull in adjacent unrelated edits?**
- **Does it have tests? Are they real-API or mocked?** (this codebase uses real APIs — see `docs/testing.md`)
- **Does it touch deprecated model names (`gemini-1.5-*`), `..tools` imports, or `load_dotenv()` without `override=True`?** (those are red flags — see `.claude/context/troubleshooting.md`)

Output a short summary to the user before doing anything destructive:
- ✅ **Keep:** list of commits or hunks that should land
- ❌ **Drop:** list of commits or hunks to skip, with reason
- ❓ **Ask:** anything ambiguous — get the user's call before acting

## Step 3 — Decide the merge strategy

Based on the review, pick ONE:

| Codex quality | Strategy |
|---------------|----------|
| All good, no conflicts, clean history | `git merge --no-ff <codex-branch>` |
| All good, but messy history | `git merge --squash <codex-branch>` then a single clean commit |
| Partially good, distinct commits | `git cherry-pick <sha1> <sha2> ...` for the good ones only |
| Partially good, intermingled hunks | `git checkout <codex-branch> -- <path>` per file, or `git apply` selected hunks from a patch |
| Bad / not worth merging | Do nothing, tell the user why, leave codex branch alone |

State the chosen strategy to the user and get explicit confirmation before running it. Cherry-picks and selective checkouts are reversible; force-pushes and resets are not — those need an explicit ask.

## Step 4 — Execute the merge

Run the chosen strategy. If conflicts arise:
- Resolve them in line with the conventions in `CLAUDE.md` — when in doubt, prefer the current branch's version since you reviewed it first
- For Gemini model names, env handling, or import depths, the current branch's convention wins
- Never `git checkout --theirs` or `--ours` wholesale — resolve each conflict on its merits

After resolution, verify the working tree:
```bash
git status
git diff --stat HEAD
```

## Step 5 — Test the merged code

This is non-negotiable. Run the appropriate test layers:

```bash
uv run pytest tests/unit/ -v                          # always
uv run pytest tests/integration/ -v --timeout=60      # if tools/agents/base changed
uv run pytest tests/functional/test_server_api.py -v  # if server routes changed
```

If a layer of tests was changed by the merge, run that layer too. Functional and E2E tests need a live `GEMINI_API_KEY` — skip them with a note if the key is missing or rate-limited.

**If any test that was passing before is now failing, STOP.** Either fix it inline (small obvious fix) or revert the merge with `git reset --hard ORIG_HEAD` and report what broke. Do not push broken code.

## Step 6 — Update documentation

If the merge introduced anything user-visible or convention-shifting:
- **CLAUDE.md** — update if a new convention was added (new model name, new module structure, new env var)
- **docs/architecture.md** — update if agents, graphs, or memory layout changed
- **docs/api.md** — update if HTTP endpoints changed
- **docs/setup.md** — update if env vars or install steps changed
- **docs/testing.md** — update if test conventions changed
- **`.claude/context/quick-reference.md`** — update file map, signatures, schemas as needed
- **`.claude/context/session-log.md`** — append a dated entry summarizing what was merged and why

Don't update docs for trivial changes (typo fixes, formatting, refactors that don't shift the public surface).

## Step 7 — Commit and push

If the merge strategy already created a commit (merge / cherry-pick), the doc updates need their own commit:

```bash
git add CLAUDE.md docs/ .claude/context/
git commit -m "Update docs after merging <codex-branch>"
```

Or, if the merge was squashed / file-selective, fold the doc updates into the same commit.

Push:
```bash
git push
```

Never `--force` push unless the user explicitly asks. Never push to `main` from this command — only to the branch we're on.

## Step 8 — Report back

Tell the user, in a few lines:
- What was merged (commit SHAs or summary of hunks)
- What was dropped and why
- Test result summary (e.g., "97/97 unit + integration passing, 7 Gemini tests skipped due to rate limit")
- Doc files updated
- New HEAD SHA on the branch + remote tracking confirmation

## Safety rails

- **Never** delete the `-codex` branch even after merging — the user may want to compare again later. If they explicitly ask, fine; otherwise leave it alone.
- **Never** force-push without an explicit ask, and never to `main`.
- **Never** silently `git reset --hard` or `git checkout --` paths that have uncommitted work.
- If anything looks ambiguous, prefer one extra clarification question over a destructive guess. The user has paired with the codex agent; they have a mental model of what should land — surface choices, don't make them in silence.
