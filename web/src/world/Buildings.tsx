import { useFrame, useThree } from "@react-three/fiber";
import { useLayoutEffect, useMemo, useRef } from "react";
import { BackSide, Color, InstancedMesh, Object3D, type BufferGeometry, type Texture } from "three";
import { districts, palette, seatOrder, seats, type DistrictName } from "../styles/tokens";
import { spaces } from "./board";
import {
  STOREY_ANCHOR,
  STOREY_HEIGHT,
  awningGeometry,
  buildDistrictGeometry,
  markerGeometry,
  portGeometry,
  shutterGeometry,
} from "./geometry";
import { lotTransform } from "./layout";
import type { WorldState } from "./reduceEvents";

/** Depot levels before a port. Level 5 (`PORT_LEVEL`) adds the crane and quay instead of a storey. */
const MAX_STOREYS = 4;
const PORT_LEVEL = 5;
const OUTLINE = 1.035;
/** Storeys per second while rising or shrinking (one storey per `travel`, 480 ms). */
const RISE_RATE = 1 / 0.48;

const districtNames = Object.keys(districts) as DistrictName[];
const LOTS = Object.fromEntries(
  districtNames.map((d) => [d, spaces.filter((s) => s.district === d).map((s) => s.index)]),
) as Record<DistrictName, number[]>;
const markerLots = spaces.filter((s) => s.district === null).map((s) => s.index);
const propertyLots = spaces.filter((s) => s.district !== null).map((s) => s.index);
/** Shutter height in lot space. Kelp shacks stand on stilts, so their facade starts above the deck. */
const SHUTTER_Y: Partial<Record<DistrictName, number>> = { kelp: 0.4 };
const shutterY = (lot: number) => SHUTTER_Y[spaces[lot].district ?? "reef"] ?? 0.12;

interface Props {
  state: WorldState;
  texture: Texture;
  reducedMotion: boolean;
  shadows: boolean;
  fullOutlines: boolean;
}

const dummy = new Object3D();

function placeLot(index: number, offset: [number, number, number] = [0, 0, 0], scale: [number, number, number] = [1, 1, 1]) {
  const { x, z, rotY } = lotTransform(index);
  dummy.position.set(x, 0, z);
  dummy.rotation.set(0, rotY, 0);
  dummy.scale.set(1, 1, 1);
  dummy.updateMatrix();
  dummy.translateX(offset[0]);
  dummy.translateY(offset[1]);
  dummy.translateZ(offset[2]);
  dummy.scale.set(...scale);
  dummy.updateMatrix();
  return dummy.matrix;
}

/** A static instanced mesh with an ink hull: two draw calls for every lot of one type. */
function Static({ geometry, lots, texture, shadows, outline }: { geometry: BufferGeometry; lots: number[]; texture: Texture; shadows: boolean; outline: boolean }) {
  const body = useRef<InstancedMesh>(null);
  const hull = useRef<InstancedMesh>(null);
  useLayoutEffect(() => {
    lots.forEach((lot, i) => {
      body.current?.setMatrixAt(i, placeLot(lot));
      hull.current?.setMatrixAt(i, placeLot(lot, [0, 0, 0], [OUTLINE, OUTLINE, OUTLINE]));
    });
    if (body.current) body.current.instanceMatrix.needsUpdate = true;
    if (hull.current) hull.current.instanceMatrix.needsUpdate = true;
  }, [lots, outline]);
  return (
    <>
      <instancedMesh ref={body} args={[geometry, undefined, lots.length]} castShadow={shadows} receiveShadow={shadows}>
        <meshLambertMaterial map={texture} />
      </instancedMesh>
      {outline ? (
        <instancedMesh ref={hull} args={[geometry, undefined, lots.length]}>
          <meshBasicMaterial color={palette.ink} side={BackSide} polygonOffset polygonOffsetFactor={1} polygonOffsetUnits={1} />
        </instancedMesh>
      ) : null}
    </>
  );
}

/**
 * The storey stacks for one district. Each lot shows `level` storeys (up to 4); the displayed
 * height eases toward the target one storey per `travel`, so builds rise and sells shrink.
 */
