import { useFrame, useThree } from "@react-three/fiber";
import { useEffect, useLayoutEffect, useMemo, useRef } from "react";
import { BackSide, Color, Group, InstancedMesh, Object3D, Vector3, type Texture } from "three";
import { piecePositions } from "./piecePositions";
import { motion, palette, seatOrder, seats } from "../styles/tokens";
import { publishLanternAnchors, type LanternAnchor } from "./anchors";
import { spaces } from "./board";
import { emblemGeometry } from "./emblems";
import { pieceGeometry } from "./geometry";
import { BRIG_ROCK, pieceSpot } from "./layout";
import type { WorldState } from "./reduceEvents";

const HOP_SECONDS = motion.standard.ms / 1000;
const HOP_HEIGHT = 0.4;
const LANTERN_HEIGHT = 1.35;
const OUTLINE = 1.08;
const AGENTS = new Set(["ppo", "dqn"]);

interface Walker {
  /** Space the piece is standing on (or hopping from). -1 means the Brig rock. */
  at: number;
  queue: number[];
  t: number;
  lastSeq: number;
}

function spotFor(target: number, seat: number, seatCount: number, out: Vector3): Vector3 {
  if (target === -1) return out.copy(BRIG_ROCK).add(new Vector3((seat - 1.5) * 0.35, 0, 0));
  return pieceSpot(target, seat, seatCount, out);
}

const isAdjacent = (a: number, b: number) => a >= 0 && (a + 1) % spaces.length === b;

interface Props {
  state: WorldState;
  /** Seat kinds, e.g. ["human", "ppo"]. Agent seats get a lantern anchor. */
  seatKinds: readonly string[];
  texture: Texture;
  reducedMotion: boolean;
  outlines: boolean;
}

/**
 * The seat pieces. A move event's path is walked one space per hop; a jump to the Brig or a
 * scrub that skips moves snaps instead. Bankrupt seats leave the board.
 */
