# Handoff: qa (task 7)

Branch: `qa` · Date: 2026-11-24 · Status: done. Report only, nothing fixed.

## What changed
- Added `docs/web/qa/fix-list.md`: 32 ranked items from `qa-browser`, `perf-auditor` and `design-critic`, run in that order against https://saltmarket.vercel.app/ at 390x844 and 1440x900. It also holds a flow coverage table, the anti-slop result, the perf budget table, headroom for the polish rework and the ranked wow gaps.
- No source, test or config files changed.

## Verified
- Full games to the end: 2p vs PPO (desktop), 4p vs PPO plus bots (phone), 2p vs DQN, 2p vs bot. No stalls, no console errors, no failed requests.
- The perf budget passes except the main chunk (1.23 MB decoded).

## Not reached or not measured
- Jail "use card", a build or upgrade decision, AI trade counter, 4x CPU throttle, textures and geometries, a 5-minute memory run. The night HUD cannot be tested live (F4).

## How to use
- Suggested fix order: F5 (Auto quality), F1 to F3, F4, then the wow gaps. Open owner questions are at the end of the fix list.
- Screenshots lived only in the session scratchpad and are not committed.

## Decisions
- Merged duplicate findings across agents and kept the finder IDs (B, P, D) next to each item.
- Where agents disagreed on severity (F2), the item says so.
