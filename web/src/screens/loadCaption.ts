import type { LoadPhase } from "../runtime/protocol";

/** What the loading signboard says during each engine load step. */
export const LOAD_CAPTION: Record<LoadPhase, string> = {
  core: "Laying the reef",
  numpy: "Charting the tides",
  bundle: "Raising the districts",
  engine: "Seating the rivals",
  ready: "Harbour open",
};