export function Pieces({ state, seatKinds, texture, reducedMotion, outlines }: Props) {
  const count = seatKinds.length;
  const body = useRef<InstancedMesh>(null);
  const hull = useRef<InstancedMesh>(null);
  const blobs = useRef<InstancedMesh>(null);
  const flags = useRef<(Group | null)[]>([]);
  const geometry = useMemo(() => pieceGeometry(), []);
  const emblems = useMemo(() => seatOrder.map((s) => emblemGeometry(s.emblem)), []);
  const walkers = useRef<Walker[]>([]);
  const { camera, size, invalidate } = useThree();
  const dummy = useMemo(() => new Object3D(), []);

  // One walker per seat, placed where the seat stands when the table size changes.
  // Runs before the move effect below, so a first move is never mistaken for a jump.
  useLayoutEffect(() => {
    walkers.current = Array.from({ length: count }, (_, seat) => ({
      at: state.inBrig[seat] ? -1 : state.position[seat],
      queue: [],
      t: 0,
      lastSeq: state.lastMove?.seq ?? -1,
    }));
    // Only a new table size resets the walkers; later state flows through the move effect.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [count]);

  useEffect(() => {
    const color = new Color();
    for (let seat = 0; seat < count; seat += 1) body.current?.setColorAt(seat, color.set(seats[seatOrder[seat].name]));
    if (body.current?.instanceColor) body.current.instanceColor.needsUpdate = true;
  }, [count]);

  // Turn the latest move into hops, or snap when the replay jumped.
  useEffect(() => {
    const move = state.lastMove;
    walkers.current.forEach((w, seat) => {
      const target = state.inBrig[seat] ? -1 : state.position[seat];
      const fresh = move && move.seat === seat && move.seq !== w.lastSeq;
      if (move && move.seat === seat) w.lastSeq = move.seq;
      const path = fresh && !state.inBrig[seat] ? move.path : null;
      const walkable = path && !reducedMotion && isAdjacent(w.queue.length ? w.queue[w.queue.length - 1] : w.at, path[0]);
      if (walkable) {
        w.queue.push(...path);
      } else if ((w.queue.length ? w.queue[w.queue.length - 1] : w.at) !== target) {
        w.queue = [];
        w.at = target;
        w.t = 0;
      }
    });
    invalidate();
  }, [state, reducedMotion, invalidate]);

  const from = useMemo(() => new Vector3(), []);
  const to = useMemo(() => new Vector3(), []);
  const lantern = useMemo(() => new Vector3(), []);

  useFrame((_, dt) => {
    let moving = false;
    const anchors: LanternAnchor[] = [];
    walkers.current.forEach((w, seat) => {
      const p = piecePositions[seat];
      if (w.queue.length) {
        moving = true;
        w.t += dt / HOP_SECONDS;
        if (w.t >= 1) {
          w.at = w.queue.shift()!;
          w.t = w.queue.length ? w.t - 1 : 0;
        }
      }
      spotFor(w.at, seat, count, from);
      if (w.queue.length) {
        spotFor(w.queue[0], seat, count, to);
        p.lerpVectors(from, to, w.t);
        p.y += Math.sin(Math.PI * w.t) * HOP_HEIGHT;
      } else {
        p.copy(from);
      }
      const gone = state.bankrupt[seat];
      const s = gone ? 1e-4 : 1;
      dummy.position.copy(p);
      dummy.rotation.set(0, 0, 0);
      dummy.scale.setScalar(s);
      dummy.updateMatrix();
      body.current?.setMatrixAt(seat, dummy.matrix);
      dummy.scale.setScalar(s * OUTLINE);
      dummy.updateMatrix();
      hull.current?.setMatrixAt(seat, dummy.matrix);
      dummy.position.set(p.x, 0.03, p.z);
      dummy.rotation.set(-Math.PI / 2, 0, 0);
      dummy.scale.setScalar(s);
      dummy.updateMatrix();
      blobs.current?.setMatrixAt(seat, dummy.matrix);
      const flag = flags.current[seat];
      if (flag) {
        // A pennant on a short pole above the piece, turned only around the vertical axis.
        flag.position.set(p.x, p.y + 0.75, p.z);
        flag.rotation.set(0, Math.atan2(camera.position.x - p.x, camera.position.z - p.z), 0);
        flag.visible = !gone;
      }
      if (AGENTS.has(seatKinds[seat]) && !gone) {
        lantern.set(p.x, p.y + LANTERN_HEIGHT, p.z).project(camera);
        anchors.push({
          seat,
          x: ((lantern.x + 1) / 2) * size.width,
          y: ((1 - lantern.y) / 2) * size.height,
          visible: lantern.z < 1 && Math.abs(lantern.x) <= 1 && Math.abs(lantern.y) <= 1,
        });
      }
    });
    for (const mesh of [body.current, hull.current, blobs.current]) if (mesh) mesh.instanceMatrix.needsUpdate = true;
    publishLanternAnchors(anchors);
    if (moving) invalidate();
  });

  return (
    <group>
      {/* Instances move every frame, so a bounding sphere from the first frame would cull them. */}
      <instancedMesh ref={body} args={[geometry, undefined, count]} castShadow frustumCulled={false}>
        <meshLambertMaterial map={texture} />
      </instancedMesh>
      {outlines ? (
        <instancedMesh ref={hull} args={[geometry, undefined, count]} frustumCulled={false}>
          <meshBasicMaterial color={palette.ink} side={BackSide} polygonOffset polygonOffsetFactor={1} polygonOffsetUnits={1} />
        </instancedMesh>
      ) : null}
      <instancedMesh ref={blobs} args={[undefined, undefined, count]} frustumCulled={false}>
        <circleGeometry args={[0.32, 12]} />
        <meshBasicMaterial color={palette.ink} transparent opacity={0.22} depthWrite={false} />
      </instancedMesh>
      {seatOrder.slice(0, count).map((seat, i) => (
        <group key={seat.name} ref={(g) => { flags.current[i] = g; }} scale={0.15}>
          <mesh position-y={-1.2}>
            <cylinderGeometry args={[0.06, 0.06, 2.4, 5]} />
            <meshBasicMaterial color={palette.ink} />
          </mesh>
          <mesh position-x={0.65}>
            <planeGeometry args={[1.3, 1.3]} />
            <meshBasicMaterial color={seats[seat.name]} />
          </mesh>
          <mesh geometry={emblems[i]} position={[0.65, 0, 0.05]} scale={0.9}>
            <meshBasicMaterial color={seat.name === "saffron" ? palette.ink : palette.sailcloth} />
          </mesh>
        </group>
      ))}
    </group>
  );
}
