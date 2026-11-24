# Perf notes, branch integrate, 2026-11-23

Method: agent-browser (headless Chrome, DPR 1, 1256x565), dev server :5281, 4-player game vs PPO, several agent turns played.
Caveat: not the owner's laptop iGPU; fps numbers are indicative only.

| Item | Budget | Measured | Result |
|---|---|---|---|
| Draw calls, street | <150 | 31-43 (high tier first frame: 33) | pass |
| Draw calls, chart | <150 | 57 | pass |
| Triangles | n/a | 11k-17k | n/a |
| DPR | <=2 | 1 (device DPR 1; tier code caps 2/1.5/1) | pass |
| Shadow updates | board change only | stayed 2 during agent turns | pass |
| Frame rate | 60 fps | high tier 120 fps; rAF 90-109 while rendering | pass (headless) |
| Start screen idle | stops rendering | 0 GL draws and 0 clears in 4 s | pass |

Observations
- Tier fell from high to low within seconds of game start (PerformanceMonitor), in a headless browser. Low tier uses frameloop demand and no shadows; probe fps is then meaningless while idle.
- One 5.2 s frame stall on first switch to chart view (lazy chunk and/or shader compile).
- __saltmarketPerf lacks textures and geometries counts (gl.info.memory). Add to PerfSnapshot in web/src/world/quality.ts and PerfProbe in web/src/world/WorldScene.tsx.
- AtollSilhouette has no probe; idle check done by patching WebGL draw calls.
