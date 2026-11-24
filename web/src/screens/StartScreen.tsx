import { lazy, Suspense, useState } from "react";
import { Dialog } from "../ui/Dialog";
import type { SessionConfig } from "../contract/types";
import { seatOrder } from "../styles/tokens";
import { Button } from "../ui/Button";
import { Emblem } from "../ui/Emblem";
import { Panel } from "../ui/Panel";
import { HOW_TO_PLAY } from "./rules";
import { buildModeConfig, MODE_LABEL, MODES, modeAllowed, modeSize, TABLE_SIZES, type Mode, type TableSize } from "./startConfig";
import styles from "./StartScreen.module.css";

// The ship loads on its own after the first paint, so the start screen stays light.
const StartShip = lazy(() => import("./ship/StartShip"));

const SEAT_KIND: Record<string, string> = {
  ppo: "PPO agent",
  dqn: "DQN agent",
  expert: "Expert bot",
  balanced: "Balanced bot",
  always_buy: "Always-buy bot",
};

interface StartScreenProps {
  /** Called with the chosen table. */
  onStart: (config: SessionConfig) => void;
  /** Engine load progress, drawn as the atoll rising behind the panel. */
  progress?: number;
  caption?: string;
}

export function StartScreen({ onStart, progress, caption }: StartScreenProps) {
  const [rulesOpen, setRulesOpen] = useState(false);
  const [mode, setMode] = useState<Mode>("ppo");
  const [size, setSize] = useState<TableSize>(2);

  const [notice, setNotice] = useState<string | null>(null);

  const pickSize = (next: TableSize) => {
    setSize(next);
    const fixedSize = mode === "quick" || mode === "table4" || mode === "watch";
    if (!modeAllowed(mode, next)) {
      setMode("ppo");
      setNotice("The DQN agent plays 2-player tables only, so the opponent is now the PPO agent.");
    } else {
      if (fixedSize) setMode("ppo");
      setNotice(null);
    }
  };

  const pickMode = (next: Mode) => {
    setMode(next);
    setSize(modeSize(next, size));
    setNotice(null);
  };

  const config = buildModeConfig(mode, size, 0);
  const start = () => {
    onStart(buildModeConfig(mode, size, Math.floor(Math.random() * 1_000_000)));
  };

  return (
    <main className={styles.screen}>
      <div className={styles.sea} aria-hidden="true">
        <div className={styles.sun} />
        <div className={styles.ship}>
          <Suspense fallback={null}>
            <StartShip />
          </Suspense>
        </div>
      </div>
      <Panel floating className={styles.panel} aria-labelledby="start-title">
        <h1 id="start-title" className={styles.title}>
          Saltmarket
        </h1>
        <p className={styles.intro}>
          Buy lots around the atoll, build depots and outlast the other traders. Take a seat against
          trained agents.
        </p>

        <fieldset className={styles.field}>
          <legend className={styles.legend}>How to play</legend>
          <div className={styles.modes}>
            {MODES.map((m) => {
              const allowed = modeAllowed(m, size);
              return (
                <label key={m} className={styles.mode} data-disabled={allowed ? undefined : "true"}>
                  <input
                    type="radio"
                    name="mode"
                    value={m}
                    checked={mode === m}
                    disabled={!allowed}
                    onChange={() => pickMode(m)}
                  />
                  <span className={styles.modeBody}>
                    <span className={styles.modeTitle}>{MODE_LABEL[m].title}</span>
                    <span className={styles.modeNote}>
                      {allowed ? MODE_LABEL[m].note : "Needs a 2-player table. Pick 2 players to use it."}
                    </span>
                  </span>
                </label>
              );
            })}
          </div>
        </fieldset>

        {notice ? (
          <p className={styles.notice} role="status">
            {notice}
          </p>
        ) : null}

        <fieldset className={styles.field}>
          <legend className={styles.legend}>Table size</legend>
          <div className={styles.sizes}>
            {TABLE_SIZES.map((n) => (
              <label key={n} className={styles.size}>
                <input
                  type="radio"
                  name="table-size"
                  value={n}
                  checked={size === n}
                  onChange={() => pickSize(n)}
                />
                <span>{n} players</span>
              </label>
            ))}
          </div>
        </fieldset>

        <div className={styles.table} role="group" aria-label="Seats at the table">
          {config.seats.map((kind, i) => (
            <div className={styles.seat} key={seatOrder[i].name}>
              <Emblem emblem={seatOrder[i].emblem} seat={seatOrder[i].name} />
              <span className={styles.seatName}>
                {kind === "human" ? "You" : `${seatOrder[i].label} seat`}
              </span>
              <span className={styles.seatKind}>
                {kind === "human" ? "" : (SEAT_KIND[kind] ?? kind.replace(/_/g, " "))}
              </span>
            </div>
          ))}
        </div>

        <div className={styles.actions}>
          <Button variant="primary" onClick={start}>
            Start game
          </Button>
          <Button variant="quiet" aria-haspopup="dialog" onClick={() => setRulesOpen(true)}>
            How to play
          </Button>
        </div>
        {progress !== undefined && progress < 1 ? (
          <p className={styles.load} role="status">
            {caption ?? "Loading the engine"} {Math.round(progress * 100)}%
          </p>
        ) : null}
      </Panel>
      {rulesOpen ? (
        <Dialog title="How to play" wide onClose={() => setRulesOpen(false)}>
          {HOW_TO_PLAY.map((topic) => (
            <section key={topic.title} className={styles.rule}>
              <h3 className={styles.ruleTitle}>{topic.title}</h3>
              <p className={styles.ruleBody}>{topic.body}</p>
            </section>
          ))}
          <Button variant="primary" onClick={() => setRulesOpen(false)}>
            Back
          </Button>
        </Dialog>
      ) : null}
    </main>
  );
}
