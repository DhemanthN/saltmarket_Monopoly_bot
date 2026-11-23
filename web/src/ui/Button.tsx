import type { ButtonHTMLAttributes } from "react";
import styles from "./Button.module.css";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** One primary per decision panel. Secondary is outlined. Quiet is text only. */
  variant?: "primary" | "secondary" | "quiet";
}

export function Button({ variant = "secondary", className, type = "button", ...rest }: ButtonProps) {
  return <button type={type} className={`${styles.button} ${styles[variant]} ${className ?? ""}`} {...rest} />;
}
