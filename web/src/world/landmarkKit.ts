import { BufferAttribute, ConeGeometry, CylinderGeometry, DodecahedronGeometry, Matrix4, PlaneGeometry, SphereGeometry, TorusGeometry, Vector3, type BufferGeometry } from "three";
import { spaces } from "./board";
import { box, merge, part, post, prism } from "./geometry";
import { lotTransform } from "./layout";

/*
 * Signature props: one per named space, built from the same boxes, prisms and posts as the
 * district kit and merged with every other prop into one mesh (one draw call plus its hull).
 * Each prop stands behind its lot, toward the outer shore, so it never hides the storeys,
 * awnings or the road. Lit glass uses the `world.glow` cell, so it shines in the night mood.
 */

export type PropKind =
  | "customsHouse" | "dryingRack" | "rowboat" | "tideGauge" | "barrels" | "jetty" | "cairn"
  | "ledgerCrates" | "fishMarket" | "bollard" | "coralDome" | "staghorn" | "saltworks"
  | "lighthouse" | "brig" | "tavern" | "shipyard" | "ropeWalk" | "palm" | "kiln" | "resinVats"
  | "beehive" | "forge" | "anvil" | "waterwheel" | "slagHeap" | "drum" | "bellTower"
  | "figurehead" | "observatory" | "anchor" | "treasury";

/** The prop for each space index, in board order. `board.test`-style check: one entry per space. */
export const LANDMARKS: readonly PropKind[] = [
  "customsHouse", // 0 Home Quay
  "dryingRack", // 1 Bladderwrack Flats
  "rowboat", // 2 Oarweed Shoal
  "tideGauge", // 3 Tide
  "barrels", // 4 Sugarkelp Bank
  "jetty", // 5 Northwind Ferry
  "cairn", // 6 Limpet Rocks
  "ledgerCrates", // 7 Ledger
  "fishMarket", // 8 Whelk Ledge
  "bollard", // 9 Mooring Fee
  "coralDome", // 10 Brain Coral Atoll
  "staghorn", // 11 Staghorn Key
  "saltworks", // 12 Saltworks
  "lighthouse", // 13 Fan Coral Cay
  "brig", // 14 The Brig
  "tavern", // 15 Tinder Bay
  "tideGauge", // 16 Tide
  "shipyard", // 17 Splinter Sound
  "ropeWalk", // 18 Hollow Log Isle
  "jetty", // 19 Eastwind Ferry
  "palm", // 20 Calm Waters
  "kiln", // 21 Honeyglass Strand
  "ledgerCrates", // 22 Ledger
  "resinVats", // 23 Resin Point
  "beehive", // 24 Goldfly Reach
  "forge", // 25 Ashfall Inlet
  "anvil", // 26 Emberstone
  "waterwheel", // 27 Tidal Mill
  "slagHeap", // 28 Slag Harbor
  "kiln", // 29 Pumice Spit
  "jetty", // 30 Southwind Ferry
  "drum", // 31 Press Gang
  "bellTower", // 32 Verdigris Haven
  "ledgerCrates", // 33 Ledger
  "figurehead", // 34 Serpentine Cove
  "observatory", // 35 Malachite Rise
  "anchor", // 36 Anchor Toll
  "customsHouse", // 37 Regent's Landing
  "tideGauge", // 38 Tide
  "treasury", // 39 Sovereign Pier
];

/** Where a prop stands in lot space: centred, behind the building, toward the outer shore. */
export const PROP_OFFSET: readonly [number, number, number] = [0, 0, -0.95];

type V3 = [number, number, number];
/** A prop's parts in prop space, plus the tops of any flag poles (a waving flag is hung there). */
interface Prop {
  parts: BufferGeometry[];
  flags?: V3[];
}

const cyl = (r: number, h: number, seg = 8, rTop = r) => new CylinderGeometry(rTop, r, h, seg).translate(0, h / 2, 0);
const glow = (w: number, h: number, at: V3) => part(box(w, h, 0.03), "world.glow", { at });
const lantern = (at: V3) => part(box(0.07, 0.09, 0.07), "world.glow", { at });
const pole = (h: number, at: V3 = [0, 0, 0]) => part(post(0.018, h), "ink", { at });

