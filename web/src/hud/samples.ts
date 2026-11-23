import type { Decision, LegalAction, TradeOfferView } from "../contract/types";

/**
 * Hand-written decisions for the `/hud` review page and tests. The engine builds the real ones;
 * labels here copy `src/saltmarket/web/labels.py`. Ids are arbitrary.
 */
const act = (id: number, label: string, extra: Partial<LegalAction> = {}): LegalAction => ({
  id,
  label,
  amount: null,
  group: null,
  space: null,
  offer: null,
  ...extra,
});

const base = { seat: 0, turn: 12, space: null, price: null, debt: null, offer: null };

const incoming: TradeOfferView = {
  proposer: 1,
  responder: 0,
  giveSpaces: [4],
  takeSpaces: [1, 2],
  giveCash: 60,
  takeCash: 0,
  givePasses: 0,
  takePasses: 0,
};

const premium = (cash: number): TradeOfferView => ({
  proposer: 0,
  responder: 1,
  giveSpaces: [],
  takeSpaces: [1, 2],
  giveCash: cash,
  takeCash: 0,
  givePasses: 0,
  takePasses: 0,
});

const proposal = (id: number, cash: number): LegalAction =>
  act(id, `Offer ${cash} for Bladderwrack Flats, Oarweed Shoal`, {
    amount: cash,
    group: "kelp",
    space: 1,
    offer: premium(cash),
  });

export const SAMPLE_DECISIONS: Decision[] = [
  {
    ...base,
    kind: "buy",
    space: 21,
    price: 210,
    legal: [act(1, "Buy Honeyglass Strand", { amount: 210, space: 21 }), act(0, "Decline and send it to auction")],
  },
  {
    ...base,
    kind: "auction",
    space: 21,
    price: 210,
    legal: [
      act(2, "Bid 52", { amount: 52, space: 21 }),
      act(3, "Bid 105", { amount: 105, space: 21 }),
      act(4, "Bid 157", { amount: 157, space: 21 }),
      act(5, "Bid 210", { amount: 210, space: 21 }),
      act(6, "Bid 262", { amount: 262, space: 21 }),
      act(0, "Pass"),
    ],
  },
  {
    ...base,
    kind: "build",
    legal: [
      act(10, "Build on Bladderwrack Flats", { amount: 40, group: "kelp", space: 1 }),
      act(11, "Build on Limpet Rocks", { amount: 50, group: "reef", space: 6 }),
      act(0, "Done building"),
    ],
  },
  {
    ...base,
    kind: "liquidate",
    debt: 180,
    legal: [
      act(20, "Sell a building on Limpet Rocks", { amount: 25, group: "reef", space: 6 }),
      act(21, "Mortgage Oarweed Shoal", { amount: 25, group: "kelp", space: 2 }),
      act(0, "Keep everything"),
    ],
  },
  {
    ...base,
    kind: "raise_cash",
    debt: 180,
    legal: [
      act(21, "Mortgage Oarweed Shoal", { amount: 25, group: "kelp", space: 2 }),
      act(22, "Mortgage Northwind Ferry", { amount: 90, space: 5 }),
    ],
  },
  {
    ...base,
    kind: "unmortgage",
    legal: [act(30, "Lift the mortgage on Oarweed Shoal", { amount: 27, group: "kelp", space: 2 }), act(0, "Done")],
  },
  {
    ...base,
    kind: "brig",
    legal: [act(40, "Roll for doubles"), act(41, "Pay the fine", { amount: 50 }), act(42, "Use a Brig pass")],
  },
  {
    ...base,
    kind: "propose",
    legal: [proposal(50, 60), proposal(51, 90), proposal(52, 120), act(0, "Make no offer")],
  },
  {
    ...base,
    kind: "accept",
    offer: incoming,
    legal: [act(60, "Accept the offer"), act(0, "Decline")],
  },
];
