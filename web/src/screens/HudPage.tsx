import { useEffect, useMemo, useState } from "react";
import type { GameFixture } from "../contract/types";
import { seatNames } from "../hud/format";
import { HudView } from "../hud/HudView";
import { SAMPLE_DECISIONS } from "../hud/samples";
import { initialHudState, reduceHud } from "../hud/state";
import { AtollSilhouette } from "../world/AtollSilhouette";
import styles from "./HudPage.module.css";

const loaders = Object.fromEntries(
  Object.entries(import.meta.glob<GameFixture>("../../fixtures/*.json", { import: "default" })).filter(
    ([path]) => !path.endsWith("/index.json"),
  ),
);

/** Dev page: replay a recorded game through the HUD and open any decision kind. Not in production builds. */
export default function HudPage() {
  const files = Object.keys(loaders);
  const [file, setFile] = useState(files[0]);
  const [fixture, setFixture] = useState<GameFixture | null>(null);
  const [upTo, setUpTo] = useState(0);
  const [kind, setKind] = useState<string>("buy");
  const [night, setNight] = useState(false);
  const [lastAnswer, setLastAnswer] = useState<number | null>(null);

  useEffect(() => {
    void loaders[file]().then((f) => {
      setFixture(f);
      setUpTo(Math.floor(f.events.length / 2));
    });
  }, [file]);

  useEffect(() => {
    document.documentElement.dataset.mood = night ? "night" : "day";
  }, [night]);

  const names = useMemo(() => seatNames(fixture?.config.seats ?? ["human", "ppo"]), [fixture]);
  const hud = useMemo(
    () => (fixture ? reduceHud(fixture.events.slice(0, upTo), names) : initialHudState(names.length)),
    [fixture, upTo, names],
  );
  const decision = SAMPLE_DECISIONS.find((d) => d.kind === kind) ?? null;
  const gameOver = fixture !== null && upTo >= fixture.events.length;

  return (
    <div className={styles.page}>
      <AtollSilhouette />
      {fixture ? (
        <HudView
          hud={hud}
          names={names}
          seats={fixture.config.seats}
          decision={gameOver ? null : decision}
          gameOver={gameOver}
          onSubmit={setLastAnswer}
          onPlayAgain={() => setUpTo(0)}
          coach
        />
      ) : null}
      <form className={styles.controls} aria-label="HUD review controls" onSubmit={(e) => e.preventDefault()}>
        <label>
          Game
          <select value={file} onChange={(e) => setFile(e.target.value)}>
            {files.map((f) => (
              <option key={f} value={f}>
                {f.split("/").pop()}
              </option>
            ))}
          </select>
        </label>
        <label>
          Decision
          <select value={kind} onChange={(e) => setKind(e.target.value)}>
            {SAMPLE_DECISIONS.map((d) => (
              <option key={d.kind}>{d.kind}</option>
            ))}
          </select>
        </label>
        <label>
          Event {upTo} of {fixture?.events.length ?? 0}
          <input type="range" min={0} max={fixture?.events.length ?? 0} value={upTo} onChange={(e) => setUpTo(Number(e.target.value))} />
        </label>
        <label>
          <input type="checkbox" checked={night} onChange={(e) => setNight(e.target.checked)} /> Night
        </label>
        <output>Last action id: {lastAnswer ?? "none"}</output>
      </form>
    </div>
  );
}
