import { useEffect, useState } from "react";
import {
  contrastRatio,
  districts,
  motion,
  palette,
  seatOrder,
  seats,
  spacing,
  typeScale,
  zLayers,
  type DistrictName,
} from "../styles/tokens";
import { Button } from "../ui/Button";
import { Emblem } from "../ui/Emblem";
import { LedgerRow } from "../ui/LedgerRow";
import { Panel } from "../ui/Panel";
import { Signboard } from "../ui/Signboard";
import { useToast } from "../ui/Toast";
import styles from "./TokensPage.module.css";

const SURFACE_COLOURS = [
  ["paper", palette.paper],
  ["paper-deep", palette.paperDeep],
  ["sailcloth", palette.sailcloth],
  ["ink", palette.ink],
  ["ink-soft", palette.inkSoft],
  ["brass", palette.brass],
  ["tide", palette.tide],
  ["focus", palette.focus],
  ["danger", palette.danger],
  ["ok", palette.ok],
  ["night", palette.night],
  ["night-panel", palette.nightPanel],
  ["night-text", palette.nightText],
] as const;

function ratio(a: string, b: string): string {
  return contrastRatio(a, b).toFixed(2);
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className={styles.section}>
      <h2>{title}</h2>
      {children}
    </section>
  );
}

function MotionDemo() {
  const [moved, setMoved] = useState(false);
  return (
    <div>
      <Button onClick={() => setMoved((m) => !m)}>Play the three speeds</Button>
      {(Object.keys(motion) as (keyof typeof motion)[]).map((name) => (
        <div className={styles.track} key={name}>
          <span className={`${styles.trackLabel} figures`}>
            {name} {motion[name].ms} ms
          </span>
          <span
            className={styles.puck}
            style={{
              transform: moved ? "translateX(calc(100cqw - 24px))" : "none",
              transition: `transform var(--motion-${name}) var(--ease-${name})`,
            }}
          />
        </div>
      ))}
    </div>
  );
}

/** Dev-only reference for every token and primitive. Not part of the production build. */
export default function TokensPage() {
  const toast = useToast();
  const [night, setNight] = useState(false);
  const base = night ? palette.night : palette.paper;

  useEffect(() => {
    document.documentElement.dataset.mood = night ? "night" : "day";
    return () => {
      delete document.documentElement.dataset.mood;
    };
  }, [night]);

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <h1>Design tokens</h1>
        <Button onClick={() => setNight((n) => !n)} aria-pressed={night}>
          {night ? "Switch to day" : "Switch to night"}
        </Button>
      </header>

      <Section title="Colour">
        <ul className={styles.swatches}>
          {SURFACE_COLOURS.map(([name, hex]) => (
            <li key={name} className={styles.swatch}>
              <span className={styles.chip} style={{ background: hex }} />
              <span className={styles.swatchName}>{name}</span>
              <span className={`${styles.swatchMeta} figures`}>
                {hex}, {ratio(hex, base)} on {night ? "night" : "paper"}
              </span>
            </li>
          ))}
        </ul>
      </Section>

      <Section title="Districts">
        <ul className={styles.swatches}>
          {(Object.keys(districts) as DistrictName[]).map((name) => (
            <li key={name} className={styles.swatch}>
              <span className={styles.chip} style={{ background: districts[name] }}>
                <span className={styles.chipLabel}>{name}</span>
              </span>
              <span className={styles.swatchName}>{name}</span>
              <span className={`${styles.swatchMeta} figures`}>
                {districts[name]}, label {ratio(palette.sailcloth, districts[name])}, mark{" "}
                {ratio(districts[name], base)}
              </span>
            </li>
          ))}
        </ul>
      </Section>

      <Section title="Seats">
        <ul className={styles.swatches}>
          {seatOrder.map(({ name, emblem, label }) => (
            <li key={name} className={styles.swatch}>
              <Emblem emblem={emblem} seat={name} size={48} label={`${label} emblem`} />
              <span className={styles.swatchName}>
                {name}, {label}
              </span>
              <span className={`${styles.swatchMeta} figures`}>{seats[name]}</span>
            </li>
          ))}
        </ul>
      </Section>

      <Section title="Type">
        <div className={styles.type}>
          {typeScale.map((step) => (
            <p
              key={step.name}
              className={step.size >= 31 ? styles.display : undefined}
              style={{ fontSize: step.size, lineHeight: `${step.line}px` }}
            >
              {step.name} {step.size}/{step.line} The harbour opens at dawn
            </p>
          ))}
          <p className="figures">Tabular figures: 1,420 &nbsp; 308 &nbsp; 15,000 &nbsp; 7</p>
        </div>
      </Section>

      <Section title="Spacing">
        <div className={styles.spacing}>
          {spacing.map((px, i) => (
            <div key={px} className={styles.spaceRow}>
              <span className={`${styles.spaceName} figures`}>
                --space-{i + 1}, {px} px
              </span>
              <span className={styles.spaceBar} style={{ width: px }} />
            </div>
          ))}
        </div>
      </Section>

      <Section title="Radius and shadow">
        <div className={styles.shapes}>
          <div className={styles.shape} style={{ borderRadius: "var(--radius-panel)" }}>Panel, 2 px</div>
          <div className={styles.shape} style={{ borderRadius: "var(--radius-signboard)" }}>Signboard, 0</div>
          <div className={styles.shape} style={{ borderRadius: "var(--radius-button)" }}>Button, 4 px</div>
          <div
            className={styles.shape}
            style={{ borderRadius: "var(--radius-panel)", boxShadow: "var(--shadow-paper-lift)" }}
          >
            Paper lift
          </div>
        </div>
      </Section>

      <Section title="Motion">
        <MotionDemo />
      </Section>

      <Section title="Z-layers">
        <ul className={styles.layers}>
          {Object.entries(zLayers).map(([name, z]) => (
            <li key={name} className="figures">
              {name.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`)}: {z}
            </li>
          ))}
        </ul>
      </Section>

      <Section title="Buttons">
        <div className={styles.row}>
          <Button variant="primary">Buy for 120</Button>
          <Button>Pass to auction</Button>
          <Button variant="quiet">How to play</Button>
          <Button variant="primary" disabled>
            Disabled
          </Button>
          <Button onClick={() => toast("Bought Bladderwrack Flats for 50.")}>Show a toast</Button>
        </div>
      </Section>

      <Section title="Panel">
        <div className={styles.row}>
          <Panel>
            <h3>Paper panel</h3>
            <p>Set into the page, no shadow.</p>
          </Panel>
          <Panel surface="sailcloth" floating>
            <h3>Floating sailcloth</h3>
            <p>Raised surface with paper lift.</p>
          </Panel>
        </div>
      </Section>

      <Section title="Ledger">
        <Panel aria-label="Ledger example">
          <LedgerRow
            mark={<Emblem emblem="sun" seat="saffron" />}
            label="You"
            value="1,420"
            delta="+120"
            tone="gain"
            active
          />
          <LedgerRow mark={<Emblem emblem="wave" seat="teal" />} label="PPO agent" value="980" delta={"−60"} tone="debt" />
          <LedgerRow mark={<Emblem emblem="star" seat="vermilion" />} label="Scripted bot" value={"−40"} />
        </Panel>
      </Section>

      <Section title="Signboards">
        <div className={styles.row}>
          <Signboard name="Home Quay" />
          <Signboard name="Bladderwrack Flats" price="50" district="kelp" />
          <Signboard name="Crown Wharf" price="400" district="crown" />
        </div>
      </Section>
    </main>
  );
}
