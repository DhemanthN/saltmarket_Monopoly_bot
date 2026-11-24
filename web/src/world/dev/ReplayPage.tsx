import { useEffect, useMemo, useState } from "react";
import type { GameFixture } from "../../contract/types";
import { reduceCount } from "../reduceEvents";
import { WorldScene } from "../WorldScene";
import type { Tier } from "../quality";
import styles from "./ReplayPage.module.css";

// Every recorded game, bundled only into dev builds through this dev-only page.
const fixtures = import.meta.glob<GameFixture>("../../../fixtures/*_*.json", { eager: true, import: "default" });
const games = Object.values(fixtures).sort((a, b) => a.name.localeCompare(b.name));

const SPEEDS = [1, 4, 16] as const;
/** Events per second at 1x: roughly one hop-length beat per event. */
const BASE_RATE = 4;

/**
 * Dev-only `/world`: replays a recorded fixture through `reduceCount` into the scene, with
 * play, pause, speed and a scrubber over the event index.
 */
export default function ReplayPage() {
  const [gameIndex, setGameIndex] = useState(0);
  const game = games[gameIndex];
  const [cursor, setCursor] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<(typeof SPEEDS)[number]>(1);
  const [tier, setTier] = useState<Tier | null>(null);
  const total = game.events.length;
  const state = useMemo(() => reduceCount(game.events, game.config.seats.length, cursor), [game, cursor]);

  useEffect(() => {
    if (!playing) return;
    const id = window.setInterval(() => {
      setCursor((c) => {
        if (c >= total) {
          setPlaying(false);
          return c;
        }
        return c + 1;
      });
    }, 1000 / (BASE_RATE * speed));
    return () => window.clearInterval(id);
  }, [playing, speed, total]);

  const last = cursor > 0 ? game.events[cursor - 1] : null;

  return (
    <>
      <WorldScene state={state} seatKinds={game.config.seats} tierOverride={tier} />
      <div className={styles.bar} role="group" aria-label="Replay controls">
        <select
          aria-label="Recorded game"
          value={gameIndex}
          onChange={(e) => {
            setGameIndex(Number(e.target.value));
            setCursor(0);
            setPlaying(false);
          }}
        >
          {games.map((g, i) => (
            <option key={g.name} value={i}>
              {g.name} ({g.config.seats.join(", ")})
            </option>
          ))}
        </select>
        <button type="button" onClick={() => setPlaying((p) => !p)}>
          {playing ? "Pause" : "Play"}
        </button>
        <button type="button" onClick={() => setSpeed((s) => SPEEDS[(SPEEDS.indexOf(s) + 1) % SPEEDS.length])}>
          {speed}x
        </button>
        <input
          type="range"
          min={0}
          max={total}
          value={cursor}
          aria-label="Event"
          onChange={(e) => setCursor(Number(e.target.value))}
        />
        <span className={styles.readout}>
          {cursor}/{total} · turn {state.turn} · {last ? last.t : "start"}
        </span>
        <select aria-label="Quality tier" value={tier ?? "auto"} onChange={(e) => setTier(e.target.value === "auto" ? null : (e.target.value as Tier))}>
          <option value="auto">auto</option>
          <option value="high">high</option>
          <option value="medium">medium</option>
          <option value="low">low-power</option>
        </select>
      </div>
    </>
  );
}
