import { Html } from "@react-three/drei";
import { useFrame, useThree } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import { Vector3 } from "three";
import styles from "./Signboards.module.css";
import { Signboard } from "../ui/Signboard";
import { BRIG_SPACE, DISTRICT_HEIGHT, spaces } from "./board";
import { BRIG_ROCK, lotTransform } from "./layout";
import type { WorldState } from "./reduceEvents";
import { seatNames, shortName } from "../hud/format";
import { zLayers } from "../styles/tokens";

/** How many spaces ahead of the followed piece get a signboard in street view. */
const AHEAD = 3;
const AHEAD_PORTRAIT = 2;
/** Leader length in CSS pixels; alternate signs get a longer leader so neighbours never share a line. */
const LEADER = 14;
const STAGGER_PX = 38;
/** Matches the desktop ledger rail in hud/LedgerRail.module.css: 340 px wide plus a 16 px margin, above 600 px of width. */
const RAIL_PX = 356;
const RAIL_MIN_WIDTH = 600;
/** Gap kept between two signs that would otherwise touch. */
const GAP_PX = 6;
const Z: [number, number] = [zLayers.worldLabel, zLayers.worldLabel];

/** Price while a buyable space is unowned, then the owner as the ledger names them, nothing otherwise. */
function signText(state: WorldState, index: number, names: readonly string[]): string | undefined {
  const space = spaces[index];
  if (space.price === null) return undefined;
  const seat = state.owner[index];
  if (seat === null) return String(space.price);
  const name = shortName(names[seat] ?? "");
  const you = name === "You";
  if (state.mortgaged[index]) return `${you ? "Yours" : name} · mortgaged`;
  return you ? "Yours" : `${name} owns`;
}

/** A sign is shown only while its anchor sits inside this share of the frame height, and inside the open width. */
const SAFE_Y = 0.8;
/** Smallest gap between a signboard and the side of the screen. */
const EDGE_PX = 8;

/**
 * World-anchored signboards (DESIGN.md): in street view, the spaces just ahead of the followed
 * piece show their name and price on a short leader from the lot's roof, so the board reads in
 * the world rather than in a panel. A sign whose anchor nears the frame edge fades out rather
 * than clipping. The Brig rock is always labelled.
 */
export function Signboards({ state, fromSpace, street, seatKinds }: { state: WorldState; fromSpace: number; street: boolean; seatKinds: readonly string[] }) {
  const names = useMemo(() => seatNames(seatKinds), [seatKinds]);
  const portrait = useThree((s) => s.size.width < s.size.height);
  const camera = useThree((s) => s.camera);
  const width = useThree((s) => s.size.width);
  const height = useThree((s) => s.size.height);
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
  // Screen rectangle of each shown sign this frame, reused so the loop allocates nothing.
  const rects = useMemo(() => Array.from({ length: AHEAD + 1 }, () => ({ left: 0, right: 0, top: 0, bottom: 0, shown: false })), []);

  useFrame(() => {
    const right = width > RAIL_MIN_WIDTH ? width - RAIL_PX : width - EDGE_PX;
    anchors.forEach((a, k) => {
      const el = boxes.current[k];
      const rect = rects[k];
      if (!el) return;
      ndc.copy(a).project(camera);
      const x = ((ndc.x + 1) / 2) * width;
      const y = ((1 - ndc.y) / 2) * height;
      let inside = ndc.z < 1 && x >= EDGE_PX && x <= right && Math.abs(ndc.y) <= SAFE_Y;
      const board = el.firstElementChild as HTMLElement | null;
      if (inside && board) {
        // Slide the board (not its leader) back inside the open frame when it would cross an edge.
        const half = board.offsetWidth / 2;
        const shift = Math.min(0, right - (x + half)) + Math.max(0, EDGE_PX - (x - half));
        board.style.translate = shift ? `${Math.round(shift)}px 0` : "";
        rect.left = x + shift - half;
        rect.right = x + shift + half;
        rect.bottom = y - LEADER - (k % 2) * STAGGER_PX;
        rect.top = rect.bottom - board.offsetHeight;
        // A sign yields to any nearer one it would overlap, so two names never share space.
        for (let j = 0; j < k && inside; j += 1) {
          const o = rects[j];
          if (o.shown && rect.left < o.right + GAP_PX && rect.right > o.left - GAP_PX && rect.top < o.bottom + GAP_PX && rect.bottom > o.top - GAP_PX) inside = false;
        }
      }
      rect.shown = inside;
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
              <Signboard name={space.name} price={signText(state, index, names)} district={space.district ?? undefined} />
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
