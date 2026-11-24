import { Html } from "@react-three/drei";
import { useFrame, useThree } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import { Vector3 } from "three";
import styles from "./Signboards.module.css";
import { Signboard } from "../ui/Signboard";
import { BRIG_SPACE, DISTRICT_HEIGHT, spaces } from "./board";
import { BRIG_ROCK, lotTransform } from "./layout";
import type { WorldState } from "./reduceEvents";
import { seatOrder, zLayers } from "../styles/tokens";

/** How many spaces ahead of the followed piece get a signboard in street view. */
const AHEAD = 3;
const AHEAD_PORTRAIT = 2;
/** Leader length in CSS pixels; alternate signs get a longer leader so neighbours never share a line. */
const LEADER = 14;
const STAGGER_PX = 30;
const Z: [number, number] = [zLayers.worldLabel, zLayers.worldLabel];

/** Price while a buyable space is unowned, then the owner's seat name, nothing otherwise. */
function signText(state: WorldState, index: number): string | undefined {
  const space = spaces[index];
  if (space.price === null) return undefined;
  if (state.owner[index] === null) return String(space.price);
  const owner = seatOrder[state.owner[index] ?? 0].label;
  return state.mortgaged[index] ? `${owner} · mortgaged` : `${owner} owns`;
}

/** A sign is shown only while its anchor sits inside this share of the frame on each side. */
const SAFE_X = 0.8;
const SAFE_Y = 0.8;

/**
 * World-anchored signboards (DESIGN.md): in street view, the spaces just ahead of the followed
 * piece show their name and price on a short leader from the lot's roof, so the board reads in
 * the world rather than in a panel. A sign whose anchor nears the frame edge fades out rather
 * than clipping. The Brig rock is always labelled.
 */
export function Signboards({ state, fromSpace, street }: { state: WorldState; fromSpace: number; street: boolean }) {
  const portrait = useThree((s) => s.size.width < s.size.height);
  const camera = useThree((s) => s.camera);
  const count = portrait ? AHEAD_PORTRAIT : AHEAD;
  const ahead = useMemo(
    () => (street ? Array.from({ length: count }, (_, k) => (fromSpace + 1 + k) % spaces.length) : []),
    [street, count, fromSpace],
  );
  const anchors = useMemo(
    () =>
      ahead.map((index) => {
        const space = spaces[index];
        const lot = lotTransform(index);
        const height = space.district ? DISTRICT_HEIGHT[space.district] : 0.6;
        return new Vector3(lot.x, height + 0.1, lot.z);
      }),
    [ahead],
  );
  const boxes = useRef<(HTMLDivElement | null)[]>([]);
  const ndc = useMemo(() => new Vector3(), []);

  useFrame(() => {
    anchors.forEach((a, k) => {
      const el = boxes.current[k];
      if (!el) return;
      ndc.copy(a).project(camera);
      const inside = ndc.z < 1 && Math.abs(ndc.x) <= SAFE_X && Math.abs(ndc.y) <= SAFE_Y;
      el.classList.toggle(styles.hidden, !inside);
    });
  });

  return (
    <group>
      {ahead.map((index, k) => {
        const space = spaces[index];
        return (
          <Html key={index} position={anchors[k]} zIndexRange={Z} pointerEvents="none">
            <div className={styles.anchor} ref={(el) => { boxes.current[k] = el; }}>
              <Signboard name={space.name} price={signText(state, index)} district={space.district ?? undefined} />
              <span className={styles.leader} style={{ height: LEADER + (k % 2) * STAGGER_PX }} />
            </div>
          </Html>
        );
      })}
      <Html position={[BRIG_ROCK.x, BRIG_ROCK.y + 0.4, BRIG_ROCK.z]} zIndexRange={Z} pointerEvents="none">
        <div className={styles.anchor}>
          <Signboard name={spaces[BRIG_SPACE].name} />
          <span className={styles.leader} style={{ height: LEADER }} />
        </div>
      </Html>
    </group>
  );
}
