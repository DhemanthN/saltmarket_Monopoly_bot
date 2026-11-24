import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import {
  PALETTE_TEXTURE_SIZE,
  buildPaletteTexture,
  cellIndex,
  contrastRatio,
  districts,
  motion,
  ornament,
  palette,
  paletteCells,
  seats,
  spacing,
  typeScale,
  zLayers,
} from "./tokens";

const css = readFileSync(new URL("./tokens.css", import.meta.url), "utf8");
const rootBlock = css.slice(css.indexOf(":root"), css.indexOf("[data-mood"));

function cssVar(name: string): string {
  const match = new RegExp(`--${name}:\\s*([^;]+);`).exec(rootBlock);
  if (!match) throw new Error(`--${name} missing from tokens.css`);
  return match[1].trim();
}

const kebab = (s: string) => s.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`);

describe("tokens.ts matches tokens.css", () => {
  it("palette colours", () => {
    for (const [name, hex] of Object.entries(palette)) {
      expect(cssVar(kebab(name)).toUpperCase(), name).toBe(hex);
    }
  });

  it("district and seat colours", () => {
    for (const [name, hex] of Object.entries(districts)) {
      expect(cssVar(`district-${name}`).toUpperCase(), name).toBe(hex);
    }
    for (const [name, hex] of Object.entries(seats)) {
      expect(cssVar(`seat-${name}`).toUpperCase(), name).toBe(hex);
    }
  });

  it("motion durations and easings", () => {
    for (const [name, m] of Object.entries(motion)) {
      expect(cssVar(`motion-${name}`)).toBe(`${m.ms}ms`);
      expect(cssVar(`ease-${name}`)).toBe(`cubic-bezier(${m.easing.join(", ")})`);
    }
  });

  it("z-layers", () => {
    for (const [name, z] of Object.entries(zLayers)) {
      const cssName = name === "worldLabel" ? "world-label" : name === "hudRail" ? "hud-rail" : kebab(name);
      expect(Number(cssVar(`z-${cssName}`)), name).toBe(z);
    }
  });

  it("spacing and type scale", () => {
    spacing.forEach((px, i) => expect(cssVar(`space-${i + 1}`)).toBe(`${px}px`));
    for (const step of typeScale) {
      expect(cssVar(`text-${step.name}`)).toBe(`${step.size}px`);
      expect(cssVar(`leading-${step.name}`)).toBe(`${step.line}px`);
    }
  });
});

describe("lit brass ornament", () => {
  it("matches tokens.css", () => {
    expect(cssVar("brass-lit").toUpperCase()).toBe(ornament.brassLit);
  });

  it("is for ornament on dark chrome only: fine on night-panel, too faint on paper", () => {
    expect(contrastRatio(ornament.brassLit, palette.nightPanel)).toBeGreaterThanOrEqual(3);
    expect(contrastRatio(ornament.brassLit, palette.paper)).toBeLessThan(3);
  });
});

describe("contrast", () => {
  const paperText: [string, string, number][] = [
    ["ink", palette.ink, 4.5],
    ["ink-soft", palette.inkSoft, 4.5],
    ["tide", palette.tide, 4.5],
    ["danger", palette.danger, 4.5],
    ["ok", palette.ok, 4.5],
  ];

  it.each(paperText)("%s on paper meets text contrast", (_n, hex, min) => {
    expect(contrastRatio(hex, palette.paper)).toBeGreaterThanOrEqual(min);
  });

  it("matches the measured figures in DESIGN.md", () => {
    expect(contrastRatio(palette.ink, palette.paper)).toBeCloseTo(12.29, 1);
    expect(contrastRatio(palette.nightText, palette.night)).toBeCloseTo(12.59, 1);
  });

  it("focus ring and district marks meet 3.0 against paper", () => {
    expect(contrastRatio(palette.focus, palette.paper)).toBeGreaterThanOrEqual(3);
    for (const [name, hex] of Object.entries(districts)) {
      expect(contrastRatio(hex, palette.paper), name).toBeGreaterThanOrEqual(3);
    }
  });

  it("district labels in sailcloth meet 4.5", () => {
    for (const [name, hex] of Object.entries(districts)) {
      expect(contrastRatio(palette.sailcloth, hex), name).toBeGreaterThanOrEqual(4.5);
    }
  });
});

describe("palette texture", () => {
  it("is 16x16 RGBA, opaque in used cells and empty elsewhere", () => {
    const day = buildPaletteTexture("day");
    expect(day.length).toBe(PALETTE_TEXTURE_SIZE * PALETTE_TEXTURE_SIZE * 4);
    expect(day[paletteCells.length * 4 - 1]).toBe(255);
    expect(day[paletteCells.length * 4 + 3]).toBe(0);
  });

  it("day and night differ in colour but share one cell map", () => {
    const day = buildPaletteTexture("day");
    const night = buildPaletteTexture("night");
    const reef = cellIndex["district.reef"];
    expect(day.slice(reef * 4, reef * 4 + 3)).not.toEqual(night.slice(reef * 4, reef * 4 + 3));
    expect(night.slice(paletteCells.length * 4)).toEqual(day.slice(paletteCells.length * 4));
  });
});
