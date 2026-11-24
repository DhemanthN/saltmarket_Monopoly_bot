import { describe, expect, it } from "vitest";
import boardData from "../../../data/board.json";
import { completedGroups, districtColor, districtLabel } from "./groups";

const spaces = boardData.spaces as { group?: string }[];
const kelp = spaces.flatMap((s, i) => (s.group === "kelp" ? [i] : []));

describe("groups", () => {
  const none = spaces.map(() => null);

  it("reports a group completed by the incoming spaces", () => {
    const owner = spaces.map((_, i) => (kelp.slice(1).includes(i) ? 0 : null));
    expect(completedGroups([kelp[0]], 0, owner)).toEqual(["kelp"]);
  });

  it("does not report a group that stays incomplete", () => {
    expect(completedGroups([kelp[0]], 0, none)).toEqual([]);
  });

  it("labels and colours districts", () => {
    expect(districtLabel("kelp")).toBe("Kelp");
    expect(districtColor("kelp")).not.toBeNull();
    expect(districtColor("other")).toBeNull();
  });
});
