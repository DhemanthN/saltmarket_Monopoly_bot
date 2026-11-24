import { BufferGeometry, DataTexture, type Texture, NearestFilter, RGBAFormat, SRGBColorSpace } from "three";
import { PALETTE_TEXTURE_SIZE, buildEmissiveTexture, buildPaletteTexture, cellIndex, type Mood } from "../styles/tokens";

/** Names of palette cells, e.g. "ink", "district.reef", "world.sea". */
export type CellName = keyof typeof cellIndex & string;

const cache = new Map<Mood, DataTexture>();

/** The one colour texture for the world. Day and night share the cell map, so a mood change is a swap. */
export function paletteTexture(mood: Mood): DataTexture {
  const cached = cache.get(mood);
  if (cached) return cached;
  const size = PALETTE_TEXTURE_SIZE;
  const texture = new DataTexture(buildPaletteTexture(mood), size, size, RGBAFormat);
  texture.magFilter = NearestFilter;
  texture.minFilter = NearestFilter;
  texture.colorSpace = SRGBColorSpace;
  texture.needsUpdate = true;
  cache.set(mood, texture);
  return texture;
}

/**
 * Night glass shines above 1.0 so the High tier's bloom (threshold 1.0) picks out windows and
 * lanterns and nothing else. Without bloom ACES rolls it off to a warm near-white.
 */
export const GLOW_INTENSITY = 1.6;

const nightGlow = new WeakMap<Texture, DataTexture>();

/**
 * The emissive map that goes with a palette texture: lit windows at night, none by day.
 * The two textures share one cell map, so a mesh needs no extra UVs.
 */
export function emissiveTexture(texture: Texture): Texture | null {
  if (texture !== cache.get("night")) return null;
  let glow = nightGlow.get(texture);
  if (!glow) {
    const size = PALETTE_TEXTURE_SIZE;
    glow = new DataTexture(buildEmissiveTexture(), size, size, RGBAFormat);
    glow.magFilter = NearestFilter;
    glow.minFilter = NearestFilter;
    glow.colorSpace = SRGBColorSpace;
    glow.needsUpdate = true;
    nightGlow.set(texture, glow);
  }
  return glow;
}

/** UV at the centre of a palette cell. */
export function cellUV(name: string): [number, number] {
  const index = cellIndex[name];
  if (index === undefined) throw new Error(`Unknown palette cell: ${name}`);
  const size = PALETTE_TEXTURE_SIZE;
  return [((index % size) + 0.5) / size, (Math.floor(index / size) + 0.5) / size];
}

/** Point every UV of `geometry` at one palette cell. Returns the same geometry for chaining. */
export function paint<G extends BufferGeometry>(geometry: G, name: string): G {
  const [u, v] = cellUV(name);
  const uv = geometry.getAttribute("uv");
  for (let i = 0; i < uv.count; i += 1) uv.setXY(i, u, v);
  uv.needsUpdate = true;
  return geometry;
}

/** Non-indexed copy for merging, or the geometry itself when it already is (Three warns on a repeat). */
export function nonIndexed(geometry: BufferGeometry): BufferGeometry {
  return geometry.index ? geometry.toNonIndexed() : geometry;
}
