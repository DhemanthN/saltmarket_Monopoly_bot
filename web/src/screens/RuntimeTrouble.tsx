import { Button } from "../ui/Button";
import { Panel } from "../ui/Panel";
import styles from "./RuntimeTrouble.module.css";

interface RuntimeTroubleProps {
  /** The technical reason, shown small for anyone reporting the problem. */
  detail: string | null;
  /** True when a game is in progress, so Retry carries it on. */
  inGame: boolean;
  onRetry: () => void;
  onLeave: () => void;
}

/** A calm message over the world when the engine stops. Retry starts a fresh engine. */
export function RuntimeTrouble({ detail, inGame, onRetry, onLeave }: RuntimeTroubleProps) {
  return (
    <div className={styles.scrim}>
      <Panel floating className={styles.panel} role="alertdialog" aria-labelledby="trouble-title" aria-describedby="trouble-body">
        <h2 id="trouble-title" className={styles.title}>
          The harbour lost its ledger for a moment
        </h2>
        <p id="trouble-body" className={styles.body}>
          {inGame
            ? "The game engine stopped. Retry restarts it and replays your moves, so the game carries on where it was."
            : "The game engine did not finish loading. Check your connection, then retry."}
        </p>
        {detail ? (
          <details className={styles.detail}>
            <summary>Technical details</summary>
            {detail}
          </details>
        ) : null}
        <div className={styles.actions}>
          <Button variant="primary" onClick={onRetry} autoFocus>
            Retry
          </Button>
          <Button onClick={onLeave}>Back to the start</Button>
        </div>
      </Panel>
    </div>
  );
}
