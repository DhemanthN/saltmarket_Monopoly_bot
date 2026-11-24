import { useLayoutEffect, useState } from "react";
import { Button } from "../ui/Button";
import { Panel } from "../ui/Panel";
import styles from "./CoachMarks.module.css";

const STORAGE_KEY = "saltmarket.coach.done";

interface Mark {
  title: string;
  body: string;
  /** `data-coach` value of the element the tip points at. The tip is skipped when it is not on screen. */
  target: string;
  /** Which side of the target the card sits on. */
  side: "above" | "below";
}

const MARKS: readonly Mark[] = [
  {
    title: "You and the road",
    body: "You are the sun piece, and your row in the ledger carries the same emblem. Your piece walks the ring road clockwise, and each lot you land on can be bought.",
    target: "ledger-you",
    side: "below",
  },
  {
    title: "Your decisions",
    body: "A panel opens here whenever you must choose. Enter takes the main action, Esc takes the quiet one, and number keys pick from a list.",
    target: "decision",
    side: "above",
  },
  {
    title: "Lanterns",
    body: "Open a lantern to see the agent's top three choices from its last move. These are the model's numbers, not an explanation in words.",
    target: "lanterns",
    side: "below",
  },
];

const CARD_WIDTH = 300;
const GAP = 12;
const EDGE = 16;

interface Placement {
  ring: { top: number; left: number; width: number; height: number };
  card: { top?: number; bottom?: number; left: number };
}

function place(mark: Mark): Placement | null {
  const el = document.querySelector<HTMLElement>(`[data-coach="${mark.target}"]`);
  if (!el) return null;
  const r = el.getBoundingClientRect();
  const left = Math.max(EDGE, Math.min(r.left, window.innerWidth - CARD_WIDTH - EDGE));
  const below = mark.side === "below" && r.bottom + GAP + 180 < window.innerHeight;
  return {
    ring: { top: r.top - 4, left: r.left - 4, width: r.width + 8, height: r.height + 8 },
    card: below ? { top: r.bottom + GAP, left } : { bottom: window.innerHeight - r.top + GAP, left },
  };
}

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

/** Up to three skippable marks, each pointing at its target, shown on the first game only. */
export function CoachMarks({ onDone }: { onDone?: () => void }) {
  const [marks, setMarks] = useState<readonly Mark[] | null>(null);
  const [step, setStep] = useState(0);
  const [visible, setVisible] = useState(() => !coachSeen());
  const [placement, setPlacement] = useState<Placement | null>(null);

  useLayoutEffect(() => {
    // Which tips apply depends on what is on screen, so the DOM is read after the first commit.
    const findMarks = () => setMarks(MARKS.filter((m) => document.querySelector(`[data-coach="${m.target}"]`)));
    if (visible) findMarks();
  }, [visible, step]);

  const mark = marks?.[step];
  useLayoutEffect(() => {
    if (!mark) return;
    const update = () => setPlacement(place(mark));
    update();
    // The decision panel slides in, so measure again once it has settled.
    const settle = window.setTimeout(update, 300);
    window.addEventListener("resize", update);
    return () => {
      window.clearTimeout(settle);
      window.removeEventListener("resize", update);
    };
  }, [mark]);

  if (!visible || !marks || !mark || !placement) return null;
  const finish = () => {
    markSeen();
    setVisible(false);
    onDone?.();
  };
  const last = step + 1 >= marks.length;
  return (
    <div className={styles.wrap}>
      <div className={styles.ring} style={placement.ring} aria-hidden="true" />
      <Panel
        floating
        role="dialog"
        aria-label={`Tip ${step + 1} of ${marks.length}`}
        className={styles.card}
        style={{ ...placement.card, width: CARD_WIDTH }}
      >
        <p className={styles.count}>
          Tip {step + 1} of {marks.length}
        </p>
        <h2 className={styles.title}>{mark.title}</h2>
        <p className={styles.body}>{mark.body}</p>
        <div className={styles.actions}>
          <Button variant="primary" autoFocus onClick={() => (last ? finish() : setStep(step + 1))}>
            {last ? "Got it" : "Next"}
          </Button>
          <Button variant="quiet" onClick={finish}>
            Skip tips
          </Button>
        </div>
      </Panel>
    </div>
  );
}
