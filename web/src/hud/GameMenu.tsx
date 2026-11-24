import { useState, useSyncExternalStore } from "react";
import { Button } from "../ui/Button";
import { Dialog } from "../ui/Dialog";
import { getCalmChoice, setCalmChoice, subscribeCalm } from "../world/cameraBus";
import type { Tier } from "../world/quality";
import styles from "./GameMenu.module.css";

/** `null` lets the performance monitor pick the tier (DESIGN.md, Quality tiers). */
export type QualityChoice = Tier | null;

const QUALITY: readonly { value: QualityChoice; label: string }[] = [
  { value: null, label: "Auto" },
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
];

interface GameMenuProps {
  quality: QualityChoice;
  onQuality: (quality: QualityChoice) => void;
  reducedMotion: boolean;
  onReducedMotion: (reduced: boolean) => void;
  onLeave: () => void;
}

/**
 * The in-game menu: a corner button that opens graphics quality, reduced motion and leaving the
 * game. New settings go in this dialog as further fieldsets.
 */
export function GameMenu({ quality, onQuality, reducedMotion, onReducedMotion, onLeave }: GameMenuProps) {
  const [open, setOpen] = useState(false);
  const calm = useSyncExternalStore(subscribeCalm, getCalmChoice);
  const [confirmLeave, setConfirmLeave] = useState(false);
  const close = () => {
    setOpen(false);
    setConfirmLeave(false);
  };

  return (
    <>
      <button type="button" className={styles.trigger} aria-haspopup="dialog" onClick={() => setOpen(true)}>
        Menu
      </button>
      {open ? (
        <Dialog title="Menu" onClose={close}>
          <fieldset className={styles.field}>
            <legend className={styles.legend}>Graphics quality</legend>
            <div className={styles.options}>
              {QUALITY.map((q) => (
                <label key={q.label} className={styles.option}>
                  <input type="radio" name="quality" checked={quality === q.value} onChange={() => onQuality(q.value)} />
                  <span>{q.label}</span>
                </label>
              ))}
            </div>
            <p className={styles.hint}>Auto lowers the detail when the frame rate drops.</p>
          </fieldset>
          <label className={styles.check}>
            <input type="checkbox" checked={reducedMotion} onChange={(e) => onReducedMotion(e.target.checked)} />
            <span>Reduce motion in the world (camera cuts, pieces jump)</span>
          </label>
          <label className={styles.check}>
            <input type="checkbox" checked={calm} onChange={(e) => setCalmChoice(e.target.checked)} />
            <span>Calm (no camera sway, parallax, shake, trail or cannon effects)</span>
          </label>
          <div className={styles.actions}>
            {confirmLeave ? (
              <>
                <p className={styles.warn}>Leave this game? It cannot be resumed.</p>
                <Button variant="primary" onClick={onLeave}>
                  Leave game
                </Button>
                <Button variant="secondary" onClick={() => setConfirmLeave(false)}>
                  Keep playing
                </Button>
              </>
            ) : (
              <>
                <Button variant="primary" onClick={close}>
                  Back to the game
                </Button>
                <Button variant="secondary" onClick={() => setConfirmLeave(true)}>
                  Leave game
                </Button>
              </>
            )}
          </div>
        </Dialog>
      ) : null}
    </>
  );
}
