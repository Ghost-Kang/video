// Maps backend RewriteResult.shots → frontend RewriteShot[] for CardStack rendering.

export interface RewriteShot {
  shot_index: number;
  dialogue: string;
  visual: string;
}

export function mapRewriteShotsToScenes(shots: RewriteShot[]): RewriteShot[] {
  return shots.map((shot) => ({
    shot_index: shot.shot_index,
    dialogue: shot.dialogue,
    visual: shot.visual,
  }));
}
