import type { DistrictName } from "../styles/tokens";
import { districts } from "../styles/tokens";
import styles from "./Signboard.module.css";

interface SignboardProps {
  name: string;
  /** Pre-formatted price or rent, for example "120". */
  price?: string;
  district?: DistrictName;
}

/** A painted sign for a space. Square corners, 1 px brass bevel, district strip on the left. */
export function Signboard({ name, price, district }: SignboardProps) {
  return (
    <div className={styles.sign} style={district ? { borderInlineStartColor: districts[district] } : undefined}>
      <span className={styles.name}>{name}</span>
      {price ? <span className={`${styles.price} figures`}>{price}</span> : null}
    </div>
  );
}
