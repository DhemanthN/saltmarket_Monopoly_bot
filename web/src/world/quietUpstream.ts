/*
 * @react-three/fiber 9.8 still builds a THREE.Clock, which Three 0.187 logs a deprecation for on
 * every scene mount. We cannot change that code, so this drops that one message and nothing else.
 */
const warn = console.warn.bind(console);
console.warn = (...args: unknown[]) => {
  if (typeof args[0] === "string" && args[0].includes("THREE.Clock")) return;
  warn(...args);
};
