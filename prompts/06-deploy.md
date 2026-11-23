Task 6: deploy. Read docs/web/handoff/integrate.md. Start in plan mode.

1. Add `web/vercel.json` with the cross-origin isolation headers if the runtime needs
   them (`Cross-Origin-Opener-Policy: same-origin`,
   `Cross-Origin-Embedder-Policy: require-corp`), long cache headers for the runtime and
   model files, and SPA rewrites if routing needs them.
2. Make sure `npm run build` in `web/` passes and `npm run preview` works with the
   headers.
3. Add CI: ruff, `pytest -m "not slow"`, and Vitest on every push. Do not add
   agent-browser to CI.
4. Push the branch. Then print:

HOSTING NEEDED: The site is ready for its first deploy. In Vercel: Add New -> Project ->
import DhemanthN/saltmarket_Monopoly_bot -> Root Directory `web` -> Deploy. Then
Settings -> Deployment Protection -> turn off Vercel Authentication for previews. Paste
the preview URL for branch <branch> here.

   Send the same text with `runpane notify` and wait. Never run `vercel` yourself.
5. When I paste the URL: open it with agent-browser, confirm the page loads with zero
   console errors and that `crossOriginIsolated` is true in the page, and report.

Handoff (include the production and preview URLs), commit, push.