const BUILD: Record<PropKind, () => Prop> = {
  customsHouse: () => ({
    parts: [
      part(box(0.62, 0.36, 0.34), "paper"),
      part(prism(0.68, 0.18, 0.4), "tide", { at: [0, 0.36, 0] }),
      ...[-0.22, 0, 0.22].map((x) => part(post(0.025, 0.32), "sailcloth", { at: [x, 0, 0.2] })),
      glow(0.1, 0.1, [-0.15, 0.2, 0.18]),
      glow(0.1, 0.1, [0.15, 0.2, 0.18]),
      pole(0.5, [0.26, 0.36, -0.08]),
    ],
    flags: [[0.26, 0.82, -0.08]],
  }),
  dryingRack: () => ({
    parts: [
      ...[-0.25, 0.25].map((x) => part(post(0.02, 0.32), "district.driftwood", { at: [x, 0, 0] })),
      part(box(0.56, 0.02, 0.02), "district.driftwood", { at: [0, 0.3, 0] }),
      ...[-0.15, 0, 0.15].map((x) => part(box(0.08, 0.2, 0.01), "district.kelp", { at: [x, 0.1, 0] })),
    ],
  }),
  rowboat: () => ({
    parts: [
      part(new SphereGeometry(0.2, 8, 4, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2).scale(1.6, 0.6, 0.7).translate(0, 0.12, 0), "district.driftwood"),
      part(box(0.04, 0.02, 0.5), "paperDeep", { at: [0.05, 0.1, 0], rot: [0, 1.3, 0] }),
    ],
  }),
  tideGauge: () => ({
    parts: [
      part(post(0.035, 0.7), "sailcloth"),
      ...[0.12, 0.3, 0.48].map((y) => part(cyl(0.045, 0.06, 6), "tide", { at: [0, y, 0] })),
      lantern([0, 0.7, 0]),
    ],
  }),
  barrels: () => ({
    parts: [
      part(cyl(0.1, 0.2, 7), "district.driftwood", { at: [-0.12, 0, 0] }),
      part(cyl(0.1, 0.2, 7), "district.driftwood", { at: [0.12, 0, 0.04] }),
      part(cyl(0.1, 0.2, 7), "district.driftwood", { at: [0, 0.2, 0.02] }),
    ],
  }),
  jetty: () => ({
    parts: [
      part(box(0.3, 0.04, 0.8), "district.driftwood", { at: [0, 0.12, -0.1] }),
      ...[-0.12, 0.12].flatMap((x) => [-0.4, 0.2].map((z) => part(post(0.025, 0.14), "district.driftwood", { at: [x, 0, z] }))),
      pole(0.42, [0.12, 0.16, -0.45]),
      lantern([0.12, 0.58, -0.45]),
    ],
  }),
  cairn: () => ({
    parts: [
      part(new DodecahedronGeometry(0.2, 0).scale(1.2, 0.6, 1).translate(0, 0.1, 0), "world.basalt"),
      part(new DodecahedronGeometry(0.13, 0).translate(0.04, 0.3, 0), "paperDeep"),
      part(new DodecahedronGeometry(0.08, 0).translate(0, 0.46, 0), "world.basalt"),
    ],
  }),
  ledgerCrates: () => ({
    parts: [
      part(box(0.24, 0.2, 0.24), "district.driftwood", { at: [-0.12, 0, 0] }),
      part(box(0.2, 0.18, 0.2), "paperDeep", { at: [0.14, 0, 0.04], rot: [0, 0.4, 0] }),
      part(box(0.18, 0.16, 0.18), "district.driftwood", { at: [-0.1, 0.2, 0], rot: [0, 0.3, 0] }),
    ],
  }),
  fishMarket: () => ({
    parts: [
      part(box(0.6, 0.16, 0.3), "paperDeep"),
      ...[-0.28, 0.28].map((x) => part(post(0.02, 0.42), "district.driftwood", { at: [x, 0, 0.13] })),
      part(prism(0.66, 0.12, 0.38), "district.reef", { at: [0, 0.42, 0] }),
      ...[-0.16, 0, 0.16].map((x) => part(new ConeGeometry(0.04, 0.16, 4).rotateZ(Math.PI / 2), "tide", { at: [x, 0.2, 0.05] })),
      lantern([0, 0.36, 0.14]),
    ],
  }),
  bollard: () => ({
    parts: [
      part(cyl(0.1, 0.26, 8, 0.08), "ink"),
      part(cyl(0.13, 0.04, 8), "ink", { at: [0, 0.26, 0] }),
      part(new TorusGeometry(0.12, 0.018, 4, 10).rotateX(Math.PI / 2), "inkSoft", { at: [0, 0.1, 0] }),
    ],
  }),
  coralDome: () => ({
    parts: [
      part(new SphereGeometry(0.28, 10, 6, 0, Math.PI * 2, 0, Math.PI / 2), "district.coral"),
      part(new SphereGeometry(0.12, 8, 5, 0, Math.PI * 2, 0, Math.PI / 2), "sailcloth", { at: [0.24, 0, 0.12] }),
    ],
  }),
  staghorn: () => ({
    parts: [-0.6, -0.2, 0.25, 0.6].map((tilt, i) => part(new ConeGeometry(0.04, 0.5 - i * 0.06, 5).translate(0, 0.25, 0), "district.coral", { at: [i * 0.08 - 0.12, 0, 0], rot: [0, 0, tilt] })),
  }),
  saltworks: () => ({
    parts: [
      part(box(0.7, 0.04, 0.4), "world.road"),
      part(box(0.32, 0.03, 0.18), "sailcloth", { at: [-0.16, 0.04, 0] }),
      part(new ConeGeometry(0.14, 0.24, 7).translate(0, 0.12, 0), "sailcloth", { at: [0.2, 0.04, 0] }),
    ],
  }),
  lighthouse: () => ({
    parts: [
      part(cyl(0.2, 0.1, 8), "world.basalt"),
      part(cyl(0.16, 0.8, 8, 0.12), "sailcloth", { at: [0, 0.1, 0] }),
      part(cyl(0.165, 0.12, 8), "district.coral", { at: [0, 0.4, 0] }),
      part(cyl(0.13, 0.12, 8), "world.glow", { at: [0, 0.9, 0] }),
      part(new ConeGeometry(0.16, 0.16, 8).translate(0, 0.08, 0), "district.coral", { at: [0, 1.02, 0] }),
    ],
  }),
  brig: () => ({
    parts: [
      part(box(0.6, 0.4, 0.36), "world.basalt"),
      ...[-0.15, -0.05, 0.05, 0.15].map((x) => part(post(0.012, 0.18), "ink", { at: [x, 0.12, 0.185] })),
      part(box(0.66, 0.05, 0.42), "inkSoft", { at: [0, 0.4, 0] }),
      lantern([0.25, 0.32, 0.2]),
    ],
  }),
  tavern: () => ({
    parts: [
      part(box(0.56, 0.36, 0.36), "paper"),
      part(prism(0.62, 0.22, 0.42), "district.driftwood", { at: [0, 0.36, 0] }),
      part(box(0.08, 0.26, 0.08), "world.basalt", { at: [-0.18, 0.4, -0.06] }),
      glow(0.12, 0.1, [-0.14, 0.18, 0.18]),
      glow(0.12, 0.1, [0.14, 0.18, 0.18]),
      part(box(0.02, 0.02, 0.16), "ink", { at: [0.3, 0.3, 0.22] }),
      part(cyl(0.045, 0.08, 6), "brass", { at: [0.3, 0.2, 0.28] }),
      part(cyl(0.07, 0.14, 6), "district.driftwood", { at: [0.36, 0, 0.12] }),
    ],
  }),
  shipyard: () => ({
    parts: [
      part(new SphereGeometry(0.2, 8, 4, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2).scale(1.8, 0.8, 0.8).translate(0, 0.18, 0), "district.driftwood"),
      part(box(0.03, 0.62, 0.03), "district.driftwood", { at: [-0.22, 0, -0.12], rot: [0, 0, -0.35] }),
      part(box(0.03, 0.62, 0.03), "district.driftwood", { at: [0.22, 0, -0.12], rot: [0, 0, 0.35] }),
      part(box(0.03, 0.03, 0.4), "district.driftwood", { at: [0, 0.57, 0.06] }),
      part(post(0.005, 0.2), "inkSoft", { at: [0, 0.37, 0.24] }),
      part(box(0.22, 0.03, 0.05), "paperDeep", { at: [0, 0.34, 0.24] }),
    ],
  }),
  ropeWalk: () => ({
    parts: [
      part(box(0.9, 0.16, 0.18), "paperDeep"),
      part(prism(0.22, 0.08, 0.9).rotateY(Math.PI / 2), "district.driftwood", { at: [0, 0.16, 0] }),
      ...[-0.36, 0, 0.36].map((x) => part(post(0.015, 0.22), "ink", { at: [x, 0, 0.16] })),
      part(box(0.8, 0.012, 0.012), "world.road", { at: [0, 0.2, 0.16] }),
    ],
  }),
  palm: () => ({
    parts: [
      part(cyl(0.035, 0.7, 5, 0.025), "district.driftwood", { rot: [0, 0, 0.12] }),
      ...[0, 1, 2, 3, 4].map((i) => part(new ConeGeometry(0.06, 0.34, 3).rotateZ(Math.PI / 2 + 0.5).rotateY((i * Math.PI * 2) / 5), "ok", { at: [-0.08, 0.68, 0] })),
    ],
  }),
  kiln: () => ({
    parts: [
      part(new SphereGeometry(0.24, 8, 5, 0, Math.PI * 2, 0, Math.PI / 2).scale(1, 1.2, 1), "world.road"),
      part(cyl(0.05, 0.3, 6), "world.basalt", { at: [0.1, 0.18, -0.06] }),
      glow(0.1, 0.08, [0, 0.06, 0.23]),
    ],
  }),
  resinVats: () => ({
    parts: [-0.18, 0.18].flatMap((x) => [part(cyl(0.13, 0.18, 8), "district.amber", { at: [x, 0, 0] }), part(cyl(0.11, 0.02, 8), "world.glow", { at: [x, 0.18, 0] })]),
  }),
  beehive: () => ({
    parts: [0, 1, 2, 3].map((i) => part(cyl(0.16 - i * 0.03, 0.1, 8), i % 2 ? "brass" : "district.amber", { at: [0, i * 0.1, 0] })),
  }),
  forge: () => ({
    parts: [
      part(box(0.4, 0.26, 0.3), "world.basalt"),
      part(cyl(0.06, 0.7, 6, 0.045), "world.basalt", { at: [0.12, 0, -0.06] }),
      glow(0.16, 0.12, [-0.06, 0.06, 0.16]),
    ],
  }),
  anvil: () => ({
    parts: [
      part(cyl(0.09, 0.18, 6), "district.driftwood"),
      part(box(0.28, 0.08, 0.12), "ink", { at: [0, 0.18, 0] }),
      part(new ConeGeometry(0.05, 0.12, 4).rotateZ(-Math.PI / 2), "ink", { at: [0.19, 0.22, 0] }),
    ],
  }),
  waterwheel: () => ({
    parts: [
      part(box(0.34, 0.3, 0.3), "paper"),
      part(prism(0.38, 0.14, 0.34), "district.driftwood", { at: [0, 0.3, 0] }),
      part(new TorusGeometry(0.2, 0.025, 4, 12).rotateY(Math.PI / 2), "district.driftwood", { at: [0.22, 0.2, 0] }),
      part(box(0.02, 0.38, 0.03), "district.driftwood", { at: [0.22, 0.01, 0] }),
      part(box(0.02, 0.03, 0.38), "district.driftwood", { at: [0.22, 0.2, 0] }),
    ],
  }),
  slagHeap: () => ({
    parts: [
      part(new ConeGeometry(0.3, 0.32, 6).translate(0, 0.16, 0), "world.basalt"),
      part(new ConeGeometry(0.16, 0.2, 5).translate(0, 0.1, 0), "district.cinder", { at: [0.26, 0, 0.1] }),
      glow(0.06, 0.04, [0, 0.12, 0.26]),
    ],
  }),
  drum: () => ({
    parts: [
      part(cyl(0.14, 0.2, 10), "danger"),
      part(cyl(0.145, 0.03, 10), "sailcloth", { at: [0, 0.2, 0] }),
      pole(0.6, [0.2, 0, 0]),
    ],
    flags: [[0.2, 0.58, 0]],
  }),
  bellTower: () => ({
    parts: [
      part(box(0.26, 0.6, 0.26), "paper"),
      ...[-0.1, 0.1].flatMap((x) => [-0.1, 0.1].map((z) => part(post(0.02, 0.2), "paper", { at: [x, 0.6, z] }))),
      part(new ConeGeometry(0.07, 0.1, 8).translate(0, -0.05, 0), "brass", { at: [0, 0.78, 0] }),
      part(new ConeGeometry(0.22, 0.26, 4).rotateY(Math.PI / 4).translate(0, 0.13, 0), "district.jade", { at: [0, 0.8, 0] }),
    ],
  }),
  figurehead: () => ({
    parts: [0, 1, 2].map((i) => part(new TorusGeometry(0.1, 0.035, 4, 8, Math.PI).rotateY(Math.PI / 2), "district.jade", { at: [0, 0.04, i * 0.18 - 0.18] })).concat([
      part(new ConeGeometry(0.06, 0.16, 5).rotateX(-Math.PI / 2.4), "district.jade", { at: [0, 0.18, 0.3] }),
    ]),
  }),
  observatory: () => ({
    parts: [
      part(cyl(0.22, 0.3, 10), "paper"),
      part(new SphereGeometry(0.22, 10, 5, 0, Math.PI * 2, 0, Math.PI / 2), "district.jade", { at: [0, 0.3, 0] }),
      part(cyl(0.03, 0.22, 6), "brass", { at: [0.06, 0.38, 0.06], rot: [0.6, 0, 0] }),
      glow(0.08, 0.08, [0, 0.14, 0.22]),
    ],
  }),
  anchor: () => ({
    parts: [
      part(box(0.05, 0.5, 0.05), "ink"),
      part(box(0.26, 0.04, 0.04), "ink", { at: [0, 0.4, 0] }),
      part(new TorusGeometry(0.16, 0.025, 4, 10, Math.PI).rotateZ(Math.PI), "ink", { at: [0, 0.16, 0] }),
      part(new TorusGeometry(0.05, 0.016, 4, 8), "ink", { at: [0, 0.54, 0] }),
    ],
  }),
  treasury: () => ({
    parts: [
      part(box(0.66, 0.08, 0.4), "paperDeep"),
      part(box(0.56, 0.36, 0.32), "sailcloth", { at: [0, 0.08, 0] }),
      ...[-0.2, -0.07, 0.07, 0.2].map((x) => part(post(0.025, 0.36), "paper", { at: [x, 0.08, 0.19] })),
      part(prism(0.62, 0.16, 0.38), "district.crown", { at: [0, 0.44, 0] }),
      part(new SphereGeometry(0.1, 8, 4, 0, Math.PI * 2, 0, Math.PI / 2), "brass", { at: [0, 0.56, -0.04] }),
      glow(0.1, 0.12, [0, 0.16, 0.17]),
      pole(0.4, [-0.24, 0.44, -0.1]),
    ],
    flags: [[-0.24, 0.82, -0.1]],
  }),
};

