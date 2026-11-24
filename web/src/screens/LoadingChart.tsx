import { useEffect, useLayoutEffect, useRef, useState, useSyncExternalStore } from "react";
import type { LoadPhase } from "../runtime/protocol";
import { armIntro, isCalm, releaseIntro } from "../world/cameraBus";
import { LOAD_CAPTION } from "./loadCaption";
import { ROUTE_STOPS, stopAhead, stopReached } from "./loadStages";
import styles from "./LoadingChart.module.css";

/** Sea routes. The wide chart runs left to right; phones get the same route running upward. */
const WIDE = { box: [960, 420], path: "M70 330 C 190 120, 330 120, 430 230 S 640 360, 740 200 S 840 100, 890 150" } as const;
const TALL = { box: [360, 640], path: "M70 580 C 320 500, 40 420, 230 350 S 320 220, 150 160 S 60 100, 250 60" } as const;
const PHONE = "(max-width: 600px)";
/** How long the ship rests on the X before the chart fades, then how long the fade takes (ms). */
const HOLD_MS = 500;
const FADE_MS = 600;
const CALM_FADE_MS = 150;

const subscribePhone = (fn: () => void) => {
  const mq = window.matchMedia(PHONE);
  mq.addEventListener("change", fn);
  return () => mq.removeEventListener("change", fn);
};
const isPhone = () => window.matchMedia(PHONE).matches;

interface Props {
  phase: LoadPhase;
  /** True once the engine is ready and the world is mounting underneath. */
  ready: boolean;
  /** Called after the chart has faded away. */
  onDone: () => void;
}

/**
 * Loading screen: a dark ocean blueprint with a dotted sea route. The ship advances one stop for
 * each real load step (runtime, Python, game code, models) and ends on an X when the first scene
 * has drawn. Then the chart fades and the camera intro swoop starts.
 */
export function LoadingChart({ phase, ready, onDone }: Props) {
  const phone = useSyncExternalStore(subscribePhone, isPhone);
  const shape = phone ? TALL : WIDE;
  const route = useRef<SVGPathElement>(null);
  const [points, setPoints] = useState<{ x: number; y: number }[]>([]);
  const [length, setLength] = useState(0);
  const [sceneDrawn, setSceneDrawn] = useState(false);
  const [fading, setFading] = useState(false);
  const calm = isCalm();
  const reached = stopReached(phase, sceneDrawn);
  const ahead = stopAhead(reached);

  // Hold the camera intro until this chart has faded.
  useEffect(() => {
    armIntro();
    return releaseIntro;
  }, []);

  useLayoutEffect(() => {
    const el = route.current;
    if (!el) return;
    const total = el.getTotalLength();
    setLength(total);
    setPoints(ROUTE_STOPS.map((_, i) => el.getPointAtLength((total * i) / (ROUTE_STOPS.length - 1))));
  }, [phone]);

  // The first scene counts as drawn two frames after the world mounts.
  useEffect(() => {
    if (!ready) return;
    let second = 0;
    const first = requestAnimationFrame(() => {
      second = requestAnimationFrame(() => setSceneDrawn(true));
    });
    return () => {
      cancelAnimationFrame(first);
      cancelAnimationFrame(second);
    };
  }, [ready]);

  useEffect(() => {
    if (!sceneDrawn) return;
    const hold = calm ? 0 : HOLD_MS;
    const start = window.setTimeout(() => setFading(true), hold);
    const done = window.setTimeout(() => {
      releaseIntro();
      onDone();
    }, hold + (calm ? CALM_FADE_MS : FADE_MS));
    return () => {
      window.clearTimeout(start);
      window.clearTimeout(done);
    };
  }, [sceneDrawn, calm, onDone]);

  const fraction = reached / (ROUTE_STOPS.length - 1);
  const ship = points[reached];
  const last = points[ROUTE_STOPS.length - 1];
  const [w, h] = shape.box;

  return (
    <div className={`${styles.chart} ${fading ? styles.fading : ""} ${calm ? styles.calm : ""}`} aria-hidden="true">
      <p className={styles.title}>Saltmarket</p>
      <svg className={styles.map} viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="xMidYMid meet">
        <path ref={route} d={shape.path} className={styles.route} />
        {length > 0 ? (
          <path d={shape.path} className={styles.sailed} strokeDasharray={`${length} ${length}`} strokeDashoffset={length * (1 - fraction)} />
        ) : null}
        {points.map((p, i) =>
          i === ROUTE_STOPS.length - 1 ? null : (
            <g key={ROUTE_STOPS[i].id}>
              <circle cx={p.x} cy={p.y} r={6} className={i <= reached ? styles.stopDone : styles.stop} />
              {i === ahead ? <circle cx={p.x} cy={p.y} r={6} className={styles.pulse} /> : null}
              <text
                x={p.x + (phone ? 14 : 0)}
                y={p.y + (phone ? 4 : 26)}
                textAnchor={phone ? "start" : "middle"}
                className={i <= reached ? styles.labelDone : styles.label}
              >
                {ROUTE_STOPS[i].label}
              </text>
            </g>
          ),
        )}
        {last ? (
          <g className={styles.x} transform={`translate(${last.x} ${last.y})`}>
            <path d="M-12 -12L12 12M12 -12L-12 12" />
            <text
              x={phone ? -18 : 0}
              y={phone ? 4 : 34}
              textAnchor={phone ? "end" : "middle"}
              className={reached === ROUTE_STOPS.length - 1 ? styles.labelDone : styles.label}
            >
              {ROUTE_STOPS[ROUTE_STOPS.length - 1].label}
            </text>
          </g>
        ) : null}
        {ship ? (
          <g className={styles.ship} style={{ transform: `translate(${ship.x}px, ${ship.y}px)` }}>
            <path d="M-14 2h28l-5 8h-18z" className={styles.hull} />
            <path d="M0 -16V2M0 -14l11 11H0z" className={styles.sail} />
          </g>
        ) : null}
      </svg>
      <p className={styles.caption}>{LOAD_CAPTION[phase]}</p>
    </div>
  );
}
