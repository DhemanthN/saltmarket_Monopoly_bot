import { Html } from "@react-three/drei";
import { Signboard } from "../ui/Signboard";
import { BRIG_SPACE, DISTRICT_HEIGHT, spaces } from "./board";
import { BRIG_ROCK, lotTransform } from "./layout";
import type { WorldState } from "./reduceEvents";
import { zLayers } from "../styles/tokens";

/** How many spaces ahead of the followed piece get a signboard in street view. */
const AHEAD = 6;
const Z: [number, number] = [zLayers.worldLabel, zLayers.worldLabel];

/** Price while a buyable space is unowned, "Mortgaged" or "Owned" after, nothing otherwise. */
function signText(state: WorldState, index: number): string | undefined {
  const space = spaces[index];
  if (space.price === null) return undefined;
  if (state.owner[index] === null) return String(space.price);
  return state.mortgaged[index] ? "Mortgaged" : "Owned";
}

/**
 * World-anchored signboards (DESIGN.md): in street view, the spaces just ahead of the followed
 * piece show their name and price, so the board reads in the world rather than in a panel.
 * The Brig rock is always labelled.
 */
export function Signboards({ state, fromSpace, street }: { state: WorldState; fromSpace: number; street: boolean }) {
  const ahead = street ? Array.from({ length: AHEAD }, (_, k) => (fromSpace + 1 + k) % spaces.length) : [];
  return (
    <group>
      {ahead.map((index) => {
        const space = spaces[index];
        const lot = lotTransform(index);
        const height = space.district ? DISTRICT_HEIGHT[space.district] : 0.6;
        return (
          <Html key={index} position={[lot.x, height + 0.45, lot.z]} center zIndexRange={Z} pointerEvents="none">
            <Signboard name={space.name} price={signText(state, index)} district={space.district ?? undefined} />
          </Html>
        );
      })}
      <Html position={[BRIG_ROCK.x, BRIG_ROCK.y + 0.9, BRIG_ROCK.z]} center zIndexRange={Z} pointerEvents="none">
        <Signboard name={spaces[BRIG_SPACE].name} />
      </Html>
    </group>
  );
}
