import { useLayoutEffect, useState } from "react";
import { Button } from "../ui/Button";
import { Panel } from "../ui/Panel";
import { useModalKeys } from "../ui/useModalKeys";
import styles from "./CoachMarks.module.css";

const STORAGE_KEY = "saltmarket.coach.done";

interface Mark {
  title: string;
  body: string;
  /** `data-coach` value of the element the tip points at. The tip is skipped when it is not on screen. */
  target: string;
  /** Which side of the target the card sits on. */
  side: "above" | "below";
  /**
   * `data-coach` value of a panel the card must not cover (tip 1 must leave the whole ledger
   * readable). On wide screens the card sits to its left; otherwise just below it.
   */
  clear?: string;
}

const MARKS: readonly Mark[] = [
  {
    title: "You and the road",
    body: "You are the sun piece, and your row in the ledger carries the same emblem. Your piece walks the ring road clockwise, and each lot you land on can be bought.",
    target: "ledger-you",
    side: "below",
    clear: "ledger",
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
/** Matches the HUD's mobile layout (ledger strip and bottom sheet). */
const NARROW = 600;

interface Placement {
  ring: { top: number; left: number; width: number; height: number };
  card: { top?: number; bottom?: number; left: number; width: number };
}

function place(mark: Mark): Placement | null {
  const el = document.querySelector<HTMLElement>(`[data-coach="${mark.target}"]`);
  if (!el) return null;
  const r = el.getBoundingClientRect();
  const width = Math.min(CARD_WIDTH, window.innerWidth - 2 * EDGE);
  const ring = { top: r.top - 4, left: r.left - 4, width: r.width + 8, height: r.height + 8 };
  const clear = mark.clear ? document.querySelector<HTMLElement>(`[data-coach="${mark.clear}"]`) : null;
  if (clear) {
    const c = clear.getBoundingClientRect();
    const beside = window.innerWidth > NARROW && c.left - GAP - width >= EDGE;
    const card = beside
      ? { top: c.top, left: c.left - GAP - width, width }
      : { top: c.bottom + GAP, left: Math.max(EDGE, Math.min(c.left, window.innerWidth - width - EDGE)), width };
    return { ring, card };
  }
  const left = Math.max(EDGE, Math.min(r.left, window.innerWidth - width - EDGE));
  const below = mark.side === "below" && r.bottom + GAP + 180 < window.innerHeight;
  return {
    ring,
    card: below ? { top: r.bottom + GAP, left, width } : { bottom: window.innerHeight - r.top + GAP, left, width },
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

interface CoachMarksProps {
  /**
   * Current tip. The parent owns it because the marks unmount between decisions, and the tour
   * must carry on where it stopped rather than start again at tip 1.
   */
  step: number;
  onStep: (step: number) => void;
  onDone?: () => void;
}

/**
 * Up to three skippable marks, each pointing at its target, shown on the first game only.
 * While a tip is open, game keys do not reach the decision panel under it; Escape skips the tips.
 */
export function CoachMarks({ step, onStep, onDone }: CoachMarksProps) {
  const [marks, setMarks] = useState<readonly Mark[] | null>(null);
  const [visible, setVisible] = useState(() => !coachSeen());
  const [placement, setPlacement] = useState<Placement | null>(null);

  useLayoutEffect(() => {
    // Which tips apply depends on what is on screen, so the DOM is read after the first commit.
    const findMarks = () => setMarks(MARKS.filter((m) => document.querySelector(`[data-coach="${m.target}"]`)));
    if (visible) findMarks();
  }, [visible, step]);

  const mark = marks?.[step];
  const finish = () => {
    markSeen();
    setVisible(false);
    onDone?.();
  };
  useModalKeys(visible && mark !== undefined, finish);
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
  const last = step + 1 >= marks.length;
  return (
    <div className={styles.wrap}>
      <div className={styles.ring} style={placement.ring} aria-hidden="true" />
      <Panel
        floating
        role="dialog"
        aria-label={`Tip ${step + 1} of ${marks.length}`}
        className={styles.card}
        style={placement.card}
      >
        <p className={styles.count}>
          Tip {step + 1} of {marks.length}
        </p>
        <h2 className={styles.title}>{mark.title}</h2>
        <p className={styles.body}>{mark.body}</p>
        <div className={styles.actions}>
          <Button variant="primary" autoFocus onClick={() => (last ? finish() : onStep(step + 1))}>
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
