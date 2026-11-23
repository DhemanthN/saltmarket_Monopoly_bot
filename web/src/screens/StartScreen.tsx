import { useState } from "react";
import { seatOrder } from "../styles/tokens";
import { Button } from "../ui/Button";
import { Emblem } from "../ui/Emblem";
import { Panel } from "../ui/Panel";
import { useToast } from "../ui/Toast";
import { AtollSilhouette } from "../world/AtollSilhouette";
import styles from "./StartScreen.module.css";

type Opponent = "ppo" | "dqn" | "bot";

const OPPONENT_LABEL: Record<Opponent, string> = {
  ppo: "PPO agent",
  dqn: "DQN agent",
  bot: "Scripted bot",
};

const MAX_SEATS = 4;

export function StartScreen() {
  const toast = useToast();
  const [opponents, setOpponents] = useState<Opponent[]>(["ppo"]);

  const setOpponent = (i: number, kind: Opponent) =>
    setOpponents((prev) => prev.map((o, j) => (j === i ? kind : o)));

  return (
    <main className={styles.screen}>
      <AtollSilhouette />
      <Panel floating className={styles.panel} aria-labelledby="start-title">
        <h1 id="start-title" className={styles.title}>
          Saltmarket
        </h1>
        <p className={styles.intro}>
          Buy lots around the atoll, build depots and outlast the other traders. Take a seat against
          trained agents.
        </p>

        <div className={styles.table} role="group" aria-labelledby="seats-title">
          <p id="seats-title" className={styles.legend}>
            Seats at the table
          </p>
          <div className={styles.seat}>
            <Emblem emblem={seatOrder[0].emblem} seat={seatOrder[0].name} />
            <span className={styles.seatName}>You</span>
          </div>
          {opponents.map((kind, i) => {
            const seat = seatOrder[i + 1];
            return (
              <div className={styles.seat} key={seat.name}>
                <Emblem emblem={seat.emblem} seat={seat.name} />
                <label className={styles.seatName} htmlFor={`seat-${i + 1}`}>
                  {seat.label} seat
                </label>
                <select
                  id={`seat-${i + 1}`}
                  className={styles.select}
                  value={kind}
                  onChange={(e) => setOpponent(i, e.target.value as Opponent)}
                >
                  {(Object.keys(OPPONENT_LABEL) as Opponent[]).map((o) => (
                    <option key={o} value={o}>
                      {OPPONENT_LABEL[o]}
                    </option>
                  ))}
                </select>
                {i > 0 ? (
                  <Button variant="quiet" onClick={() => setOpponents((prev) => prev.slice(0, -1))}>
                    Remove
                  </Button>
                ) : null}
              </div>
            );
          })}
          {opponents.length + 1 < MAX_SEATS ? (
            <Button variant="quiet" className={styles.add} onClick={() => setOpponents((prev) => [...prev, "bot"])}>
              Add a seat
            </Button>
          ) : null}
        </div>

        <div className={styles.actions}>
          <Button variant="primary" onClick={() => toast("The game engine is not connected yet.")}>
            Start game
          </Button>
          <Button variant="quiet" onClick={() => toast("The rules summary arrives with the game screen.")}>
            How to play
          </Button>
        </div>
      </Panel>
    </main>
  );
}
