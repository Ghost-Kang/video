"""Generate 15 CascadeAnalysisContract fixtures (5 per niche) for P1-3 smoke tests.

Run once from repo root:
    cd backend && uv run python ../scripts/gen_rewrite_smoke_fixtures.py

Each fixture is a valid CascadeAnalysisContract — varies hook / scenes /
emotional_arc / replicable_formula so the rewrite is tested across diverse
inputs without requiring 15 real video URLs.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "backend" / "src" / "agent" / "cascade" / "fixtures" / "rewrite_smoke"


def scene(idx: int, start: float, end: float, scene: str, dialogue: str, visual: str,
          subject: str | None = None, shot_type: str = "medium",
          camera: str = "static") -> dict:
    return {
        "scene_index": idx,
        "timestamp_start": start,
        "timestamp_end": end,
        "scene": scene,
        "dialogue_and_narration": dialogue,
        "visual_content": visual,
        "subject": subject,
        "shot_type": shot_type,
        "camera_movement": camera,
        "first_frame_url": None,
        "warnings": [],
    }


def base_contract(*, niche: str, idx: int, hook: str, emotional_arc: str,
                  formula: str, scenes: list[dict], duration: int,
                  confidence: float = 0.86, model: str = "doubao-seed-2-0-pro",
                  cost: float = 0.42) -> dict:
    return {
        "_provenance": "rewrite_smoke_v1",
        "_niche": niche,
        "schema_version": "1.0",
        "analysis_id": f"ana_smk_{niche}_{idx:03d}",
        "source_url": f"https://www.douyin.com/video/smoke_{niche}_{idx:03d}",
        "platform": "douyin",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "cost_cny": cost,
        "duration_s": duration,
        "confidence": confidence,
        "viral_analysis": {
            "hook": hook,
            "pacing": "4-3-2 秒压缩,临近结尾镜头变短",
            "climax": "倒数第二镜情绪反转",
            "visual_style": "暖色调,家庭场景,自然光",
            "emotional_arc": emotional_arc,
            "target_audience": "目标人群明确,场景代入感强",
            "engagement_levers": "结尾抛问题诱导评论",
            "replicable_formula": formula,
        },
        "scenes": scenes,
        "warnings": [],
    }


# --- 宝妈辅食 (baomam_fushi) — 5 variants ---

BAOMAM_VARIANTS = [
    dict(
        idx=1,
        hook="开场 1.2 秒:宝宝撇头拒食 + 妈妈无奈表情",
        emotional_arc="焦虑 → 尝试 → 惊喜 → 成就",
        formula="悬念开场(拒食痛点) + 3 步解决(换花样) + 反差结尾(主动吃)",
        scenes=[
            scene(1, 0.0, 4.5, "宝宝在餐椅上撇头不吃胡萝卜泥",
                  "你家宝宝是不是也这样,怎么喂都不吃?",
                  "暖色俯拍,餐椅特写,橙色胡萝卜泥", subject="宝宝", shot_type="close_up"),
            scene(2, 4.5, 11.0, "妈妈在木砧板切苹果块",
                  "试试换成苹果,颜色更亮宝宝更感兴趣",
                  "暖色俯拍砧板,红苹果块", subject="妈妈"),
            scene(3, 11.0, 18.0, "蒸锅蒸苹果",
                  "蒸 8 分钟,又软又香",
                  "侧拍蒸锅,蒸汽中红苹果"),
            scene(4, 18.0, 28.0, "妈妈喂宝宝,宝宝张嘴",
                  "看,张嘴了!这一勺下去我眼泪都要出来",
                  "中景,妈妈手持勺子,宝宝张嘴接住", subject="妈妈"),
            scene(5, 28.0, 38.0, "宝宝抢勺子自己吃",
                  "我哭了。你家宝宝几个月开始抢勺子,评论区告诉我",
                  "宝宝面部特写,手抓勺子", subject="宝宝", shot_type="close_up",
                  camera="handheld"),
        ],
        duration=38,
    ),
    dict(
        idx=2,
        hook="开场 1.5 秒:妈妈打开冰箱皱眉,这周宝宝又不爱吃了",
        emotional_arc="迷茫 → 灵感 → 期待 → 满足",
        formula="痛点反复(总是不吃) + 1 个意外解法(把食材做成卡通形状) + 宝宝反应",
        scenes=[
            scene(1, 0.0, 3.5, "妈妈打开冰箱,菜没动",
                  "这周第三次了,做啥都不吃",
                  "中景,冰箱内景,妈妈背影", subject="妈妈"),
            scene(2, 3.5, 9.0, "把南瓜削成小熊形状",
                  "小熊南瓜,小朋友哪有不爱的",
                  "俯拍砧板,南瓜削皮特写"),
            scene(3, 9.0, 15.0, "蒸熟摆盘",
                  "8 分钟蒸熟,摆个笑脸",
                  "侧拍蒸笼,出锅特写"),
            scene(4, 15.0, 22.0, "宝宝盯着盘子",
                  "看见小熊了吗?",
                  "宝宝眼神特写", subject="宝宝", shot_type="close_up"),
            scene(5, 22.0, 30.0, "宝宝主动伸手抓",
                  "你家有没有这种'换个造型就吃'的瞬间",
                  "宝宝小手伸向盘子", subject="宝宝", camera="handheld"),
        ],
        duration=30,
    ),
    dict(
        idx=3,
        hook="开场 1 秒:妈妈疲惫旁白—又一次没吃完",
        emotional_arc="挫败 → 尝试 → 转折 → 解脱",
        formula="妈妈视角自述(我也不会) + 一个家常解法 + 一段独白",
        scenes=[
            scene(1, 0.0, 4.0, "厨房一片狼藉",
                  "做了一上午,还是没吃完",
                  "广角厨房,台面散乱"),
            scene(2, 4.0, 11.0, "妈妈坐下喘气",
                  "我也不是营养师,就想让他多吃一口",
                  "中景妈妈侧脸", subject="妈妈"),
            scene(3, 11.0, 17.0, "翻冰箱找剩饭",
                  "剩米饭加蛋,捏成饭团",
                  "俯拍砧板,饭团手部动作"),
            scene(4, 17.0, 24.0, "宝宝啃饭团",
                  "他居然吃完了,我都没敢相信",
                  "宝宝小手抓饭团特写", subject="宝宝", shot_type="close_up"),
            scene(5, 24.0, 32.0, "妈妈对镜头",
                  "有时候简单的反而好,你家也这样吗",
                  "妈妈对镜头中景", subject="妈妈"),
        ],
        duration=32,
    ),
    dict(
        idx=4,
        hook="开场 2 秒:宝宝把碗推翻,胡萝卜泥洒一桌",
        emotional_arc="崩溃 → 平静 → 智慧 → 成长",
        formula="冲突开场(强对抗) + 妈妈的退让(不喂了) + 宝宝主动",
        scenes=[
            scene(1, 0.0, 3.0, "碗被推翻,泥洒桌",
                  "我深呼吸三次",
                  "餐桌广角,胡萝卜泥洒落"),
            scene(2, 3.0, 9.0, "妈妈不喂了,自己吃别的",
                  "今天不喂了,你看妈妈吃",
                  "妈妈侧面端碗", subject="妈妈"),
            scene(3, 9.0, 16.0, "宝宝盯着妈妈的碗",
                  "他开始好奇了",
                  "宝宝眼神追随特写", subject="宝宝", shot_type="close_up"),
            scene(4, 16.0, 24.0, "宝宝伸手要",
                  "诶?自己想吃了?",
                  "宝宝小手伸向妈妈", subject="宝宝", camera="handheld"),
            scene(5, 24.0, 30.0, "母子一起吃",
                  "你家有没有'不追着喂就吃'的瞬间",
                  "母子餐桌中景", subject="妈妈"),
        ],
        duration=30,
    ),
    dict(
        idx=5,
        hook="开场 1.8 秒:钟表指着 7 点,妈妈端着夜奶",
        emotional_arc="疲惫 → 决心 → 尝试 → 释然",
        formula="时间压力(夜奶) + 一个新尝试(米糊换苹果) + 宝宝接受",
        scenes=[
            scene(1, 0.0, 4.0, "深夜厨房,妈妈端奶",
                  "夜奶喝到 1 岁了,试试换辅食",
                  "夜间厨房暖灯,妈妈侧影", subject="妈妈"),
            scene(2, 4.0, 10.0, "煮米糊加苹果泥",
                  "米糊里掺一点苹果泥",
                  "锅内特写,米糊冒泡"),
            scene(3, 10.0, 17.0, "测温度,贴手腕",
                  "凉到 37 度刚好",
                  "妈妈手部动作特写", subject="妈妈"),
            scene(4, 17.0, 25.0, "宝宝在小床喝米糊",
                  "他喝完了,翻身继续睡",
                  "宝宝睡颜侧面特写", subject="宝宝", shot_type="close_up"),
            scene(5, 25.0, 33.0, "妈妈靠床",
                  "你家是几岁戒夜奶的,评论区聊聊",
                  "妈妈对镜头自拍角度", subject="妈妈"),
        ],
        duration=33,
    ),
]


YUER_VARIANTS = [
    dict(
        idx=1,
        hook="开场 1 秒:妈妈在凌晨 3 点的卧室,娃又醒了",
        emotional_arc="疲惫 → 触动 → 治愈 → 自我和解",
        formula="深夜场景痛点 + 孩子一句话 + 妈妈独白治愈",
        scenes=[
            scene(1, 0.0, 4.0, "凌晨卧室,妈妈坐起",
                  "他又醒了,这是今晚第三次",
                  "夜灯昏黄,卧室广角"),
            scene(2, 4.0, 11.0, "妈妈轻拍娃",
                  "我快撑不住了",
                  "妈妈手轻拍娃后背特写", subject="妈妈"),
            scene(3, 11.0, 18.0, "娃小声说:妈妈在",
                  "他说了句'妈妈在',然后就睡了",
                  "娃睡颜侧面", subject="孩子", shot_type="close_up"),
            scene(4, 18.0, 26.0, "妈妈静静看着",
                  "原来他也在确认我在",
                  "妈妈侧脸特写", subject="妈妈"),
            scene(5, 26.0, 32.0, "妈妈对镜头",
                  "你被娃哪句话戳过,留言告诉我",
                  "自拍角度,妈妈对镜头", subject="妈妈"),
        ],
        duration=32,
    ),
    dict(
        idx=2,
        hook="开场 1.5 秒:大宝把奶给二宝,自己没喝",
        emotional_arc="震惊 → 心疼 → 骄傲 → 释然",
        formula="兄妹细节 + 大宝意外举动 + 妈妈感动",
        scenes=[
            scene(1, 0.0, 4.0, "大宝抱着奶瓶",
                  "我以为他要自己喝",
                  "客厅广角,大宝抱奶瓶"),
            scene(2, 4.0, 10.0, "大宝把奶递给二宝",
                  "他说'妹妹也要喝'",
                  "大宝小手递奶特写", subject="孩子", shot_type="close_up"),
            scene(3, 10.0, 16.0, "二宝喝奶,大宝在旁边",
                  "自己一口没喝",
                  "二宝喝奶中景"),
            scene(4, 16.0, 23.0, "妈妈给大宝倒水",
                  "我给他单独泡了一杯",
                  "妈妈倒水手部特写", subject="妈妈"),
            scene(5, 23.0, 30.0, "大宝喝水点头",
                  "你家大宝有没有'让着妹妹'的瞬间",
                  "大宝喝水中景", subject="妈妈"),
        ],
        duration=30,
    ),
    dict(
        idx=3,
        hook="开场 2 秒:妈妈崩溃到躲进厕所哭",
        emotional_arc="崩溃 → 自我对话 → 走出来 → 拥抱",
        formula="妈妈崩溃 + 内心独白 + 孩子靠近修复",
        scenes=[
            scene(1, 0.0, 3.5, "妈妈关厕所门",
                  "我今天真的撑不住了",
                  "厕所门外视角"),
            scene(2, 3.5, 10.0, "妈妈坐地上",
                  "当妈是不是都这样",
                  "妈妈侧脸暗光", subject="妈妈"),
            scene(3, 10.0, 16.0, "门外小手敲门",
                  "他不知道发生了什么",
                  "门缝小手特写", subject="孩子", shot_type="close_up"),
            scene(4, 16.0, 24.0, "妈妈开门抱住娃",
                  "原来你担心我",
                  "母子拥抱中景", subject="妈妈"),
            scene(5, 24.0, 30.0, "母子坐沙发",
                  "你家有没有'被孩子治愈'的瞬间",
                  "沙发中景", subject="妈妈"),
        ],
        duration=30,
    ),
    dict(
        idx=4,
        hook="开场 1 秒:娃的画里只有妈妈没有爸爸",
        emotional_arc="疑惑 → 心酸 → 理解 → 释然",
        formula="孩子作品的细节 + 父母解读 + 内心和解",
        scenes=[
            scene(1, 0.0, 3.5, "餐桌上一张画",
                  "他画了我们家",
                  "餐桌画作俯拍特写"),
            scene(2, 3.5, 9.0, "妈妈指画问",
                  "爸爸呢?他说爸爸在加班",
                  "妈妈手指画作特写", subject="妈妈"),
            scene(3, 9.0, 16.0, "晚上爸爸看到画",
                  "他笑了一下,没说话",
                  "爸爸侧脸暗光"),
            scene(4, 16.0, 24.0, "爸爸第二天请假回家",
                  "下周他请了三天假",
                  "客厅一家三口中景"),
            scene(5, 24.0, 30.0, "妈妈对镜头",
                  "你家有没有'孩子画里漏了谁'的瞬间",
                  "自拍角度", subject="妈妈"),
        ],
        duration=30,
    ),
    dict(
        idx=5,
        hook="开场 1.8 秒:娃在幼儿园门口不撒手",
        emotional_arc="挣扎 → 心疼 → 转折 → 成长",
        formula="入园分离焦虑 + 一个细节 + 妈妈反思",
        scenes=[
            scene(1, 0.0, 4.0, "幼儿园门口娃拽妈妈衣角",
                  "他第一天不肯进去",
                  "幼儿园门口广角"),
            scene(2, 4.0, 10.0, "妈妈蹲下来",
                  "我说'妈妈下午第一个来接你'",
                  "妈妈蹲下中景", subject="妈妈"),
            scene(3, 10.0, 17.0, "娃慢慢松手",
                  "他看了我三秒",
                  "娃手部松开特写", subject="孩子", shot_type="close_up"),
            scene(4, 17.0, 25.0, "妈妈躲到墙后哭",
                  "我躲到墙后才敢哭",
                  "妈妈侧影暗光", subject="妈妈"),
            scene(5, 25.0, 31.0, "下午接娃笑跑",
                  "你家娃第一天入园是什么样",
                  "幼儿园门口中景", subject="妈妈"),
        ],
        duration=31,
    ),
]


CHUFANG_VARIANTS = [
    dict(
        idx=1,
        hook="开场 1.2 秒:餐厅 88 元的菜,在家做花了 12",
        emotional_arc="好奇 → 上手 → 满足 → 小骄傲",
        formula="餐厅 vs 家庭对比 + 3 步操作 + 成品反差",
        scenes=[
            scene(1, 0.0, 3.5, "对比餐厅菜单照",
                  "餐厅卖 88,我猜成本不到 15",
                  "手机屏幕照特写"),
            scene(2, 3.5, 10.0, "切牛肉腌料",
                  "牛肉切片,生抽糖淀粉抓匀",
                  "俯拍砧板,牛肉特写"),
            scene(3, 10.0, 17.0, "热锅快炒",
                  "热锅冷油,30 秒变色",
                  "侧拍炒锅,火光特写"),
            scene(4, 17.0, 25.0, "装盘撒葱",
                  "出锅撒葱花,这卖相",
                  "成品装盘俯拍"),
            scene(5, 25.0, 32.0, "对镜头吃",
                  "餐厅 88 你猜成本多少,评论区告诉我",
                  "对镜头吃中景"),
        ],
        duration=32,
    ),
    dict(
        idx=2,
        hook="开场 2 秒:用电饭煲做整锅卤味",
        emotional_arc="疑问 → 验证 → 惊喜 → 推荐",
        formula="工具反差(电饭煲) + 简化流程 + 成品好评",
        scenes=[
            scene(1, 0.0, 3.5, "电饭煲掀盖",
                  "电饭煲能做卤味吗?",
                  "电饭煲俯拍特写"),
            scene(2, 3.5, 11.0, "码料汁",
                  "酱油老抽糖八角桂皮",
                  "调料碗俯拍"),
            scene(3, 11.0, 18.0, "鸡腿放进去",
                  "鸡腿戳几下入味",
                  "鸡腿手部特写"),
            scene(4, 18.0, 26.0, "煮饭键按下",
                  "煮饭键 + 保温 30 分钟",
                  "电饭煲按键特写"),
            scene(5, 26.0, 33.0, "开盖撕鸡腿",
                  "撕开你看,这汁",
                  "撕开成品特写"),
        ],
        duration=33,
    ),
    dict(
        idx=3,
        hook="开场 1.5 秒:厨房小白也能做的法式吐司",
        emotional_arc="紧张 → 上手 → 满足 → 自信",
        formula="新手友好定位 + 5 分钟操作 + 早餐场景",
        scenes=[
            scene(1, 0.0, 3.5, "鸡蛋牛奶打散",
                  "厨房小白也能做",
                  "搅拌碗俯拍"),
            scene(2, 3.5, 10.0, "面包浸蛋液",
                  "面包两面浸 10 秒",
                  "面包浸入特写"),
            scene(3, 10.0, 16.0, "小火煎",
                  "小火慢煎,别开大火",
                  "平底锅侧拍"),
            scene(4, 16.0, 23.0, "撒糖粉",
                  "出锅撒糖粉,挤蜂蜜",
                  "撒糖动作特写"),
            scene(5, 23.0, 30.0, "餐桌切开",
                  "周末早餐你做不做,评论区聊聊",
                  "餐桌切开特写"),
        ],
        duration=30,
    ),
    dict(
        idx=4,
        hook="开场 1.8 秒:不用烤箱也能做芝士拉丝",
        emotional_arc="挑战 → 操作 → 高潮 → 安利",
        formula="工具限制反向打 + 关键步骤 + 拉丝结尾",
        scenes=[
            scene(1, 0.0, 3.5, "厨房无烤箱",
                  "家里没烤箱怎么办",
                  "厨房广角"),
            scene(2, 3.5, 10.0, "土豆泥铺底",
                  "土豆泥铺一层",
                  "锅内俯拍"),
            scene(3, 10.0, 17.0, "撒芝士盖盖",
                  "芝士撒满,盖盖小火焖",
                  "撒芝士特写"),
            scene(4, 17.0, 25.0, "开盖拉丝",
                  "看,这拉丝",
                  "拉丝瞬间特写"),
            scene(5, 25.0, 32.0, "对镜头吃",
                  "这一锅成本不到 20,你做不做",
                  "对镜头吃中景"),
        ],
        duration=32,
    ),
    dict(
        idx=5,
        hook="开场 1 秒:一根黄瓜变三道菜",
        emotional_arc="好奇 → 节俭 → 创意 → 推荐",
        formula="一物多用 + 3 步变形 + 节俭主题",
        scenes=[
            scene(1, 0.0, 3.0, "一根黄瓜",
                  "一根黄瓜,我能做三道",
                  "黄瓜砧板俯拍"),
            scene(2, 3.0, 10.0, "拍黄瓜凉拌",
                  "拍碎拌蒜醋",
                  "拍黄瓜手部特写"),
            scene(3, 10.0, 17.0, "切片做小菜",
                  "切薄片加糖醋",
                  "切片砧板俯拍"),
            scene(4, 17.0, 24.0, "切丁炒鸡蛋",
                  "切丁炒蛋,一锅菜",
                  "炒锅侧拍"),
            scene(5, 24.0, 31.0, "三道菜上桌",
                  "你家黄瓜还有什么吃法,评论区分享",
                  "餐桌三盘菜俯拍"),
        ],
        duration=31,
    ),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    plans = [
        ("baomam_fushi", BAOMAM_VARIANTS),
        ("yuer_richang", YUER_VARIANTS),
        ("jiating_chufang", CHUFANG_VARIANTS),
    ]
    written = 0
    for niche, variants in plans:
        niche_dir = OUT / niche
        niche_dir.mkdir(parents=True, exist_ok=True)
        for v in variants:
            data = base_contract(niche=niche, **v)
            path = niche_dir / f"ref_{v['idx']:03d}.json"
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            written += 1
    print(f"wrote {written} fixtures to {OUT}")


if __name__ == "__main__":
    main()
