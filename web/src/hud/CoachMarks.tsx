import { useState } from "react";
import { Button } from "../ui/Button";
import { Panel } from "../ui/Panel";
import styles from "./CoachMarks.module.css";

const STORAGE_KEY = "saltmarket.coach.done";

interface Mark {
  title: string;
  body: string;
}

const MARKS: readonly Mark[] = [
  { title: "Your piece and the road", body: "You are the sun piece. Your piece walks the ring road clockwise, and each lot you land on can be bought." },
  { title: "Your decisions", body: "A panel opens at the bottom whenever you must choose. Enter takes the main action, Esc takes the quiet one, and number keys pick from a list." },
  { title: "Lanterns", body: "Open a lantern, top left, to see the agent's top three choices from its last move. These are the model's numbers, not an explanation in words." },
];

function coachSeen(): boolean {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}

function markSeen(): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, "1");
  } catch {
    // Storage can be blocked. The marks then show again next game, which is harmless.
  }
}

/** Three skippable marks, shown on the first game only. */
export function CoachMarks({ onDone }: { onDone?: () => void }) {
  const [step, setStep] = useState(0);
  const [visible, setVisible] = useState(() => !coachSeen());
  if (!visible) return null;
  const mark = MARKS[step];
  const finish = () => {
    markSeen();
    setVisible(false);
    onDone?.();
  };
  return (
    <div className={styles.wrap}>
      <Panel floating role="dialog" aria-label={`Tip ${step + 1} of ${MARKS.length}`} className={styles.card}>
        <p className={styles.count}>
          Tip {step + 1} of {MARKS.length}
        </p>
        <h2 className={styles.title}>{mark.title}</h2>
        <p className={styles.body}>{mark.body}</p>
        <div className={styles.actions}>
          <Button variant="primary" autoFocus onClick={() => (step + 1 < MARKS.length ? setStep(step + 1) : finish())}>
            {step + 1 < MARKS.length ? "Next" : "Got it"}
          </Button>
          <Button variant="quiet" onClick={finish}>
            Skip tips
          </Button>
        </div>
      </Panel>
    </div>
  );
}
