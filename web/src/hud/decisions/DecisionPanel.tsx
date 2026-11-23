import { useEffect, useRef, useState } from "react";
import boardData from "../../../../data/board.json";
import type { Decision, LegalAction, TradeOfferView } from "../../contract/types";
import { districts, seatOrder, type DistrictName } from "../../styles/tokens";
import { Button } from "../../ui/Button";
import { Emblem } from "../../ui/Emblem";
import { Panel } from "../../ui/Panel";
import { money, spaceName } from "../format";
import { DECISION_TITLE, panelModel, type PanelModel } from "../layout";
import type { HudState } from "../state";
import { useDecisionKeys } from "../useDecisionKeys";
import styles from "./DecisionPanel.module.css";

interface RawSpace {
  name: string;
  kind: string;
  group?: string;
  price?: number;
  rents?: number[];
}

const RAW = boardData.spaces as RawSpace[];
const LADDER_LABELS = ["No depots", "1 depot", "2 depots", "3 depots", "4 depots", "Port"];

export interface DecisionPanelProps {
  decision: Decision;
  hud: HudState;
  /** Display name per seat. */
  names: readonly string[];
  onSubmit: (actionId: number) => void;
}

/** One panel per decision. Only legal actions are shown, with one primary action. */
export function DecisionPanel({ decision, hud, names, onSubmit }: DecisionPanelProps) {
  const model = panelModel(decision);
  const rootRef = useRef<HTMLDivElement>(null);
  const [bidIndex, setBidIndex] = useState(0);

  useEffect(() => {
    rootRef.current?.focus();
  }, []);

  const isAuction = decision.kind === "auction";
  const selectedBid = model.bids[Math.min(bidIndex, model.bids.length - 1)] ?? null;
  const primary = isAuction ? selectedBid : model.primary;

  useDecisionKeys({
    onEnter: () => primary && onSubmit(primary.id),
    onEscape: () => model.pass && onSubmit(model.pass.id),
    onDigit: (i) => {
      if (isAuction) setBidIndex(i);
      else if (model.choices[i]) onSubmit(model.choices[i].id);
    },
    onArrow: (step) => {
      if (isAuction) setBidIndex((i) => Math.max(0, Math.min(model.bids.length - 1, i + step)));
    },
  });

  return (
    <div ref={rootRef} tabIndex={-1} className={styles.wrap} data-coach="decision">
    <Panel floating as="section" className={styles.panel} aria-labelledby="decision-title">
      <h2 id="decision-title" className={styles.title}>
        {DECISION_TITLE[decision.kind]}
      </h2>
      <Body decision={decision} model={model} hud={hud} names={names} onSubmit={onSubmit} bidIndex={bidIndex} setBidIndex={setBidIndex} />
      <div className={styles.actions}>
        {primary ? (
          <Button variant="primary" onClick={() => onSubmit(primary.id)}>
            {primaryLabel(decision, primary)}
            <kbd className={styles.key}>Enter</kbd>
          </Button>
        ) : null}
        {model.pass ? (
          <Button variant="secondary" onClick={() => onSubmit(model.pass!.id)}>
            {model.pass.label}
            <kbd className={styles.key}>Esc</kbd>
          </Button>
        ) : null}
      </div>
    </Panel>
    </div>
  );
}

function primaryLabel(decision: Decision, action: LegalAction): string {
  if (decision.kind === "buy" && action.amount !== null) return `Buy for ${money(action.amount)}`;
  if (decision.kind === "auction" && action.amount !== null) return `Bid ${money(action.amount)}`;
  if (decision.kind === "accept") return "Accept";
  return action.label;
}

interface BodyProps extends DecisionPanelProps {
  model: PanelModel;
  bidIndex: number;
  setBidIndex: (i: number) => void;
}

function Body(props: BodyProps) {
  const { decision } = props;
  switch (decision.kind) {
    case "buy":
      return <Deed space={decision.space} cash={props.hud.cash[decision.seat]} price={decision.price} />;
    case "auction":
      return <Auction {...props} />;
    case "accept":
      return decision.offer ? <OfferLedger offer={decision.offer} names={props.names} /> : null;
    case "propose":
      return <ProposeList {...props} />;
    default:
      return <ChoiceList {...props} />;
  }
}

