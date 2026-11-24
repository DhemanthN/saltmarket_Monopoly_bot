import { useState } from "react";
import type { Explanation } from "../contract/types";
import { seatOrder } from "../styles/tokens";
import { Emblem } from "../ui/Emblem";
import { lanternBars } from "./lanternBars";
import styles from "./Lantern.module.css";

export interface LanternDockProps {
  /** Seats that are agents, with their latest explanation. */
  lanterns: { seat: number; name: string; explanation: Explanation | null }[];
}

/** One lantern per agent opponent. Hover, focus or tap opens its top three choices. */
export function LanternDock({ lanterns }: LanternDockProps) {
  const [hover, setHover] = useState<number | null>(null);
  const [pinned, setPinned] = useState<number | null>(null);
  if (lanterns.length === 0) return null;
  return (
    <div className={styles.dock} data-coach="lanterns">
      {lanterns.map(({ seat, name, explanation }) => {
        const isOpen = hover === seat || pinned === seat;
        const agent = explanation?.agent === "dqn" ? "DQN" : "PPO";
        return (
          <div
            key={seat}
            className={styles.lantern}
            onMouseEnter={() => setHover(seat)}
            onMouseLeave={() => setHover((cur) => (cur === seat ? null : cur))}
          >
            <button
              type="button"
              className={styles.button}
              aria-expanded={isOpen}
              aria-pressed={pinned === seat}
              aria-controls={`lantern-${seat}`}
              onClick={() => setPinned(pinned === seat ? null : seat)}
              onKeyDown={(e) => {
                if (e.key !== "Escape") return;
                setPinned(null);
                setHover(null);
              }}
            >
              <Emblem emblem={seatOrder[seat].emblem} seat={seatOrder[seat].name} size={22} />
              {name}
              <span className={styles.hint}>top choices</span>
            </button>
            {isOpen ? (
              <div id={`lantern-${seat}`} className={styles.card} role="region" aria-label={`${agent} top choices`}>
                {explanation ? (
                  <>
                    <h3 className={styles.heading}>{agent}&rsquo;s top choices</h3>
                    <p className={styles.sub}>
                      {explanation.agent === "ppo" ? "How likely it found each move" : "How good it rated each move"}, last decision
                    </p>
                    <ol className={styles.bars}>
                      {lanternBars(explanation).map((bar, i) => (
                        <li key={bar.id}>
                          <span className={styles.label}>
                            {i + 1}. {bar.label}
                          </span>
                          <span className={styles.track} aria-hidden="true">
                            <span className={styles.fill} style={{ width: `${bar.share * 100}%` }} />
                          </span>
                          <span className={`${styles.figure} figures`}>{bar.figure}</span>
                        </li>
                      ))}
                    </ol>
                  </>
                ) : (
                  <p className={styles.sub}>No decision yet.</p>
                )}
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
