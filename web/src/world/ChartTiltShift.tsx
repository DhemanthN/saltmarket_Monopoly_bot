import { EffectComposer, TiltShift2 } from "@react-three/postprocessing";

/** Tilt-shift blur for chart view on the high tier only: the atoll reads as a model on a table. */
export default function ChartTiltShift() {
  return (
    <EffectComposer multisampling={0}>
      <TiltShift2 blur={0.18} taper={0.6} start={[0.5, 0.0]} end={[0.5, 1.0]} />
    </EffectComposer>
  );
}
