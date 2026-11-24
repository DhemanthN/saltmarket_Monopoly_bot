import { describe, expect, it } from "vitest";
import { PIXELS_PER_DEGREE, compassMarks, headingText, pointFor } from "./compass";
import { telemetryFor } from "./telemetry";

describe("compass", () => {
  it("names the nearest point and pads the reading", () => {
    expect(pointFor(0)).toBe("N");
    expect(pointFor(44)).toBe("NE");
    expect(pointFor(359)).toBe("N");
    expect(pointFor(-90)).toBe("W");
    expect(headingText(45)).toBe("045° NE");
    expect(headingText(0)).toBe("000° N");
  });

  it("centres the heading and wraps past north", () => {
    const marks = compassMarks(358, 420);
    const north = marks.find((m) => m.point === "N");
    expect(north).toBeDefined();
    expect(north!.x).toBeCloseTo(210 + 2 * PIXELS_PER_DEGREE, 5);
    expect(marks.every((m) => m.x >= -PIXELS_PER_DEGREE * 5 && m.x <= 420 + PIXELS_PER_DEGREE * 5)).toBe(true);
  });

  it("marks points, then quarter-hour numbers, then plain ticks", () => {
    const marks = compassMarks(90, 420);
    const east = marks.find((m) => m.degrees === 90)!;
    expect(east.point).toBe("E");
    expect(east.length).toBeGreaterThan(marks.find((m) => m.degrees === 105)!.length);
    expect(marks.find((m) => m.degrees === 105)!.numbered).toBe(true);
    expect(marks.find((m) => m.degrees === 100)!.numbered).toBe(false);
  });
});

describe("telemetry", () => {
  it("derives round, time of day and cash from the game state", () => {
    expect(telemetryFor(0, 4, 1500)).toEqual({ turn: 0, round: 1, timeOfDay: "Dawn", cash: 1500 });
    expect(telemetryFor(13, 4, 900)).toMatchObject({ round: 4, timeOfDay: "Dusk" });
    expect(telemetryFor(20, 2, null)).toMatchObject({ timeOfDay: "Night", cash: null });
  });
});
