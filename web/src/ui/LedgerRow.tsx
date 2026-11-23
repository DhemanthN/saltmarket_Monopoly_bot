import type { ReactNode } from "react";
import styles from "./LedgerRow.module.css";

interface LedgerRowProps {
  /** Seat emblem or district swatch. */
  mark?: ReactNode;
  label: string;
  /** Pre-formatted figure, for example "1,420". Shown in tabular figures. */
  value: string;
  /** Change since the last update. Always print the sign (use U+2212 for minus); colour is never the only cue. */
  delta?: string;
  /** Colours the delta, not the balance. */
  tone?: "default" | "gain" | "debt";
  active?: boolean;
}

/** One ledger line: mark, label, then right-aligned tabular figures on a hairline brass rule. */
export function LedgerRow({ mark, label, value, delta, tone = "default", active = false }: LedgerRowProps) {
  return (
    <div className={`${styles.row} ${active ? styles.active : ""}`}>
      <span className={styles.mark}>{mark}</span>
      <span className={styles.label}>{label}</span>
      <span className={`${styles.delta} figures ${tone === "default" ? "" : styles[tone]}`}>{delta}</span>
      <span className={`${styles.value} figures ${value.startsWith("−") ? styles.negative : ""}`}>{value}</span>
    </div>
  );
}
