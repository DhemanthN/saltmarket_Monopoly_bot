import { describe, expect, it } from "vitest";
import { enterSubmits } from "../hud/layout";
import { isGameKey } from "./useModalKeys";

const key = (k: string, mods: Partial<Record<"ctrlKey" | "metaKey" | "altKey", boolean>> = {}) => ({
  key: k,
  ctrlKey: false,
  metaKey: false,
  altKey: false,
  ...mods,
});

describe("keys under an open tip or menu", () => {
  it("are kept from the decision panel and camera", () => {
    // Before the fix, Escape under tip 2 submitted Pass, and a digit could submit a list row.
    for (const k of ["Escape", "Enter", "1", "9", "ArrowLeft", "ArrowDown", "c"]) {
      expect(isGameKey(key(k)), k).toBe(true);
    }
  });

  it("leave Tab, letters and shortcuts with modifiers alone", () => {
    for (const k of ["Tab", "a", " "]) expect(isGameKey(key(k)), k).toBe(false);
    expect(isGameKey(key("1", { ctrlKey: true }))).toBe(false);
  });
});

describe("Enter on a decision", () => {
  it("never sells or mortgages blindly", () => {
    expect(enterSubmits("raise_cash")).toBe(false);
    expect(enterSubmits("liquidate")).toBe(false);
    expect(enterSubmits("buy")).toBe(true);
  });
});
