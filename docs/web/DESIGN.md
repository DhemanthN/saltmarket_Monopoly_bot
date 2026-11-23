# Saltmarket 3D: design

Read with `ANTI_SLOP.md` (every hit there is a FAIL) and `REFERENCES.md`.

## Principles

- The world is the hero. The HUD hugs the edges.
- Panels are objects from the island (paper, sailcloth, brass), not glass.
- Each decision panel has one primary action. Everything else is visibly secondary.
- Every animation explains something: a hop, travelling coins, a building rising.
- Colour is never the only cue.

## HUD patterns per moment

These are our own rules. The 2D screens are designed from these, not from outside examples.

| Moment | Pattern |
| --- | --- |
| Buy or pass | A deed card: space name, district accent strip, price, rent ladder in tabular figures, and cash left after buying. Primary: "Buy for {price}". Secondary: "Pass to auction". |
| Auction | Set in the market square. A row of 7 bid chips shows real amounts (multiples of list price). Amounts above the player's cash are not offered. A live ladder shows the seat emblems and current high bid. |
| Trade | A two-column ledger, "you give" and "you get", with badges where a side completes a group. Responding: Accept is primary, Decline secondary. Proposing: pick a group, then one of 3 premiums. |
| Cash, net worth, rent | A ledger rail on the screen edge, one row per seat. Rent paid shows as a feed line with a travelling coin. All numbers use tabular figures. |
| First game | Three coach marks only: your piece and the road, the decision panel, the lanterns. Skippable. Never repeated. |
| Game over | Winner, turn count, final ledger, a replay button. Any win rate shown names its table size and opponent pool and comes from `results/`. |

## Tokens

### Colour

Contrast uses the WCAG 2.x relative-luminance formula. Text needs at least 4.5, non-text
marks at least 3.0.

| Token | Hex | Use and measured contrast |
| --- | --- | --- |
| paper | `#F3EAD7` | Panel surface. Ink on paper 12.29 |
| paper-deep | `#E6D8BC` | Inset rows, mortgaged sails. Ink on it 10.44 |
| sailcloth | `#FBF7EE` | Raised surface and light labels. Ink on it 13.75 |
| ink | `#1F2A2E` | Text and outlines |
| ink-soft | `#4A5558` | Secondary text. 6.43 on paper |
| brass | `#8A6A1F` | Rules and small caps. 4.72 on sailcloth. 4.22 on paper, so ornament or large text only there |
| tide | `#1E5A66` | Links, chart water ink. 6.48 on paper |
| focus | `#0B5CAD` | 2 px focus ring. 5.58 against paper |
| danger | `#A3261A` | Debt, bankruptcy. 6.16 on paper |
| ok | `#2E6B34` | Gains. 5.37 on paper |
| night | `#16232B` | World at night, page background in night mode |
| night-panel | `#22333C` | Panels at night |
| night-text | `#EDE3CF` | Text at night. 12.59 on night, 10.26 on night-panel |

**District accents.** Each carries a sailcloth label at 4.5 or more and reaches 3.0 or more
against paper as a mark. Against night-panel they reach only 1.6 to 2.7, so on dark panels
every swatch gets a 1 px sailcloth ring.

| District | Hex | Sailcloth label | Against paper |
| --- | --- | --- | --- |
| kelp | `#4F7A3A` | 4.70 | 4.20 |
| reef | `#B5523B` | 4.64 | 4.15 |
| coral | `#C2456B` | 4.51 | 4.03 |
| driftwood | `#7A5A3C` | 5.85 | 5.23 |
| amber | `#96680F` | 4.58 | 4.10 |
| cinder | `#5B4A4E` | 7.75 | 6.93 |
| jade | `#2F7F6B` | 4.50 | 4.02 |
| crown | `#3B4F8C` | 7.32 | 6.55 |

**Owner colours.**

| Seat | Hex | Label colour and contrast |
| --- | --- | --- |
| 1 saffron | `#D9A21B` | ink, 6.39 |
| 2 teal | `#137C86` | sailcloth, 4.62 |
| 3 vermilion | `#B8321A` | sailcloth, 5.60 |
| 4 indigo | `#3A2F7A` | sailcloth, 10.52 |

The four owner colours sit close in brightness (pairwise contrast 1.08 to 2.96), so colour
alone must never identify an owner. Each seat also has an emblem (sun, wave, star, anchor)
drawn as custom SVG, never emoji, and every owner mark has a 1.5 px ink outline. In 3D, owner
colour goes on sails and awnings and the emblem goes on a flag.

### Typefaces

Both are OFL-licensed and self-hosted as woff2 in `web/public/fonts/`.

- **Display: Fraunces** (variable, with optical size and softness axes). Its almanac and
  sea-chart lettering gives the island a voice that a neutral sans cannot. Used for headings
  and space names. Fallback: `"Iowan Old Style", Georgia, "Times New Roman", serif`.
- **Text and figures: IBM Plex Sans.** Clear at 12 to 14 px, a workmanlike tone that suits a
  harbour, and real tabular figures (`font-variant-numeric: tabular-nums`) for the ledger.
  Fallback: `"Segoe UI", "Helvetica Neue", Arial, sans-serif`.

That gives three visible levels: display (Fraunces), text (Plex), and tabular figures (Plex).

### Type scale

