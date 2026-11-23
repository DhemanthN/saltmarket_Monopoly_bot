import type { HTMLAttributes } from "react";
import styles from "./Panel.module.css";

interface PanelProps extends HTMLAttributes<HTMLElement> {
  /** `paper` is the default surface. `sailcloth` is a raised surface for labels and cards. */
  surface?: "paper" | "sailcloth";
  /** Floating panels get the paper-lift shadow. Panels set into a page do not. */
  floating?: boolean;
  as?: "section" | "div" | "aside";
}

/** A cut-paper surface: 2 px corners, hairline brass edge. */
export function Panel({ surface = "paper", floating = false, as: Tag = "section", className, ...rest }: PanelProps) {
  const classes = [styles.panel, styles[surface], floating ? styles.floating : "", className ?? ""].join(" ");
  return <Tag className={classes} {...rest} />;
}
