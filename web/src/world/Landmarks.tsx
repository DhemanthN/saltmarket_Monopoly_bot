import { useLayoutEffect, useMemo, useRef } from "react";
import { BackSide, Color, InstancedMesh, Object3D, type Texture } from "three";
import { useDispose } from "./dispose";
import { merge } from "./geometry";
import { flagGeometry, landmarkGeometry, pushedHull } from "./landmarkKit";
import { LitMaterial } from "./LitMaterial";
import { silhouetteParts } from "./silhouettes";
import { swayMaterial } from "./shaders";
import { palette, districts } from "../styles/tokens";

/** Flag colours cycle through these, so a row of poles reads as bunting, not one repeated cloth. */
const FLAG_TINTS = [palette.danger, districts.crown, palette.tide, districts.amber, palette.sailcloth];

/**
 * Signature props for all 40 spaces, the shore watchtowers, quay cranes and rope bridges:
 * one merged mesh and one ink hull. Their flags are one instanced, waving mesh.
 */
export function Landmarks({ texture, shadows, outline }: { texture: Texture; shadows: boolean; outline: boolean }) {
  const built = useMemo(() => {
    const props = landmarkGeometry();
    const sil = silhouetteParts();
    const body = merge([props.geometry, ...sil.parts]);
    return { body, hull: pushedHull(body), flags: [...props.flags, ...sil.flags], flag: flagGeometry() };
  }, []);
  const flagMaterial = useMemo(() => swayMaterial(texture, 0.05), [texture]);
  useDispose(built.body, built.hull, built.flag, flagMaterial);
  const flags = useRef<InstancedMesh>(null);

  useLayoutEffect(() => {
    const mesh = flags.current;
    if (!mesh) return;
    const o = new Object3D();
    const c = new Color();
    built.flags.forEach((f, i) => {
      o.position.copy(f.at);
      o.rotation.set(0, f.rotY + Math.PI / 2, 0);
      o.updateMatrix();
      mesh.setMatrixAt(i, o.matrix);
      mesh.setColorAt(i, c.set(FLAG_TINTS[i % FLAG_TINTS.length]));
    });
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  }, [built, flagMaterial]);

  return (
    <group>
      <mesh geometry={built.body} castShadow={shadows} receiveShadow={shadows}>
        <LitMaterial texture={texture} />
      </mesh>
      {outline ? (
        <mesh geometry={built.hull}>
          <meshBasicMaterial color={palette.ink} side={BackSide} polygonOffset polygonOffsetFactor={1} polygonOffsetUnits={1} />
        </mesh>
      ) : null}
      <instancedMesh ref={flags} args={[built.flag, flagMaterial, built.flags.length]} frustumCulled={false} />
    </group>
  );
}
