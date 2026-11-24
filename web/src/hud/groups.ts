import boardData from "../../../data/board.json";
import { districts, type DistrictName } from "../styles/tokens";

interface RawSpace {
  group?: string;
}

const RAW = boardData.spaces as RawSpace[];

/** Capitalises a district name for display, for example "kelp" becomes "Kelp". */
export function districtLabel(group: string): string {
  return group.charAt(0).toUpperCase() + group.slice(1);
}

/** Swatch colour for a district, or null for anything that is not one. */
export function districtColor(group: string | null | undefined): string | null {
  return group && group in districts ? districts[group as DistrictName] : null;
}

/** Groups that `seat` would own in full after receiving `incoming`, given current owners. */
export function completedGroups(incoming: readonly number[], seat: number, owner: readonly (number | null)[]): string[] {
  const touched = new Set(incoming.flatMap((i) => (RAW[i]?.group ? [RAW[i].group as string] : [])));
  return [...touched].filter((group) =>
    RAW.every((space, i) => space.group !== group || owner[i] === seat || incoming.includes(i)),
  );
}
