import { seatOrder } from "../styles/tokens";
import { Emblem } from "../ui/Emblem";
import { LedgerRow } from "../ui/LedgerRow";
import { Panel } from "../ui/Panel";
import { useState } from "react";
import { TURNS_PER_DAY } from "../world/sun";
import { dayCaption, money, shortName, signedMoney } from "./format";
import { netWorth, type HudState } from "./state";
import styles from "./LedgerRail.module.css";

export interface LedgerRailProps {
  hud: HudState;
  names: readonly string[];
  /** Seat whose turn it is, when known. */
  active?: number | null;
  /** The human's seat, anchored for the coach marks. */
  human?: number;
}

/** Cash for every seat, then (unless folded away) net worth, the day and a short feed of rent, trades and auctions. */
export function LedgerRail({ hud, names, active = null, human = -1 }: LedgerRailProps) {
  const [open, setOpen] = useState(false);
  return (
    <Panel as="aside" floating className={styles.rail} aria-label="Ledger" data-coach="ledger">
      {names.map((fullName, seat) => {
        const name = shortName(fullName);
        const note = hud.bankrupt[seat] ? "out" : null;
        return (
          <div key={fullName + seat} className={styles.seat} data-coach={seat === human ? "ledger-you" : undefined}>
            <LedgerRow
              mark={<Emblem emblem={seatOrder[seat].emblem} seat={seatOrder[seat].name} size={22} />}
              label={note ? `${name} (${note})` : name}
              value={money(hud.cash[seat])}
              delta={signedMoney(hud.lastDelta[seat])}
              tone={hud.lastDelta[seat] > 0 ? "gain" : hud.lastDelta[seat] < 0 ? "debt" : "default"}
              active={active === seat}
            />
            {open ? <p className={`${styles.worth} figures`}>Net worth {money(netWorth(hud, seat))}</p> : null}
          </div>
        );
      })}
      <p className={styles.day}>{dayCaption(hud.turn, TURNS_PER_DAY)}</p>
      <button type="button" className={styles.toggle} aria-expanded={open} onClick={() => setOpen((o) => !o)}>
        {open ? "Hide net worth" : "Show net worth"}
      </button>
      <ul className={styles.feed} aria-live="polite" aria-label="Recent events">
        {hud.feed.map((line) => (
          <li key={line.seq} className={line.coin ? styles.rent : undefined}>
            {line.text}
          </li>
        ))}
      </ul>
    </Panel>
  );
}
