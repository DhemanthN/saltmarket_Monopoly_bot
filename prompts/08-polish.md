Task 8: polish. Read docs/web/handoff/qa.md and docs/web/qa/fix-list.md. Start in
plan mode.

1. Fix the fix list top-down: everything that blocks play, then everything that looks
   wrong, then polish while there is time. `/clear` between groups.
2. Add the replay scrubber after game over (and the critic "win-chance river" line if
   the critic weights exist).
3. Update README.md with a short "Play it" section: the live URL, one GIF recorded with
   agent-browser, and two sentences on how the browser runs the real engine and agents.
4. Check every number on the site and in the README against `results/` and RESULTS.md,
   and that each win rate names its table size and opponent pool. Never "~90%", never
   85.6% without "2-player", never "Monopoly rules engine".
5. Re-run `qa-browser` and `design-critic` on the new preview URL (ask with
   `HOSTING NEEDED:` only if the preview did not update).

Handoff with a summary for my resume notes (what was built, real measured numbers
only). Commit, push, and ask me to merge to `main`.