function Storeys({ district, geometry, state, texture, reducedMotion, shadows }: { district: DistrictName; geometry: BufferGeometry; state: WorldState; texture: Texture; reducedMotion: boolean; shadows: boolean }) {
  const lots = LOTS[district];
  const body = useRef<InstancedMesh>(null);
  const hull = useRef<InstancedMesh>(null);
  const shown = useRef<number[]>(lots.map((l) => Math.min(state.level[l], MAX_STOREYS)));
  const invalidate = useThree((s) => s.invalidate);

  const write = () => {
    lots.forEach((lot, li) => {
      for (let k = 0; k < MAX_STOREYS; k += 1) {
        const fill = Math.max(0, Math.min(1, shown.current[li] - k));
        const at: [number, number, number] = [STOREY_ANCHOR[0], STOREY_ANCHOR[1] + k * STOREY_HEIGHT, STOREY_ANCHOR[2]];
        const i = li * MAX_STOREYS + k;
        // An empty slot collapses on every axis; flattening only y left a coloured plate behind.
        const w = fill > 0 ? 1 : 0;
        body.current?.setMatrixAt(i, placeLot(lot, at, [w, fill, w]));
        hull.current?.setMatrixAt(i, placeLot(lot, at, [w * OUTLINE, fill * OUTLINE, w * OUTLINE]));
      }
    });
    if (body.current) body.current.instanceMatrix.needsUpdate = true;
    if (hull.current) hull.current.instanceMatrix.needsUpdate = true;
  };

  useLayoutEffect(() => {
    if (reducedMotion) shown.current = lots.map((l) => Math.min(state.level[l], MAX_STOREYS));
    write();
    invalidate();
  });

  useFrame((_, dt) => {
    let moving = false;
    lots.forEach((lot, li) => {
      const target = Math.min(state.level[lot], MAX_STOREYS);
      const d = target - shown.current[li];
      if (Math.abs(d) < 1e-3) return;
      moving = true;
      shown.current[li] += Math.sign(d) * Math.min(Math.abs(d), RISE_RATE * dt);
    });
    if (moving) {
      write();
      invalidate();
    }
  });

  const count = lots.length * MAX_STOREYS;
  return (
    <>
      <instancedMesh ref={body} args={[geometry, undefined, count]} castShadow={shadows} receiveShadow={shadows}>
        <meshLambertMaterial map={texture} />
      </instancedMesh>
      <instancedMesh ref={hull} args={[geometry, undefined, count]}>
        <meshBasicMaterial color={palette.ink} side={BackSide} polygonOffset polygonOffsetFactor={1} polygonOffsetUnits={1} />
      </instancedMesh>
    </>
  );
}

/** Awnings in owner colour, closed shutters on mortgaged lots, and port cranes. Hidden lots scale to zero. */
function LotMarks({ state, texture }: { state: WorldState; texture: Texture }) {
  const geo = useMemo(() => ({ awning: awningGeometry(), shutter: shutterGeometry(), port: portGeometry() }), []);
  const awning = useRef<InstancedMesh>(null);
  const shutter = useRef<InstancedMesh>(null);
  const port = useRef<InstancedMesh>(null);
  const invalidate = useThree((s) => s.invalidate);

  useLayoutEffect(() => {
    const color = new Color();
    const hidden: [number, number, number] = [1e-4, 1e-4, 1e-4];
    propertyLots.forEach((lot, i) => {
      const owner = state.owner[lot];
      const mortgaged = state.mortgaged[lot];
      awning.current?.setMatrixAt(i, placeLot(lot, [0, 0.36, 0.48], owner === null ? hidden : [1, 1, 1]));
      awning.current?.setColorAt(i, color.set(owner === null ? palette.paperDeep : mortgaged ? palette.paperDeep : seats[seatOrder[owner].name]));
      shutter.current?.setMatrixAt(i, placeLot(lot, [0, shutterY(lot), 0.5], mortgaged ? [1, 1, 1] : hidden));
      port.current?.setMatrixAt(i, placeLot(lot, [0, 0, 0], state.level[lot] >= PORT_LEVEL ? [1, 1, 1] : hidden));
    });
    for (const mesh of [awning.current, shutter.current, port.current]) {
      if (!mesh) continue;
      mesh.instanceMatrix.needsUpdate = true;
      if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
    }
    invalidate();
  }, [state.owner, state.mortgaged, state.level, invalidate]);

  const n = propertyLots.length;
  return (
    <>
      <instancedMesh ref={awning} args={[geo.awning, undefined, n]}>
        <meshLambertMaterial map={texture} />
      </instancedMesh>
      <instancedMesh ref={shutter} args={[geo.shutter, undefined, n]}>
        <meshLambertMaterial map={texture} />
      </instancedMesh>
      <instancedMesh ref={port} args={[geo.port, undefined, n]}>
        <meshLambertMaterial map={texture} />
      </instancedMesh>
    </>
  );
}

/** Every building on the atoll: district silhouettes, storeys, owner marks and space markers. */
export function Buildings({ state, texture, reducedMotion, shadows, fullOutlines }: Props) {
  const geometry = useMemo(() => Object.fromEntries(districtNames.map((d) => [d, buildDistrictGeometry(d)])) as Record<DistrictName, ReturnType<typeof buildDistrictGeometry>>, []);
  const marker = useMemo(() => markerGeometry(), []);
  return (
    <group>
      {districtNames.map((d) => (
        <group key={d}>
          <Static geometry={geometry[d].base} lots={LOTS[d]} texture={texture} shadows={shadows} outline />
          <Storeys district={d} geometry={geometry[d].storey} state={state} texture={texture} reducedMotion={reducedMotion} shadows={shadows} />
        </group>
      ))}
      <Static geometry={marker} lots={markerLots} texture={texture} shadows={shadows} outline={fullOutlines} />
      <LotMarks state={state} texture={texture} />
    </group>
  );
}
