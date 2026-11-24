import boardData from "../../../data/board.json";
import { districts, type DistrictName } from "../styles/tokens";

export interface BoardSpace {
  index: number;
  name: string;
  kind: string;
  district: DistrictName | null;
  /** Purchase price for buyable spaces, from data/board.json. */
  price: number | null;
}

interface RawSpace {
  index: number;
  name: string;
  kind: string;
  group?: string;
  price?: number;
}

function isDistrict(group: string | undefined): group is DistrictName {
  return group !== undefined && group in districts;
}

/** The 40 spaces of data/board.json, in walking order. Space 0 is Home Quay. */
export const spaces: readonly BoardSpace[] = (boardData.spaces as RawSpace[]).map((s) => ({
  index: s.index,
  name: s.name,
  kind: s.kind,
  district: isDistrict(s.group) ? s.group : null,
  price: s.price ?? null,
}));

/** Height of the lot's silhouette, so each district reads from the skyline alone. */
export const DISTRICT_HEIGHT: Record<DistrictName, number> = {
  kelp: 0.5,
  reef: 0.9,
  coral: 1.1,
  driftwood: 0.9,
  amber: 1.0,
  cinder: 1.6,
  jade: 1.3,
  crown: 2.1,
};

export const RING_RADIUS = 9;

/** Position of a space on the ring road. Space 0 sits at the front, and play runs clockwise from above. */
export function ringPosition(index: number, count = spaces.length): { x: number; z: number; angle: number } {
  const angle = Math.PI / 2 - (index / count) * Math.PI * 2;
  return { x: Math.cos(angle) * RING_RADIUS, z: Math.sin(angle) * RING_RADIUS, angle };
}

/** Index of The Brig, where `brig_in` sends a piece. */
export const BRIG_SPACE = spaces.findIndex((s) => s.kind === "brig");
