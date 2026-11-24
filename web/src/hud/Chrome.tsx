import { useLayoutEffect, useRef, useState, useSyncExternalStore } from "react";
import { getHeading, subscribeHeading } from "../world/cameraBus";
import { compassMarks, headingText } from "./compass";
import { telemetryFor } from "./telemetry";
import styles from "./Chrome.module.css";

const BRACKET = (
  <svg className={styles.bracket} viewBox="0 0 34 34" aria-hidden="true">
    <path d="M2 32V8Q2 2 8 2H32" strokeWidth="2" />
    <path d="M8 32V13Q8 8 13 8H32" strokeWidth="1" opacity=".65" />
    <path d="M15 12l3 3-3 3-3-3z" fill="currentColor" stroke="none" />
  </svg>
);

/** The bar's width in pixels, tracked so the ticks are drawn at a readable size. */
function useWidth(): [React.RefObject<HTMLDivElement | null>, number] {
  const ref = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(360);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    setWidth(el.clientWidth || 360);
    const observer = new ResizeObserver(() => setWidth(el.clientWidth || 360));
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
  return [ref, width];
}

/** Compass bar: ticks slide past a fixed needle as the camera turns. Redraws on each whole degree. */
function CompassBar() {
  const heading = useSyncExternalStore(subscribeHeading, getHeading);
  const [ref, width] = useWidth();
  const height = 44;
  return (
    <div className={styles.compass} role="img" aria-label={`Camera heading ${headingText(heading)}`}>
      <b className={styles.reading}>{headingText(heading)}</b>
      <div ref={ref} className={styles.bar}>
        <svg viewBox={`0 0 ${width} ${height}`} aria-hidden="true">
          {compassMarks(heading, width).map((m) => (
            <g key={m.x}>
              <path d={`M${m.x} 0v${height * m.length}`} className={m.point ? styles.major : styles.minor} />
              {m.point ? (
                <text x={m.x} y={height * 0.72} textAnchor="middle" className={m.point.length === 1 ? styles.cardinal : styles.point}>
                  {m.point}
                </text>
              ) : m.numbered && width > 300 ? (
                <text x={m.x} y={height * 0.7} textAnchor="middle" className={styles.degree}>
                  {m.degrees}
                </text>
              ) : null}
            </g>
          ))}
          <path d={`M${width / 2} 0V${height}`} className={styles.needle} />
          <path d={`M${width / 2 - 5} ${height}h10l-5-7z`} className={styles.pointer} />
        </svg>
      </div>
    </div>
  );
}

interface ChromeProps {
  turn: number;
  seatCount: number;
  /** Cash of the person's seat; null in a watched game. */
  cash: number | null;
}

/**
 * The chart-table frame around the world: corner brackets, a vignette, a compass bar that follows
 * the real camera heading, and a readout of the turn, round, time of day and cash. It draws only
 * data from the game and never takes pointer events.
 */
export function Chrome({ turn, seatCount, cash }: ChromeProps) {
  const t = telemetryFor(turn, seatCount, cash);
  return (
    <div className={styles.chrome} aria-hidden={false}>
      <div className={styles.vignette} aria-hidden="true" />
      <span className={`${styles.corner} ${styles.tl}`}>{BRACKET}</span>
      <span className={`${styles.corner} ${styles.tr}`}>{BRACKET}</span>
      <span className={`${styles.corner} ${styles.bl}`}>{BRACKET}</span>
      <span className={`${styles.corner} ${styles.br}`}>{BRACKET}</span>
      <CompassBar />
      <p className={styles.tele}>
        <span>
          <i>Turn</i> <b>{t.turn}</b>
        </span>
        <span>
          <i>Round</i> <b>{t.round}</b>
        </span>
        <span>
          <b>{t.timeOfDay}</b>
        </span>
        {t.cash !== null ? (
          <span className={styles.cash}>
            <i>Cash</i> <b>{t.cash.toLocaleString("en-US")}</b>
          </span>
        ) : null}
      </p>
    </div>
  );
}