/** Lot-space matrix for a prop behind lot `index`. */
function propMatrix(index: number): Matrix4 {
  const { x, z, rotY } = lotTransform(index);
  const lot = new Matrix4().makeRotationY(rotY).setPosition(x, 0, z);
  return lot.multiply(new Matrix4().makeTranslation(...PROP_OFFSET));
}

/**
 * Every signature prop on the atoll as one merged mesh, plus world positions and headings of
 * the flags that hang from their poles (the flags are a separate instanced, waving mesh).
 */
export function landmarkGeometry(): { geometry: BufferGeometry; flags: { at: Vector3; rotY: number }[] } {
  const parts: BufferGeometry[] = [];
  const flags: { at: Vector3; rotY: number }[] = [];
  spaces.forEach((space) => {
    const prop = BUILD[LANDMARKS[space.index]]();
    const m = propMatrix(space.index);
    for (const g of prop.parts) parts.push(g.applyMatrix4(m));
    for (const f of prop.flags ?? []) flags.push({ at: new Vector3(...f).applyMatrix4(m), rotY: lotTransform(space.index).rotY });
  });
  return { geometry: merge(parts), flags };
}

/** Prop kinds that exist only as data, for tests: every kind in `LANDMARKS` has a builder. */
export const PROP_KINDS = Object.keys(BUILD) as PropKind[];

