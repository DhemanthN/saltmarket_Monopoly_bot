import { useEffect, useRef, useState } from "react";
import boardData from "../../../../data/board.json";
import type { Decision, LegalAction, TradeOfferView } from "../../contract/types";
import { districts, seatOrder, type DistrictName } from "../../styles/tokens";
import { Button } from "../../ui/Button";
import { Emblem } from "../../ui/Emblem";
import { Panel } from "../../ui/Panel";
import { money, spaceName } from "../format";
import { completedGroups, districtColor, districtLabel } from "../groups";
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
  const model = panelModel(decision, hud.cash[decision.seat]);
  const rootRef = useRef<HTMLDivElement>(null);
  const [bidIndex, setBidIndex] = useState(0);
  const [groupIndex, setGroupIndex] = useState(0);

  useEffect(() => {
    rootRef.current?.focus();
  }, []);

  const isAuction = decision.kind === "auction";
  const selectedBid = model.bids[Math.min(bidIndex, model.bids.length - 1)] ?? null;
  const isPropose = decision.kind === "propose";
  const groups = proposalGroups(model);
  const offers = isPropose ? offersFor(model, groups[Math.min(groupIndex, groups.length - 1)]) : [];
  const selectedOffer = offers[Math.min(bidIndex, offers.length - 1)] ?? null;
  const primary = isAuction ? selectedBid : isPropose ? selectedOffer : model.primary;

  useDecisionKeys({
    onEnter: () => primary && onSubmit(primary.id),
    onEscape: () => model.pass && onSubmit(model.pass.id),
    onDigit: (i) => {
      if (isAuction || isPropose) setBidIndex(i);
      else if (model.choices[i + 1]) onSubmit(model.choices[i + 1].id);
    },
    onArrow: (step) => {
      const count = isAuction ? model.bids.length : offers.length;
      if (isAuction || isPropose) setBidIndex((i) => Math.max(0, Math.min(count - 1, i + step)));
    },
  });

  return (
    <div ref={rootRef} tabIndex={-1} className={styles.wrap} data-coach="decision">
    <Panel floating as="section" className={styles.panel} aria-labelledby="decision-title">
      <h2 id="decision-title" className={styles.title}>
        {DECISION_TITLE[decision.kind]}
      </h2>
      <Body decision={decision} model={model} hud={hud} names={names} onSubmit={onSubmit} bidIndex={bidIndex} setBidIndex={setBidIndex} groupIndex={groupIndex} setGroupIndex={setGroupIndex} />
      <div className={styles.actions}>
        {primary ? (
          <Button variant="primary" onClick={() => onSubmit(primary.id)}>
            <span>{primaryLabel(decision, primary, hud.cash[decision.seat])}</span>
            {primaryFigure(decision, primary) ? <span className="figures">{primaryFigure(decision, primary)}</span> : null}
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

/** Trailing amount for list-style primaries ("Build on ..." 40). Buy, bid and offer put theirs in the label. */
function primaryFigure(decision: Decision, action: LegalAction): string | null {
  const inLabel = ["buy", "auction", "propose", "accept"].includes(decision.kind);
  return !inLabel && action.amount !== null ? money(action.amount) : null;
}

function primaryLabel(decision: Decision, action: LegalAction, cash: number): string {
  if (decision.kind === "buy" && action.amount !== null) {
    const short = action.amount - cash;
    return short > 0 ? `Buy for ${money(action.amount)} (raise ${money(short)} first)` : `Buy for ${money(action.amount)}`;
  }
  if (decision.kind === "auction" && action.amount !== null) return `Bid ${money(action.amount)}`;
  if (decision.kind === "accept") return "Accept";
  if (decision.kind === "propose" && action.amount !== null) return `Offer ${money(action.amount)}`;
  return action.label;
}

interface BodyProps extends DecisionPanelProps {
  model: PanelModel;
  bidIndex: number;
  setBidIndex: (i: number) => void;
  groupIndex: number;
  setGroupIndex: (i: number) => void;
}

function Body(props: BodyProps) {
  const { decision } = props;
  switch (decision.kind) {
    case "buy":
      return <Deed space={decision.space} cash={props.hud.cash[decision.seat]} price={decision.price} />;
    case "auction":
      return <Auction {...props} />;
    case "accept":
      return decision.offer ? <OfferLedger offer={decision.offer} names={props.names} seat={decision.seat} owner={props.hud.owner} /> : null;
    case "propose":
      return <ProposeList {...props} />;
    default:
      return <ChoiceList {...props} />;
  }
}

function Deed({ space, cash, price, ladder = true }: { space: number | null; cash: number; price: number | null; ladder?: boolean }) {
  if (space === null) return null;
  const raw = RAW[space];
  const district = raw.group as DistrictName | undefined;
  const rents = raw.rents ?? [];
  const showLadder = ladder && raw.kind === "property";
  return (
    <div className={styles.deed} style={district ? { borderInlineStartColor: districts[district] } : undefined}>
      <p className={styles.deedName}>{raw.name}</p>
      <p className={styles.deedMeta}>{district ? `${district} district` : raw.kind}</p>
      {price !== null ? (
        <dl className={styles.facts}>
          <dt>Price</dt>
          <dd className="figures">{money(price)}</dd>
          <dt>Cash after buying</dt>
          <dd className={`figures ${cash - price < 0 ? styles.short : ""}`}>{money(cash - price)}</dd>
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
  const selected = Math.min(bidIndex, model.bids.length - 1);
  return (
    <>
      {decision.space !== null ? <Deed space={decision.space} cash={hud.cash[decision.seat]} price={null} ladder={false} /> : null}
      {decision.price !== null ? (
        <p className={styles.note}>
          List price <span className="figures">{money(decision.price)}</span>. Bids are shares of it.
        </p>
      ) : null}
      <ol className={styles.ladderBids} aria-live="polite" aria-label="Bids so far">
        {names.map((name, seat) => {
          const bid = hud.auction?.bids[seat] ?? null;
          const leads = hud.auction?.high?.seat === seat;
          return hud.bankrupt[seat] ? null : (
            <li key={name + seat} className={leads ? styles.leads : ""}>
              <Emblem emblem={seatOrder[seat].emblem} seat={seatOrder[seat].name} size={20} />
              <span>{name}</span>
              <span className="figures">{bid === null ? "no bid" : money(bid)}</span>
            </li>
          );
        })}
      </ol>
      <div role="radiogroup" aria-label="Bid amount" className={`${styles.chips} ${styles.bidChips}`}>
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
        {model.choices.slice(1).map((action, i) => (
          <li key={action.id}>
            <button
              type="button"
              className={styles.row}
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

function proposalGroups(model: PanelModel): string[] {
  return [...new Set(model.choices.map((a) => a.group ?? "other"))];
}

function offersFor(model: PanelModel, group: string): LegalAction[] {
  return model.choices.filter((a) => (a.group ?? "other") === group).sort((x, y) => (x.amount ?? 0) - (y.amount ?? 0));
}

/** Pick a group, then one of its premiums. The primary button sends the selected offer. */
function ProposeList({ model, decision, hud, groupIndex, setGroupIndex, bidIndex, setBidIndex }: BodyProps) {
  const groups = proposalGroups(model);
  const group = groups[Math.min(groupIndex, groups.length - 1)];
  const offers = offersFor(model, group);
  const selected = Math.min(bidIndex, offers.length - 1);
  const completes = completedGroups(offers[0]?.offer?.takeSpaces ?? [], decision.seat, hud.owner);
  return (
    <div className={styles.groups}>
      <p className={styles.note}>Pick a group, then one of three premiums.</p>
      <div role="radiogroup" aria-label="Group to buy" className={styles.chips}>
        {groups.map((g, i) => (
          <button
            key={g}
            type="button"
            role="radio"
            aria-checked={g === group}
            className={`${styles.chip} ${g === group ? styles.chipOn : ""}`}
            onClick={() => {
              setGroupIndex(i);
              setBidIndex(0);
            }}
          >
            {districtColor(g) ? <span className={styles.swatch} style={{ background: districtColor(g) ?? undefined }} aria-hidden="true" /> : null}
            {g === "other" ? "Other" : districtLabel(g)}
          </button>
        ))}
      </div>
      <p className={styles.deedMeta}>
        {offers[0]?.label.replace(/^Offer \d+ for /i, "For ")}
        {completes.length > 0 ? <span className={styles.badge}>Completes {districtLabel(completes[0])}</span> : null}
      </p>
      <div role="radiogroup" aria-label="Premium" className={styles.chips}>
        {offers.map((a, i) => (
          <button
            key={a.id}
            type="button"
            role="radio"
            aria-checked={i === selected}
            className={`${styles.chip} ${i === selected ? styles.chipOn : ""} figures`}
            onClick={() => setBidIndex(i)}
          >
            <span className={styles.chipIndex}>{i + 1}</span>
            {money(a.amount ?? 0)}
          </button>
        ))}
      </div>
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
function OfferLedger({ offer, names, seat, owner }: { offer: TradeOfferView; names: readonly string[]; seat: number; owner: readonly (number | null)[] }) {
  const completes = completedGroups(offer.giveSpaces, seat, owner);
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
            {completes.map((g) => (
              <li key={g} className={styles.badge}>
                <span className={styles.swatch} style={{ background: districtColor(g) ?? undefined }} aria-hidden="true" />
                Completes {districtLabel(g)}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </>
  );
}
