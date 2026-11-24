import type { Texture } from "three";
import { emissiveTexture } from "./palette";

/** The world's one material: Lambert shading over the palette texture, with lit windows at night. */
export function LitMaterial({ texture, color }: { texture: Texture; color?: string }) {
  const glow = emissiveTexture(texture);
  return <meshLambertMaterial key={glow ? "night" : "day"} map={texture} color={color} emissive={glow ? "#ffffff" : "#000000"} emissiveMap={glow} />;
}