function Deed({ space, cash, price }: { space: number | null; cash: number; price: number | null }) {
  if (space === null) return null;
  const raw = RAW[space];
  const district = raw.group as DistrictName | undefined;
  const rents = raw.rents ?? [];
  const showLadder = raw.kind === "property";
  return (
    <div className={styles.deed} style={district ? { borderInlineStartColor: districts[district] } : undefined}>
      <p className={styles.deedName}>{raw.name}</p>
      <p className={styles.deedMeta}>{district ? `${district} district` : raw.kind}</p>
      {price !== null ? (
        <dl className={styles.facts}>
          <dt>Price</dt>
          <dd className="figures">{money(price)}</dd>
          <dt>Cash after buying</dt>
          <dd className="figures">{money(cash - price)}</dd>
        </dl>
      ) : null}
      {showLadder ? (
        <table className={styles.ladder}>
          <caption>Rent ladder</caption>
          <tbody>
            {rents.map((rent, i) => (
              <tr key={LADDER_LABELS[i]}>
                <th scope="row">{LADDER_LABELS[i]}</th>
                <td className="figures">{money(rent)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </div>
  );
}

function Auction({ decision, model, hud, names, bidIndex, setBidIndex }: BodyProps) {
  const high = hud.auction?.high ?? null;
  const selected = Math.min(bidIndex, model.bids.length - 1);
  return (
    <>
      {decision.space !== null ? <Deed space={decision.space} cash={hud.cash[decision.seat]} price={null} /> : null}
      {decision.price !== null ? (
        <p className={styles.note}>
          List price <span className="figures">{money(decision.price)}</span>. Bids are shares of it.
        </p>
      ) : null}
      <p className={styles.highBid} aria-live="polite">
        {high ? (
          <>
            <Emblem emblem={seatOrder[high.seat].emblem} seat={seatOrder[high.seat].name} size={20} />
            <span>
              {names[high.seat]} leads at <span className="figures">{money(high.amount)}</span>
            </span>
          </>
        ) : (
          "No bids yet"
        )}
      </p>
      <div role="radiogroup" aria-label="Bid amount" className={styles.chips}>
        {model.bids.map((bid, i) => (
          <button
            key={bid.id}
            type="button"
            role="radio"
            aria-checked={i === selected}
            className={`${styles.chip} ${i === selected ? styles.chipOn : ""} figures`}
            onClick={() => setBidIndex(i)}
          >
            <span className={styles.chipIndex}>{i + 1}</span>
            {money(bid.amount ?? 0)}
          </button>
        ))}
      </div>
    </>
  );
}

function ChoiceList({ model, hud, decision, onSubmit }: BodyProps) {
  const debt = decision.debt;
  return (
    <>
      {debt !== null ? (
        <p className={styles.note}>
          You owe <span className="figures">{money(debt)}</span> and hold <span className="figures">{money(hud.cash[decision.seat])}</span>.
        </p>
      ) : null}
      <ul className={styles.list}>
        {model.choices.map((action, i) => (
          <li key={action.id}>
            <button
              type="button"
              className={`${styles.row} ${action === model.primary ? styles.rowPrimary : ""}`}
              onClick={() => onSubmit(action.id)}
            >
              <span className={styles.chipIndex}>{i + 1}</span>
              <span className={styles.rowLabel}>{action.label}</span>
              {action.amount !== null ? <span className="figures">{money(action.amount)}</span> : null}
            </button>
          </li>
        ))}
      </ul>
    </>
  );
}

function ProposeList({ model, onSubmit }: BodyProps) {
  const groups = [...new Set(model.choices.map((a) => a.group ?? "other"))];
  let n = 0;
  return (
    <div className={styles.groups}>
      <p className={styles.note}>Pick a group, then one of three premiums.</p>
      {groups.map((group) => (
        <fieldset key={group} className={styles.group}>
          <legend>{group === "other" ? "Other" : `${group} district`}</legend>
          <div className={styles.chips}>
            {model.choices
              .filter((a) => (a.group ?? "other") === group)
              .map((a) => {
                n += 1;
                return (
                  <button key={a.id} type="button" className={`${styles.chip} figures`} onClick={() => onSubmit(a.id)}>
                    <span className={styles.chipIndex}>{n}</span>
                    {money(a.amount ?? 0)}
                  </button>
                );
              })}
          </div>
          <p className={styles.deedMeta}>{model.choices.find((a) => (a.group ?? "other") === group)?.label.replace(/^Offer \d+ for /, "For ")}</p>
        </fieldset>
      ))}
    </div>
  );
}

function side(offer: TradeOfferView, give: boolean): string[] {
  const spaces = give ? offer.giveSpaces : offer.takeSpaces;
  const cash = give ? offer.giveCash : offer.takeCash;
  const passes = give ? offer.givePasses : offer.takePasses;
  return [
    ...spaces.map(spaceName),
    ...(cash ? [`${money(cash)} cash`] : []),
    ...(passes ? [`${passes} Brig pass${passes > 1 ? "es" : ""}`] : []),
  ];
}

/** Two columns from the responder's view: what you give, what you get. */
function OfferLedger({ offer, names }: { offer: TradeOfferView; names: readonly string[] }) {
  return (
    <>
      <p className={styles.note}>{names[offer.proposer]} offers a trade.</p>
      <div className={styles.columns}>
        <div>
          <h3 className={styles.colTitle}>You give</h3>
          <ul className={styles.plain}>
            {side(offer, false).map((t) => (
              <li key={t}>{t}</li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className={styles.colTitle}>You get</h3>
          <ul className={styles.plain}>
            {side(offer, true).map((t) => (
              <li key={t}>{t}</li>
            ))}
          </ul>
        </div>
      </div>
    </>
  );
}