Ratio 1.25. Size / line height in px.

| Step | Size / line | Font |
| --- | --- | --- |
| caption | 12 / 16 | Plex |
| small | 14 / 20 | Plex |
| body | 16 / 24 | Plex |
| h4 | 20 / 28 | Plex, semibold |
| h3 | 25 / 32 | Plex, semibold |
| h2 | 31 / 36 | Fraunces |
| h1 | 39 / 44 | Fraunces |
| display | 49 / 52 | Fraunces |

### Spacing

4 px base. `--space-1` to `--space-10` are 4, 8, 12, 16, 20, 24, 32, 40, 48, 64.
Panel padding is 16 or 24, gaps between controls are 8, gaps between sections are 24.

### Radius and shadow

Not uniform on purpose (anti-slop item 6).

- Panels 2 px, like cut paper. Signboards 0 with a 1 px brass bevel. Buttons 4 px. Only seat
  emblems and dice pips are fully round.
- Shadow only on floating panels, "paper lift":
  `0 1px 0 rgb(31 42 46 / .12), 0 8px 18px -8px rgb(31 42 46 / .35)`.
- Buttons have no shadow. The primary button has a 2 px ink bottom edge and moves down 1 px
  when pressed. Ledger rows use hairline brass rules and no shadow.

### Motion

| Name | Duration | Easing | Used for |
| --- | --- | --- | --- |
| quick | 120 ms | `cubic-bezier(0.2, 0, 0, 1)` | Hover, press, focus, chip select |
| standard | 240 ms | `cubic-bezier(0.3, 0, 0, 1)` | Panel enter and exit, lantern open, one hop per space |
| travel | 480 ms | `cubic-bezier(0.65, 0, 0.35, 1)` | Camera toggle, coin cart leg, one storey rising |

With `prefers-reduced-motion`, travel and hops become a 120 ms crossfade, pieces fade to
their destination, and the camera cuts.

### Z-layers

| Layer | z-index |
| --- | --- |
| Canvas | 0 |
| World-anchored labels (signboards, lantern anchors) | 100 |
| HUD rails (ledger, lanterns) | 200 |
| Decision panel | 300 |
| Coach marks | 400 |
| Toast | 500 |
| Menu and modal | 600 |
| Dev overlay | 900 |

## Art direction for the 3D world

- **Palette texture.** One 16x16 PNG generated from `tokens.ts`. Every mesh maps its UVs into
  a cell, and there are no other colour textures. A second 16x16 texture gives the night mood,
  so a mood change is one texture swap.
- **Outlines.** An inverted-hull ink outline (`ink`, 1.5 to 2.5 percent scale) on buildings,
  pieces and the road edge, drawn as a second instanced mesh. The high tier adds a depth and
  normal edge pass.
- **Fog.** Exponential and coloured to the sky at the horizon. Light in chart view. Denser in
  street view, to soften the far side of the ring and the ocean edge.
- **Lighting by time of day.** One day is 24 turns. One directional light plus one hemisphere
  light, blended between keyframes by the sun arc:

  | Time | Sun | Notes |
  | --- | --- | --- |
  | dawn | `#F2B27A`, low | long shadows |
  | noon | `#FFF4E0`, high | short shadows |
  | dusk | `#E9875A`, low | amber glass roofs glow |
  | night | moon `#8FA8C8` | window and lantern emissives on, an ambient floor keeps the board readable |

  The shadow map is re-rendered only when a build or sell happens or the sun keyframe
  changes, at most once per turn.
- **District silhouettes.** Each must read from the skyline alone:
  - kelp: low stilt shacks with drying racks over the shallows, wide and flat
  - reef: squat round stone towers behind a sea wall
  - coral: stepped terraces with rounded domes
  - driftwood: leaning timber A-frames, deliberately crooked
  - amber: glasshouse workshops whose roofs glow at dusk
  - cinder: dark basalt foundries with chimneys and smoke, the sharpest spikes
  - jade: steep verdigris-roofed merchant halls
  - crown: harbour-master towers with flag masts, the highest skyline
- **Building levels.** Each depot level adds a storey. A port (`PORT_LEVEL`) adds a crane and
  quay. A mortgaged lot closes its shutters and greys its sail to `paper-deep`.
- **Life.** A few instanced boats and gulls on fixed loops, high tier only.
- **Assets.** Procedural geometry first. Kenney CC0 kits may be used only when recoloured
  through the palette texture. No Monopoly shapes, colours or text.

## Quality tiers

Chosen by drei `PerformanceMonitor`, and the player can override them. Low-power also turns
on with `prefers-reduced-motion`.

| | High | Medium | Low-power |
| --- | --- | --- | --- |
| DPR | min(device, 2) | 1.5 | 1 |
| Shadows | 2048 map, updated on change only | 1024 map | Off, blob decals |
| Outlines | Hull plus edge pass | Hull only | Hull on buildings only |
| Post-processing | Edge pass, light bloom on lanterns | None | None |
| Water | Animated shader | Static normal map | Flat colour |
| Boats and gulls | On | Off | Off |
| Frame loop | Always | Always | `frameloop="demand"`, renders only on change |

Every tier stays under 150 draw calls, uses instanced buildings and caps DPR at 2. The target
is 60 fps on the integrated Radeon 890M at the medium tier.
