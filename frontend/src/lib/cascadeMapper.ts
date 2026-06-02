// Maps backend RewriteResult.shots → frontend RewriteShot[] for CardStack rendering.

export interface RewriteShot {
  shot_index: number;
  dialogue: string;
  visual: string;
  // 生成草稿图 leg:首帧图 URL,由 WS 帧 shot_first_frame_returned 打进 store(初始 undefined)。
  firstFrameUrl?: string;
  // 生成失败时后端在同一帧带 error(用户向友好提示)→ 该镜头即时翻到「失败/重试」,
  // 不必等前端 75s 超时。成功或重试时清空。
  firstFrameError?: string;
}

export function mapRewriteShotsToScenes(shots: RewriteShot[]): RewriteShot[] {
  return shots.map((shot) => ({
    shot_index: shot.shot_index,
    dialogue: shot.dialogue,
    visual: shot.visual,
  }));
}
