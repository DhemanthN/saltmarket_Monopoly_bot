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
  /** The human's seat, anchored for the coach marks. */
  human?: number;
}

/** Splits "Star (always buy)" into the short name and its qualifier. */
function splitName(name: string): [string, string | null] {
  const match = /^(.*?) \((.*)\)$/.exec(name);
  return match ? [match[1], match[2]] : [name, null];
}

/** Cash and net worth for every seat, then a feed of rent, trades and auctions. */
export function LedgerRail({ hud, names, active = null, human = -1 }: LedgerRailProps) {
  return (
    <Panel as="aside" floating className={styles.rail} aria-label="Ledger" data-coach="ledger">
      {names.map((fullName, seat) => {
        const [name, qualifier] = splitName(fullName);
        const note = hud.bankrupt[seat] ? "bankrupt" : qualifier;
        return (
        <div key={fullName + seat} className={styles.seat} data-coach={seat === human ? "ledger-you" : undefined}>
          <LedgerRow
            mark={<Emblem emblem={seatOrder[seat].emblem} seat={seatOrder[seat].name} size={22} />}
            label={name}
            value={money(hud.cash[seat])}
            delta={signedMoney(hud.lastDelta[seat])}
            tone={hud.lastDelta[seat] > 0 ? "gain" : hud.lastDelta[seat] < 0 ? "debt" : "default"}
            active={active === seat}
          />
          <p className={`${styles.worth} figures`}>
            Net worth {money(netWorth(hud, seat))}
            {note ? ` · ${note}` : ""}
          </p>
        </div>
        );
      })}
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