const OUTLINE_PUSH = 0.012;
const FLAG_W = 0.3;
const FLAG_H = 0.18;

/** A flag that hangs from x = 0: `aSway` grows from 0 at the pole to 1 at the free edge. */
export function flagGeometry(): BufferGeometry {
  const g = part(new PlaneGeometry(FLAG_W, FLAG_H, 6, 1).translate(FLAG_W / 2, -FLAG_H / 2, 0), "world.white");
  const pos = g.getAttribute("position");
  const sway = new Float32Array(pos.count);
  for (let i = 0; i < pos.count; i += 1) sway[i] = pos.getX(i) / FLAG_W;
  g.setAttribute("aSway", new BufferAttribute(sway, 1));
  return g;
}

/**
 * Hull outline by normal push: each vertex moves out along its normal, drawn back-faced in ink.
 * A merged world-space mesh cannot be scaled about one centre, so this replaces the scale hull.
 */
export function pushedHull(geometry: BufferGeometry): BufferGeometry {
  const g = geometry.clone();
  const pos = g.getAttribute("position");
  const nrm = g.getAttribute("normal");
  for (let i = 0; i < pos.count; i += 1) {
    pos.setXYZ(i, pos.getX(i) + nrm.getX(i) * OUTLINE_PUSH, pos.getY(i) + nrm.getY(i) * OUTLINE_PUSH, pos.getZ(i) + nrm.getZ(i) * OUTLINE_PUSH);
  }
  return g;
}

