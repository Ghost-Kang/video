// Maps backend RewriteResult.shots → frontend RewriteShot[] for CardStack rendering.

export interface RewriteShot {
  shot_index: number;
  dialogue: string;
  visual: string;
  // 生成草稿图 leg:首帧图 URL,由 WS 帧 shot_first_frame_returned 打进 store(初始 undefined)。
  // 组件据此渲染图;PENDING/FAILED 是组件本地瞬态(见 RewriteShotCard)。
  firstFrameUrl?: string;
}

export function mapRewriteShotsToScenes(shots: RewriteShot[]): RewriteShot[] {
  return shots.map((shot) => ({
    shot_index: shot.shot_index,
    dialogue: shot.dialogue,
    visual: shot.visual,
  }));
}
