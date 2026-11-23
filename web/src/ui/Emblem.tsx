import type { EmblemName, SeatName } from "../styles/tokens";
import { seats } from "../styles/tokens";

interface EmblemProps {
  emblem: EmblemName;
  seat: SeatName;
  size?: number;
  /** Accessible name. Omit when a visible label already names the seat. */
  label?: string;
}

const PATHS: Record<EmblemName, string> = {
  sun: "M16 9a7 7 0 1 0 0 14 7 7 0 0 0 0-14ZM16 2v4M16 26v4M2 16h4M26 16h4M6 6l3 3M23 23l3 3M26 6l-3 3M9 23l-3 3",
  wave: "M3 12c3-4 5-4 8 0s5 4 8 0 5-4 8 0M3 20c3-4 5-4 8 0s5 4 8 0 5-4 8 0",
  star: "M16 3l3.5 8.2 8.9.8-6.7 5.9 2 8.7L16 21.9 8.3 26.6l2-8.7-6.7-5.9 8.9-.8Z",
  anchor: "M16 5a2.5 2.5 0 1 0 0 .01ZM16 9v18M10 13h12M5 20c1 5 6 7 11 7s10-2 11-7",
};

/** Seat emblem: custom SVG on a round seat-coloured disc with a 1.5 px ink outline. */
export function Emblem({ emblem, seat, size = 28, label }: EmblemProps) {
  const glyph = seat === "saffron" ? "var(--ink)" : "var(--sailcloth)";
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      style={{ flex: "none" }}
    >
      <circle cx="16" cy="16" r="15" fill={seats[seat]} stroke="var(--outline)" strokeWidth="1.5" />
      <g transform="translate(16 16) scale(0.62) translate(-16 -16)">
        <path
          d={PATHS[emblem]}
          fill={emblem === "star" ? glyph : "none"}
          stroke={glyph}
          strokeWidth="2.4"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </g>
    </svg>
  );
}