/** One galleon in its own space: bow toward +z, sails carry `aSway` so they belly in the wind. */
export function galleonGeometry(): BufferGeometry {
  const sail = (w: number, h: number, at: [number, number, number]) => {
    const g = part(new PlaneGeometry(w, h, 1, 4).rotateY(Math.PI / 2), "sailcloth", { at });
    const pos = g.getAttribute("position");
    const sway = new Float32Array(pos.count);
    // Belly is greatest mid-height and zero at the yards, top and bottom.
    for (let i = 0; i < pos.count; i += 1) sway[i] = Math.sin(((pos.getY(i) - (at[1] - h / 2)) / h) * Math.PI) * 0.6;
    g.setAttribute("aSway", new BufferAttribute(sway, 1));
    return g;
  };
  const rigid = (g: BufferGeometry) => {
    g.setAttribute("aSway", new BufferAttribute(new Float32Array(g.getAttribute("position").count), 1));
    return g;
  };
  return merge([
    rigid(part(new SphereGeometry(0.5, 8, 4, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2).scale(0.9, 0.7, 2.6), "district.driftwood", { at: [0, 0.25, 0] })),
    rigid(part(box(0.8, 0.06, 2.2), "paperDeep", { at: [0, 0.22, 0] })),
    rigid(part(box(0.78, 0.4, 0.5), "district.driftwood", { at: [0, 0.25, -0.95] })),
    rigid(part(box(0.5, 0.12, 0.04), "world.glow", { at: [0, 0.45, -1.21] })),
    rigid(part(post(0.04, 2.1), "district.driftwood", { at: [0, 0.25, 0.35] })),
    rigid(part(post(0.035, 1.7), "district.driftwood", { at: [0, 0.25, -0.5] })),
    rigid(part(new CylinderGeometry(0.02, 0.03, 1.1, 4).rotateX(Math.PI / 2.6), "district.driftwood", { at: [0, 0.6, 1.4] })),
    sail(1.1, 0.8, [0, 1.0, 0.35]),
    sail(0.9, 0.6, [0, 1.85, 0.35]),
    sail(0.9, 0.7, [0, 0.95, -0.5]),
    rigid(part(box(0.02, 0.18, 0.3), "danger", { at: [0, 2.25, 0.5] })),
  ]);
}

