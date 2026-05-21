## Summary

<!-- One sentence describing what this PR changes and why. -->

## Scope

<!-- Mark all that apply. -->

- [ ] Bug fix
- [ ] New feature
- [ ] Refactor (no behavior change)
- [ ] Docs only
- [ ] Test/CI/tooling only
- [ ] Upstream sync (cherry-pick from waHhhHao/OpenRHTV)
- [ ] PM artifact (allocation / blocker / closure log)

## Touched areas

<!-- Mark all that apply. -->

- [ ] Cascade backend (`backend/src/agent/cascade/`)
- [ ] Cascade prompts (`backend/src/agent/prompts/rewrite_*.md`)
- [ ] Frontend (cascade) (`frontend/src/{components/{anchors,cards,feedback,landing,analytics},pages,hooks,lib}`)
- [ ] Frontend (canvas/video) — shared with upstream
- [ ] Eval harness (`backend/src/agent/cascade/eval/`, `scripts/p2-6_eval.py`)
- [ ] Routines (`pm-check-progress` / `upstream-sync-watch`)
- [ ] Documentation (`docs/nexus/**`)

## Verification

<!-- Replace pluses with what you actually ran. Delete sections that don't apply. -->

- [ ] `cd backend && uv run pytest tests/test_<scope>.py -q` — N passed
- [ ] `cd frontend && npm run build` — clean (`tsc -b` 0 errors)
- [ ] `cd frontend && npm run test` — N passed
- [ ] `cd frontend && npm run lint` — clean
- [ ] `bash scripts/check_progress.sh` — relevant tickets flipped to `done`
- [ ] Manual click-through (frontend only): screenshot below

<!-- Drop screenshots / pytest tail / build output here -->

## Founder review needed?

<!-- Required for upstream-sync REVIEW commits, prompt iterations, scope cuts, and anything that changes cascade product semantics. -->

- [ ] Yes — flagging founder
- [ ] No — safe to auto-merge after CI

## Related

<!-- Cite handoff brief / allocation doc / founder log entry. -->

- Brief: `docs/nexus/handoff/...`
- Allocation: `docs/nexus/PM_W<N>_allocation.md §<n>`
- Founder log: `docs/nexus/founder_log/...`

## Notes for reviewers

<!-- Anything that won't be obvious from the diff alone — performance trade-offs, deferred follow-ups, etc. -->
