/**
 * Typed mirror of tokens.css for the 3D side. Source of truth: docs/web/DESIGN.md.
 * tokens.test.ts fails if a value here drifts from tokens.css.
 */

export const palette = {
  paper: "#F3EAD7",
  paperDeep: "#E6D8BC",
  sailcloth: "#FBF7EE",
  ink: "#1F2A2E",
  inkSoft: "#4A5558",
  brass: "#8A6A1F",
  tide: "#1E5A66",
  focus: "#0B5CAD",
  danger: "#A3261A",
  ok: "#2E6B34",
  night: "#16232B",
  nightPanel: "#22333C",
  nightText: "#EDE3CF",
} as const;

export const districts = {
  kelp: "#4F7A3A",
  reef: "#B5523B",
  coral: "#C2456B",
  driftwood: "#7A5A3C",
  amber: "#96680F",
  cinder: "#5B4A4E",
  jade: "#2E7E6A",
  crown: "#3B4F8C",
} as const;

export type DistrictName = keyof typeof districts;

export const seats = {
  saffron: "#D9A21B",
  teal: "#137C86",
  vermilion: "#B8321A",
  indigo: "#3A2F7A",
} as const;

export type SeatName = keyof typeof seats;

/** Seats in table order. Each also has an emblem so colour is never the only cue. */
export const seatOrder: readonly { name: SeatName; emblem: EmblemName; label: string }[] = [
  { name: "saffron", emblem: "sun", label: "Sun" },
  { name: "teal", emblem: "wave", label: "Wave" },
  { name: "vermilion", emblem: "star", label: "Star" },
  { name: "indigo", emblem: "anchor", label: "Anchor" },
];

export type EmblemName = "sun" | "wave" | "star" | "anchor";

export const motion = {
  quick: { ms: 120, easing: [0.2, 0, 0, 1] },
  standard: { ms: 240, easing: [0.3, 0, 0, 1] },
  travel: { ms: 480, easing: [0.65, 0, 0.35, 1] },
} as const;

export const zLayers = {
  canvas: 0,
  worldLabel: 100,
  hudRail: 200,
  decision: 300,
  coach: 400,
  toast: 500,
  modal: 600,
  dev: 900,
} as const;

export const spacing = [4, 8, 12, 16, 20, 24, 32, 40, 48, 64] as const;

export const typeScale = [
  { name: "caption", size: 12, line: 16 },
  { name: "small", size: 14, line: 20 },
  { name: "body", size: 16, line: 24 },
  { name: "h4", size: 20, line: 28 },
  { name: "h3", size: 25, line: 32 },
  { name: "h2", size: 31, line: 36 },
  { name: "h1", size: 39, line: 44 },
  { name: "display", size: 49, line: 52 },
] as const;

/** Time-of-day keyframes for the sun light (DESIGN.md, "Lighting by time of day"). */
export const sunKeyframes = {
  dawn: "#F2B27A",
  noon: "#FFF4E0",
  dusk: "#E9875A",
  night: "#8FA8C8",
} as const;

export type Mood = "day" | "night";

/**
 * World-only colours (not UI tokens, so not in tokens.css). Sea and lagoon differ from the
 * sky so the horizon reads as a line, not a gradient. `white` is the tint cell: instanced
 * sails sample it and take the owner colour from their instance colour.
 */
export const worldColors = {
  sky: "#EBC9A0",
  sea: "#2C6E7A",
  lagoon: "#6FA3A8",
  sand: "#E2CFA6",
  road: "#B9A98A",
  basalt: "#3A3436",
  white: "#FFFFFF",
  /** Lit window and lantern glass. Dark in the day texture; the night emissive texture lights this cell. */
  glow: "#F7C873",
} as const;

/** WCAG 2.x relative luminance of a `#RRGGBB` colour. */
export function relativeLuminance(hex: string): number {
  const [r, g, b] = parseHex(hex).map((c) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** WCAG 2.x contrast ratio between two `#RRGGBB` colours, from 1 to 21. */
export function contrastRatio(a: string, b: string): number {
  const [hi, lo] = [relativeLuminance(a), relativeLuminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

function parseHex(hex: string): [number, number, number] {
  const n = Number.parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function mix(a: string, b: string, t: number): string {
  const [ar, ag, ab] = parseHex(a);
  const [br, bg, bb] = parseHex(b);
  const channel = (x: number, y: number) => Math.round(x + (y - x) * t);
  const n = (channel(ar, br) << 16) | (channel(ag, bg) << 8) | channel(ab, bb);
  return `#${n.toString(16).padStart(6, "0").toUpperCase()}`;
}

const cellEntries: readonly (readonly [string, string])[] = [
  ["paper", palette.paper],
  ["paperDeep", palette.paperDeep],
  ["sailcloth", palette.sailcloth],
  ["ink", palette.ink],
  ["inkSoft", palette.inkSoft],
  ["brass", palette.brass],
  ["tide", palette.tide],
  ["danger", palette.danger],
  ["ok", palette.ok],
  ...Object.entries(districts).map(([k, v]) => [`district.${k}`, v] as const),
  ...Object.entries(seats).map(([k, v]) => [`seat.${k}`, v] as const),
  ...Object.entries(worldColors).map(([k, v]) => [`world.${k}`, v] as const),
];

/** Every colour a world mesh may use, in cell order. A mesh maps its UVs into one cell. */
export const paletteCells: readonly string[] = cellEntries.map(([, hex]) => hex);

/** Index of a named colour in `paletteCells`, for UV lookups. */
export const cellIndex: Readonly<Record<string, number>> = Object.fromEntries(
  cellEntries.map(([name], i) => [name, i]),
);

export const PALETTE_TEXTURE_SIZE = 16;

/**
 * Build the 16x16 RGBA palette texture. Day uses the token colours. Night pulls each
 * colour toward the moonlight: dark cells move further (up to 50%) so basalt and cinder
 * keep their shape at night, light cells only 15%. A mood change is one texture swap and
 * both moods share one cell map.
 */
export function buildPaletteTexture(mood: Mood): Uint8Array {
  const size = PALETTE_TEXTURE_SIZE;
  const data = new Uint8Array(size * size * 4);
  paletteCells.forEach((hex, i) => {
    const lift = 0.15 + 0.35 * (1 - Math.sqrt(relativeLuminance(hex)));
    const [r, g, b] = parseHex(mood === "night" ? mix(hex, sunKeyframes.night, lift) : hex);
    data.set([r, g, b, 255], i * 4);
  });
  return data;
}

/** Palette cells that give off light at night (windows and lamps). Every other cell stays dark. */
export const glowCells: readonly string[] = ["world.glow"];

/** Build the emissive twin of the palette texture: glow cells in colour, all others black. */
export function buildEmissiveTexture(): Uint8Array {
  const size = PALETTE_TEXTURE_SIZE;
  const data = new Uint8Array(size * size * 4);
  for (let i = 0; i < size * size; i += 1) data[i * 4 + 3] = 255;
  for (const name of glowCells) {
    const index = cellIndex[name];
    data.set([...parseHex(paletteCells[index]), 255], index * 4);
  }
  return data;
}
