import { seatOrder } from "../styles/tokens";
import { Emblem } from "../ui/Emblem";
import { LedgerRow } from "../ui/LedgerRow";
import { Panel } from "../ui/Panel";
import { money, signedMoney } from "./format";
import { netWorth, type HudState } from "./state";
import styles from "./LedgerRail.module.css";

export interface LedgerRailProps {
  hud: HudState;
  names: readonly string[];
  /** Seat whose turn it is, when known. */
  active?: number | null;
}

/** Cash and net worth for every seat, then a feed of rent, trades and auctions. */
export function LedgerRail({ hud, names, active = null }: LedgerRailProps) {
  return (
    <Panel as="aside" floating className={styles.rail} aria-label="Ledger" data-coach="ledger">
      {names.map((name, seat) => (
        <div key={name + seat} className={styles.seat}>
          <LedgerRow
            mark={<Emblem emblem={seatOrder[seat].emblem} seat={seatOrder[seat].name} size={22} />}
            label={hud.bankrupt[seat] ? `${name} (bankrupt)` : name}
            value={money(hud.cash[seat])}
            delta={signedMoney(hud.lastDelta[seat])}
            tone={hud.lastDelta[seat] > 0 ? "gain" : hud.lastDelta[seat] < 0 ? "debt" : "default"}
            active={active === seat}
          />
          <p className={`${styles.worth} figures`}>Net worth {money(netWorth(hud, seat))}</p>
        </div>
      ))}
      <ul className={styles.feed} aria-live="polite" aria-label="Recent events">
        {hud.feed.map((line) => (
          <li key={line.seq}>{line.text}</li>
        ))}
      </ul>
    </Panel>
  );
}
