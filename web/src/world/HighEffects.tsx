import { Bloom, EffectComposer, TiltShift2, ToneMapping } from "@react-three/postprocessing";
import { ToneMappingMode } from "postprocessing";

/**
 * High tier only, loaded lazily. Bloom with a threshold of 1.0 catches only what shines above
 * white: night windows and lanterns (`GLOW_INTENSITY`) and the flare. Chart view adds the
 * tilt-shift blur, so the atoll reads as a model on a table. The composer renders to a float
 * buffer, which skips the renderer's tone mapping, so ACES runs here as the last effect: the
 * High tier keeps the same ACES look as Medium and Low. The HUD is HTML and never tone mapped.
 */
export default function HighEffects({ chart }: { chart: boolean }) {
  return (
    <EffectComposer multisampling={0}>
      <Bloom mipmapBlur luminanceThreshold={1} luminanceSmoothing={0.15} intensity={0.85} radius={0.6} />
      {chart ? <TiltShift2 blur={0.07} taper={0.85} start={[0.5, 0.0]} end={[0.5, 1.0]} /> : <></>}
      <ToneMapping mode={ToneMappingMode.ACES_FILMIC} />
    </EffectComposer>
  );
}
