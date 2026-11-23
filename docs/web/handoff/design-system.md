# Handoff: design-system

Branch: `design-system` · Date: 2026-11-23 · Status: done

## What changed
- Added `web/`: Vite 8, React 19, TypeScript 5.9, react-three-fiber 9, drei 10, Vitest 5, ESLint 10. Versions are pinned exactly.
- `web/vite.config.ts` sends `Cross-Origin-Opener-Policy: same-origin` and `Cross-Origin-Embedder-Policy: require-corp` on both the dev and preview servers, from one `ISOLATION_HEADERS` constant. `crossOriginIsolated` is `true` in the preview.
- Fonts self-hosted in `web/public/fonts/` (Fraunces variable with all axes, IBM Plex Sans 400/500/600, Latin subset, OFL texts). No third-party font requests.
- `web/src/styles/tokens.css`: every DESIGN.md token as a custom property, plus a `[data-mood="night"]` role remap and reduced-motion overrides.
- `web/src/styles/tokens.ts`: typed mirror, WCAG `contrastRatio`, and `buildPaletteTexture(mood)` (16x16 RGBA) with `cellIndex` for task 4a.
- Primitives in `web/src/ui/`: Panel, Button (primary, secondary, quiet), LedgerRow, Signboard, Toast (+ `ToastProvider`, `useToast`), Emblem (custom SVG, four seat emblems).
- Start screen (`web/src/screens/StartScreen.tsx`): atoll placeholder fills the viewport, a floating paper panel at the bottom-left (bottom sheet on phones) holds the seat table and "Start game". Seats are local state only. "Start game" shows a toast saying the engine is not connected.
- Placeholder world (`web/src/world/`): 40 lots from `data/board.json` as two instanced meshes (body + ink hull outline), ring road, lagoon, fog, `frameloop="demand"`. Home Quay's signboard is projected to screen coordinates and drawn as DOM.
- `/tokens` page: all tokens, type scale, spacing, radii, shadow, motion demo, z-layers, every primitive, day/night toggle. Present in `npm run dev` and `npm run preview:dev` only; `npm run build` drops it.

## Decisions made (and why)
- **COOP/COEP on now.** The spike has not reported, but runtime A is the recommendation and every asset is self-hosted. If the spike picks B, delete `ISOLATION_HEADERS` and the two `headers` entries.
- **Jade changed to `#2E7E6A`** (was `#2F7F6B`). The old value measures 4.4956 against sailcloth, below the 4.5 DESIGN.md claims. `docs/web/DESIGN.md` is updated to 4.56 / 4.08.
- **TypeScript 5.9.3**, not 7: `typescript-eslint` 8.74 supports `<6.1`.
- **No `drei <Html>`**: it never mounted in this setup (no DOM node was created). The signboard anchor is projected manually in `CameraRig`.
- **No router library**: a pathname check in `App.tsx`. `TokensPage` is created behind the dev flag so production builds drop its chunk.
- **Night texture** = each palette colour pulled 45% toward `night`. DESIGN.md does not specify night world colours; 4a may replace this.
- Installed `agent-browser` globally (`npm i -g --allow-scripts=agent-browser agent-browser`, then `agent-browser install`).

## design-critic result
- Verdict SHIP, no ANTI_SLOP failures, on `/` and `/tokens` at 1440x900 and 390x844, day and night.
- Fixed from its report: night swatch captions now use night contrast; night gain (`#7FC98A`, 6.61 on night-panel) and debt (`#F2988A`, 6.00) colours; night paper-lift; ledger colours the delta, not the balance, with a true minus (U+2212); styled `<select>`; visible primary button edge (`--primary-edge`); mobile camera so the ring clears the panel; "Add a seat" hit area inside the panel.
- Not done (for 4a): the sea reads as a gradient backdrop because the fog colour (sky) blends into it. Give the lagoon and sea their own palette colours and a horizon line. Depth was graded C by the critic.

## How to verify
- Commands: `cd web; npm ci; npm run lint; npm test; npm run build; npm run preview:dev`
- Then open `http://localhost:4173/` and `/tokens`. `curl -I http://localhost:4173/` shows both isolation headers. In the console `crossOriginIsolated` is `true`.

## Tests
- Added: `web/src/styles/tokens.test.ts` (tokens.ts equals tokens.css; WCAG pairs from DESIGN.md; palette texture shape and day/night cell map) and `web/src/world/board.test.ts` (40 spaces, 8 districts, ring positions).
- Results: Vitest 18 passed. `tsc --noEmit` and ESLint clean. `ruff check .` untouched (no Python changed).

## Left for later / known issues
- Placeholder scene colours `SKY` and the lagoon `#6FA3A8` in `AtollSilhouette.tsx` are not in `tokens.ts`; task 4a should move them into the palette texture.
- The main JS chunk is about 1.16 MB (320 KB gzip) because of three and drei. Task 4a/5 should split it.
- Console shows a three.js warning, `THREE.Clock has been deprecated`, from react-three-fiber. Not ours.
- Mobile ring is slightly cropped at the sides at 390 px.
- "How to play" is a toast placeholder.
- Draw calls were not measured with `gl.info`; by construction the start scene is about 6 meshes.

## What the next task needs to know
- Use `tokens.ts` `cellIndex` and `buildPaletteTexture` for the palette texture. Primitives take pre-formatted strings; they do not format numbers.
- `useToast()` needs `ToastProvider` (already in `main.tsx`).
- CSS modules per component; semantic roles (`--surface`, `--text`, `--rule`, `--outline`) change under `data-mood="night"`, so use them instead of raw colours.
