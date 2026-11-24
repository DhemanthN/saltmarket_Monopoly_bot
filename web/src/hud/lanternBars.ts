import type { Explanation } from "../contract/types";

export interface LanternBar {
  id: number;
  label: string;
  /** Pre-formatted figure: a percentage for PPO, a Q-value for DQN. */
  figure: string;
  /** Bar length from 0 to 1. */
  share: number;
}

const MIN_SHARE = 0.06;

/** Turns an explanation into rows. PPO shows probabilities as they are. DQN scales the three Q-values against each other. */
export function lanternBars(explanation: Explanation): LanternBar[] {
  const top = explanation.top.slice(0, 3);
  if (explanation.agent === "ppo") {
    return top.map((a) => ({
      id: a.id,
      label: a.label,
      figure: `${((a.prob ?? 0) * 100).toFixed(0)}%`,
      share: Math.max(MIN_SHARE, a.prob ?? 0),
    }));
  }
  const qs = top.map((a) => a.q ?? 0);
  const lo = Math.min(...qs);
  const span = Math.max(...qs) - lo;
  return top.map((a) => ({
    id: a.id,
    label: a.label,
    figure: (a.q ?? 0).toFixed(2).replace("-", "−"),
    share: span === 0 ? 1 : Math.max(MIN_SHARE, ((a.q ?? 0) - lo) / span),
  }));
}
