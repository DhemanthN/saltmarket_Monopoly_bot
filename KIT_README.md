# Saltmarket 3D starter kit

Unzip into the root of `saltmarket_Monopoly_bot`, then:

1. Append `CLAUDE.web.md` to the end of `CLAUDE.md` and delete `CLAUDE.web.md`.
   (PowerShell: `Get-Content CLAUDE.web.md | Add-Content CLAUDE.md; Remove-Item CLAUDE.web.md`)
2. If you already have `.claude/settings.json`, merge the `model` and `permissions`
   keys by hand instead of overwriting it.
3. Commit: `git add -A; git commit -m "docs: add web build kit"; git push`
4. Open RunPane's Pane Chat and paste `prompts/DISPATCHER.md` (the part under the line).

What's inside:

| Path | What it is |
| --- | --- |
| `CLAUDE.web.md` | Rules for all web work: plan first, one pane per task, handoffs, honesty, performance budget, `HOSTING NEEDED:` protocol |
| `.claude/settings.json` | `opusplan` model (Opus plans, Sonnet builds) and safe command permissions; blocks `vercel` |
| `.claude/agents/` | explorer (Haiku), test-writer (Sonnet), design-critic (Opus), perf-auditor (Sonnet), qa-browser (Sonnet) |
| `docs/web/REFERENCES.md` | 3D references and Mobbin searches |
| `docs/web/ANTI_SLOP.md` | The 12-point checklist the design-critic enforces |
| `docs/web/handoff/_TEMPLATE.md` | What each pane writes when it finishes |
| `prompts/` | Dispatcher plus one kickoff prompt per task (00-08) |
