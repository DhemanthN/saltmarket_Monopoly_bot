# Task 8, world slice: the living atoll

Branch `upgrade`. Commits `7300e67` and `03649c6`.

## What changed

| Item | Change |
|---|---|
| Building kit | `world/landmarkKit.ts`: one signature prop for each of the 40 spaces (customs house, tavern, shipyard crane, lighthouse, fish market, rope walk, treasury, the Brig cell, saltworks, water wheel, bell tower and more). Props stand behind each lot, toward the outer shore, and never reach the ring road (tested). All props merge into one mesh plus one ink hull. |
| Style 1 and 2 | Same geometry. Day uses the day palette texture. The night mood is Style 2: the existing night texture plus lit glass (`world.glow`) at `GLOW_INTENSITY` 1.6. No extra draws. |
| Silhouettes | `world/silhouettes.ts`: four cliff watchtowers with lanterns and flags, three quay cranes behind the ferries, rope bridges from shore to two cliffs and from the market to the Brig rock. Merged into the landmark mesh. |
| Flags and sails | `world/shaders.ts` `swayMaterial`: vertex sway `aSway * amp * sin(time + x)` with a per-instance phase. Flags are one instanced mesh; galleon sails use the same patch. |
| Galleons | `LivingSea.tsx` `Galleons`: 3 on High, 2 on Medium, none on Low. Closed `CatmullRomCurve3` loops at radius 21 to 29, with rocking. One instanced draw. |
| Flare | `LivingSea.tsx` `Flare`: every 15 to 20 s (seeded), or on `triggerFlare()`. Parabolic arc from a galleon to the reef, a fading ribbon and a splash ring. It calls `triggerCameraShake` at launch (0.25, 0.35 s) and at the splash (0.5, 0.6 s). Gate: `flaresAllowed`, which is off on Low, in Calm, with reduced motion, and while `isDecisionOpen()` or `anyModalOpen()` is true. A flare in flight hides at once if a panel opens. |
| Clock | `WorldClock` advances one shared uniform only while motion is on. In Calm, with reduced motion or on Low, the flags, sails, water and galleons hold still. |
| Water | The sea uses `waterMaterial` on Medium and High: drifting swell bands with no reflections. `ShoreFoam` draws rolling foam at the outer shore and the lagoon edge in one draw. Low keeps flat colour. |
| Bloom and tone | `HighEffects.tsx` replaces `ChartTiltShift.tsx` and loads lazily on High only. Bloom at threshold 1.0, so only the night glass and the flare bloom. Chart view adds tilt-shift. ACES runs as the composer's last effect. |

## Contrast

ACES applies only inside the WebGL canvas. R3F already used ACES on every tier, and High now matches it through the composer. The HUD is HTML and is not tone mapped, so the measured token contrast numbers in DESIGN.md do not change. No palette colour was edited.

## Perf (`/world?perf=1`, dev replay, desktop 1869x1327, DPR 1.75)

| Tier | Street | Chart |
|---|---|---|
| High | 68 draws, 29.1k tris | 85 draws, 33.4k tris |
| Medium | 48 draws, 27.6k tris | 68 draws, 33.2k tris |
| Low | 43 draws, 20.4k tris | 45 draws, 20.8k tris |

All tiers stay under 150 draws. The fps reading in the background Pane tab was not meaningful. Real-phone fps is not measured.

## Not done

- Phone 390x844 check, a night screenshot and real-device fps: not run. The next QA pass should run perf-auditor and design-critic on these.
- No flare sound. Sound is not part of this slice.
- `triggerFlare()` has no caller yet. The main agent can call it on a big event.

## How to verify

`cd web; npx tsc --noEmit; npx eslint .; npx vitest run` (181 pass). `python -m pytest -m smoke` (426 pass). Open `/world?perf=1`, read `window.__saltmarketPerf`, and press C for chart view.
