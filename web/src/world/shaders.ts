import { Color, DoubleSide, MeshLambertMaterial, ShaderMaterial, type Texture } from "three";
import { GLOW_INTENSITY, emissiveTexture } from "./palette";

/*
 * Small shader patches on the world's Lambert material. One shared clock uniform drives every
 * one of them, so the clock component writes a single number per frame. A frozen clock (Calm,
 * reduced motion, Low tier) leaves every surface still, never half-animated.
 */

/** Seconds of world time. `WorldClock` advances it only while motion is allowed. */
export const worldTime = { value: 0 };

/**
 * Lambert over the palette texture with a cloth sway: vertices move along local z by
 * `aSway * amp * sin(time * speed + x * 6 + phase)`, where the phase comes from the instance's
 * position, so neighbouring flags never flap in step. Geometry without `aSway` stays rigid.
 */
export function swayMaterial(texture: Texture, amp: number, speed = 3): MeshLambertMaterial {
  const glow = emissiveTexture(texture);
  const material = new MeshLambertMaterial({ map: texture, emissive: glow ? "#ffffff" : "#000000", emissiveMap: glow, emissiveIntensity: glow ? GLOW_INTENSITY : 1, side: DoubleSide });
  material.onBeforeCompile = (shader) => {
    shader.uniforms.uTime = worldTime;
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", "#include <common>\nuniform float uTime;\nattribute float aSway;")
      .replace(
        "#include <begin_vertex>",
        `#include <begin_vertex>
        float phase = 0.0;
        #ifdef USE_INSTANCING
          phase = instanceMatrix[3].x * 1.7 + instanceMatrix[3].z * 1.3;
        #endif
        transformed.z += aSway * ${amp.toFixed(3)} * sin(uTime * ${speed.toFixed(2)} + transformed.x * 6.0 + phase);`,
      );
  };
  material.customProgramCacheKey = () => `sway-${amp}-${speed}-${glow ? 1 : 0}`;
  return material;
}

/**
 * Sea and lagoon: Lambert plus slow drifting light bands, brighter where long and short waves
 * line up. No reflections, no extra textures. A frozen clock keeps the bands still.
 */
export function waterMaterial(texture: Texture): MeshLambertMaterial {
  const material = new MeshLambertMaterial({ map: texture });
  material.onBeforeCompile = (shader) => {
    shader.uniforms.uTime = worldTime;
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", "#include <common>\nvarying vec2 vWorldXZ;")
      .replace("#include <worldpos_vertex>", "#include <worldpos_vertex>\nvWorldXZ = (modelMatrix * vec4(transformed, 1.0)).xz;");
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", "#include <common>\nuniform float uTime;\nvarying vec2 vWorldXZ;")
      .replace(
        "#include <map_fragment>",
        `#include <map_fragment>
        float r = length(vWorldXZ);
        float a = atan(vWorldXZ.y, vWorldXZ.x);
        float swell = sin(r * 1.6 - uTime * 0.7 + sin(a * 5.0 + uTime * 0.2) * 0.8);
        float chop = sin(vWorldXZ.x * 3.1 + uTime * 1.1) * sin(vWorldXZ.y * 2.7 - uTime * 0.9);
        float band = smoothstep(0.82, 1.0, swell * 0.7 + chop * 0.3);
        diffuseColor.rgb = mix(diffuseColor.rgb, diffuseColor.rgb * 1.22 + 0.04, band * 0.55);`,
      );
  };
  material.customProgramCacheKey = () => "water";
  return material;
}

/**
 * Foam at the sand's edges: bands that roll toward each shore radius in `radii` and fade out
 * within `width`. Transparent, unlit, no depth write, so it sits on the water as a wash.
 */
export function foamMaterial(radii: readonly number[], width: number, color: string): ShaderMaterial {
  return new ShaderMaterial({
    transparent: true,
    depthWrite: false,
    uniforms: { uTime: worldTime, uColor: { value: new Color(color) } },
    vertexShader: `varying vec2 vXZ;
      void main() {
        vec4 w = modelMatrix * vec4(position, 1.0);
        vXZ = w.xz;
        gl_Position = projectionMatrix * viewMatrix * w;
      }`,
    fragmentShader: `uniform float uTime; uniform vec3 uColor; varying vec2 vXZ;
      void main() {
        float r = length(vXZ);
        float d = min(abs(r - ${radii[0].toFixed(3)}), abs(r - ${radii[radii.length - 1].toFixed(3)}));
        float edge = 1.0 - smoothstep(0.0, ${width.toFixed(3)}, d);
        float a = atan(vXZ.y, vXZ.x);
        float roll = 0.5 + 0.5 * sin(d * 14.0 - uTime * 1.6 + sin(a * 9.0) * 1.5);
        float alpha = edge * (0.35 + 0.45 * roll) * edge;
        if (alpha < 0.02) discard;
        gl_FragColor = vec4(uColor, alpha * 0.8);
      }`,
  });
}
