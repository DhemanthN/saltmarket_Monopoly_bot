# References for Saltmarket 3D

Take one idea from each. Never copy a look, model, texture, or layout wholesale.

## 3D world and feel

| Reference | Take this |
| --- | --- |
| Messenger by Abeto — https://messenger.abeto.co/ (case study: https://www.awwwards.com/messenger.html) | A tiny world you can walk all the way around; ink outlines; one 16x16 palette texture holds every colour so a mood change is one swap; NPCs that make the place feel lived in |
| Bruno Simon 2025 portfolio — https://www.awwwards.com/brunos-portfolio-case-study.html (source, MIT: https://github.com/brunosimon/folio-2025) | Third-person play in a toy world; physics that invite poking; WebGPU when available with WebGL fallback |
| Windland (Codrops) — https://tympanus.net/codrops/2022/04/25/case-study-windland-an-immersive-three-js-experience/ | Realistic light on low-poly buildings; post-effects chosen for mood without killing frame rate |
| outlol lobby — https://discourse.threejs.org/t/outlol-multiplayer-browser-football-and-foosball-3d-view-in-three-js/94799 | Low-poly city island; instanced buildings; shadow map rebuilt only when the scene changes |
| 7 small 3D games, ~900 KB each — https://discourse.threejs.org/t/7-small-3d-browser-games-with-zero-model-texture-or-audio-files-900-kb-each/95438 | Procedural geometry keeps a 3D game tiny (three.js, Vite, postprocessing) |
| Threescaper — https://boingboing.net/2024/06/17/explore-your-townscaper-towns-in-the-first-person-perspective-again.html | Dropping from god view into first person in a small town: our street view / chart view pair |
| Kenney City Kits (CC0) — https://kenney-assets.itch.io/city-kit-suburban | Free low-poly GLB buildings and roads to start from; recolour through our palette |
| R3F scaling performance — https://r3f.docs.pmnd.rs/advanced/scaling-performance | Instancing, on-demand frames, PerformanceMonitor quality tiers |

## 2D interface

The owner decided not to use Mobbin (2026-11-23). The patterns for each Saltmarket moment
(buy or pass, auction, trade, cash and rent, first game, game over) are written in
`DESIGN.md`, section "HUD patterns per moment".
