import { BufferGeometry, DataTexture, NearestFilter, RGBAFormat, SRGBColorSpace } from "three";
import { PALETTE_TEXTURE_SIZE, buildPaletteTexture, cellIndex, type Mood } from "../styles/tokens";

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
