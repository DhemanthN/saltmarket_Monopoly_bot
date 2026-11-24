import { EffectComposer, TiltShift2 } from "@react-three/postprocessing";

/** Tilt-shift blur for chart view on the high tier only: the atoll reads as a model on a table. */
export default function ChartTiltShift() {
  return (
    <EffectComposer multisampling={0}>
      <TiltShift2 blur={0.07} taper={0.85} start={[0.5, 0.0]} end={[0.5, 1.0]} />
    </EffectComposer>
  );
}
