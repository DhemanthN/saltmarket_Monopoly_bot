import { PerspectiveCamera, Vector3 } from "three";
import { LOT_RADIUS } from "./layout";

export const CHART_POSITION = new Vector3(0, 30, 21);
export const CHART_TARGET = new Vector3(0, 0, 0.5);
/** Chart view backs off until the whole ring, lots and rooftops included, sits inside this share of the open frame. */
const CHART_FILL = 0.94;
const CHART_REACH = LOT_RADIUS + 0.9;
const CHART_ROOF = 2.2;
const CHART_BACK = CHART_POSITION.clone().sub(CHART_TARGET);
const CHART_NEAREST = CHART_BACK.length();
export const CHART_DIR = CHART_BACK.clone().normalize();

const RING_SAMPLES = 24;

/**
 * Distance from the chart target at which the ring fits the frame the HUD leaves open: the full
 * width, and the height above `bottomInset`. Found by testing a probe camera, so it holds for any
 * aspect ratio and field of view. Never closer than the default chart pose.
 */
export function chartDistance(width: number, height: number, bottomInset: number, fov: number): number {
  const probe = new PerspectiveCamera(fov, width / height, 0.3, 400);
  const open = Math.max(0.3, (height - bottomInset) / height);
  const point = new Vector3();
  const fits = (distance: number) => {
    probe.position.copy(CHART_TARGET).addScaledVector(CHART_DIR, distance);
    probe.lookAt(CHART_TARGET);
    probe.updateMatrixWorld();
    probe.updateProjectionMatrix();
    for (let i = 0; i < RING_SAMPLES; i += 1) {
      const a = (i / RING_SAMPLES) * Math.PI * 2;
      for (const y of [0, CHART_ROOF]) {
        point.set(Math.cos(a) * CHART_REACH, y, Math.sin(a) * CHART_REACH).project(probe);
        if (Math.abs(point.x) > CHART_FILL || Math.abs(point.y) > CHART_FILL * open) return false;
      }
    }
    return true;
  };
  let low = CHART_NEAREST;
  if (fits(low)) return low;
  let high = low * 4;
  for (let i = 0; i < 16; i += 1) {
    const mid = (low + high) / 2;
    if (fits(mid)) high = mid;
    else low = mid;
  }
  return high;
}

