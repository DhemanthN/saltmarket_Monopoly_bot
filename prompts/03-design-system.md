Task 3: design-system. Read docs/web/handoff/plan.md, docs/web/DESIGN.md and
docs/web/ANTI_SLOP.md. Start in plan mode. Use the frontend-design skill.

Scaffold `web/`:
- Vite + React + TypeScript + @react-three/fiber + @react-three/drei, Vitest, ESLint.
- Dev server sends the two cross-origin isolation headers if the spike chose option A.
- Fonts self-hosted in `web/public/fonts/` (no third-party font loads).
- Tokens from DESIGN.md as CSS custom properties in `web/src/styles/tokens.css` and a
  typed `tokens.ts` for the 3D side (palette texture colours, motion durations).
- Primitives: Panel (paper/sailcloth surface), Button (primary, secondary, quiet),
  Ledger row with tabular figures, Signboard (for prices in the world), Toast.
- One real screen: the start screen, with the atoll silhouette as a placeholder
  canvas behind it. Not a hero + feature cards page.
- A `/tokens` dev-only page showing every token and primitive.

Before calling it done, run the `design-critic` subagent on the start screen and the
tokens page at local preview, and fix every checklist failure.

Handoff, commit, push.
