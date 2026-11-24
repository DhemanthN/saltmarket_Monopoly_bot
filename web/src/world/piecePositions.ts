import { Vector3 } from "three";

/** World position of each seat's piece. `Pieces` writes it every frame; the camera rig reads it. */
export const piecePositions: Vector3[] = [0, 1, 2, 3].map(() => new Vector3());
