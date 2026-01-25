import os
import re
import time
import random
import asyncio
import math
from dataclasses import dataclass
from typing import Optional, Tuple, Dict

import aiosqlite
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message

# ----------------------------
# 配置
# ----------------------------
DB_PATH = "data/mushenji.sqlite3"
PREFIX = "."

# 闭关冷却：10-15分钟（规格书）
TRAIN_CD_MIN = 10 * 60
TRAIN_CD_MAX = 15 * 60

# 深度闭关：8小时；冷却22小时（规格书）
DEEP_DURATION = 8 * 60 * 60
DEEP_COOLDOWN = 22 * 60 * 60

# 被动修为：每人每60秒最多+1，且消息长度>=6（强限流，防刷屏）
PASSIVE_CD = 60
PASSIVE_MIN_LEN = 6
PASSIVE_GAIN = 1

# 一些基础丹药（用于MVP测试；后续你可以完全换成模板里的物品体系）
PILLS: Dict[str, dict] = {
    "聚气丹": {"exp": 120, "min_tier": 0, "min_stage": 1},
    "清灵丹": {"exp": 0, "min_tier": 0, "min_stage": 1, "clear_toxic": True},
}

# 灵体示例（后续你可以按模板更细化）
LINGTI_POOL = [
    ("青龙灵体", 24.9),
    ("朱雀灵体", 24.9),
    ("白虎灵体", 24.9),
    ("玄武灵体", 24.9),
    ("霸体", 0.4),
]

DAOHAO_PREFIX = [
    "赵", "钱", "孙", "李", "周", "吴", "郑", "王",
    "冯", "陈", "褚", "卫", "蒋", "沈", "韩", "杨",
    "朱", "秦", "尤", "许", "何", "吕", "施", "张",
    "孔", "曹", "严", "华", "金", "魏", "陶", "姜",
    "谢", "邹", "喻", "柏", "窦", "章", "云", "苏",
    "潘", "葛", "范", "彭", "鲁", "韦", "马", "袁", "柳",
    "欧阳", "司马", "诸葛", "上官", "夏侯", "东方",
    "皇甫", "尉迟", "公孙", "慕容", "令狐", "长孙"
]

DAOHAO_SUFFIX = [
    "玄", "清", "明", "晟", "昱", "曜", "朗", "昭",
    "宁", "安", "定", "和", "平",
    "然", "修", "远", "达", "弘", "毅", "诚", "义",
    "衡", "正", "元", "钧", "翊",
    "云", "风", "霖", "泽", "渊", "川", "岳", "松",
    "宸", "轩", "卿", "昊", "辰",
    "瑾", "瑜", "珩", "璟", "子安", "子渊", "子墨", "子卿", "子游", "子期",
    "伯言", "伯安", "仲卿", "仲文", "叔和", "季明",
    "景行", "景曜", "景元", "景尧", "景鸿",
    "承安", "承泽", "承霖", "怀瑾", "怀玉",
    "明远", "明哲", "明修", "明轩",
    "清和", "清扬", "玄同", "玄策",
    "修远", "修文", "修然", "修竹",
    "元礼", "元正", "元朗", "元恺",
    "云舟", "云深", "云起", "云岚",
    "逸仙", "逸尘", "逸风", "逸然",
    "若水", "若尘", "若虚", "若川",
    "澄明", "澄心", "澄一"
]

REALM_TIERS = ["灵胎", "五曜", "六合", "七星", "天人","生死","神桥"]  # MVP占位
STAGES_PER_TIER = 3


# ----------------------------
# DB
# ----------------------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS player (
  user_id INTEGER PRIMARY KEY,
  nick TEXT,
  daohao TEXT,
  lingti TEXT,
  tier INTEGER DEFAULT 0,
  stage INTEGER DEFAULT 1,
  exp INTEGER DEFAULT 0,
  stone INTEGER DEFAULT 0,

  train_ready_ts INTEGER DEFAULT 0,

  deep_active INTEGER DEFAULT 0,
  deep_start_ts INTEGER DEFAULT 0,
  deep_end_ts INTEGER DEFAULT 0,
  deep_next_ts INTEGER DEFAULT 0,

  passive_ready_ts INTEGER DEFAULT 0,

  toxic_points INTEGER DEFAULT 0,
  last_pill_name TEXT DEFAULT '',
  last_pill_ts INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS inv (
  user_id INTEGER,
  item TEXT,
  qty INTEGER,
  PRIMARY KEY (user_id, item)
);
"""


async def db_init():
    os.makedirs("data", exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()


async def get_player(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT * FROM player WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        return row


async def create_player(user_id: int, nick: str, daohao: str, lingti: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO player(user_id,nick,daohao,lingti,tier,stage,exp,stone) VALUES(?,?,?,?,0,1,0,0)",
            (user_id, nick, daohao, lingti),
        )
        # 初始发一点丹药用于测试
        await db.execute("INSERT OR IGNORE INTO inv(user_id,item,qty) VALUES(?,?,?)", (user_id, "聚气丹", 3))
        await db.execute("INSERT OR IGNORE INTO inv(user_id,item,qty) VALUES(?,?,?)", (user_id, "清灵丹", 1))
        await db.commit()


async def set_player_field(user_id: int, **fields):
    keys = list(fields.keys())
    vals = list(fields.values())
    sets = ",".join([f"{k}=?" for k in keys])
    sql = f"UPDATE player SET {sets} WHERE user_id=?"
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(sql, (*vals, user_id))
        await db.commit()


async def add_exp(user_id: int, delta: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE player SET exp = exp + ? WHERE user_id=?", (delta, user_id))
        await db.commit()


async def inv_get_all(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT item, qty FROM inv WHERE user_id=? ORDER BY item", (user_id,))
        return await cur.fetchall()


async def inv_get(user_id: int, item: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT qty FROM inv WHERE user_id=? AND item=?", (user_id, item))
        row = await cur.fetchone()
        return int(row[0]) if row else 0


async def inv_add(user_id: int, item: str, delta: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO inv(user_id,item,qty) VALUES(?,?,?) "
            "ON CONFLICT(user_id,item) DO UPDATE SET qty = qty + excluded.qty",
            (user_id, item, delta),
        )
        # 防止负数
        await db.execute("UPDATE inv SET qty=0 WHERE user_id=? AND item=? AND qty<0", (user_id, item))
        await db.commit()


# ----------------------------
# 业务逻辑（MVP版）
# ----------------------------
def weighted_choice(pool):
    total = sum(w for _, w in pool)
    r = random.uniform(0, total)
    upto = 0
    for item, w in pool:
        if upto + w >= r:
            return item
        upto += w
    return pool[-1][0]


def gen_daohao() -> str:
    return random.choice(DAOHAO_PREFIX) + random.choice(DAOHAO_SUFFIX)


PHASE_CAP_BASE = {1: 500, 2: 1500, 3: 3000}
TIER_GROWTH = 8  # 必须 >6，保证“上一境界后期 < 下一境界前期”

def stage_to_phase(stage: int) -> str:
    return "前期" if stage == 1 else ("中期" if stage == 2 else "后期")

def phase_cap(tier: int, stage: int) -> int:
    return PHASE_CAP_BASE[stage] * (TIER_GROWTH ** tier)

def tier_total(tier: int) -> int:
    return sum(PHASE_CAP_BASE[s] for s in (1, 2, 3)) * (TIER_GROWTH ** tier)

def tier_offset(tier: int) -> int:
    # 之前所有境界的总需求，用于全局累计 exp
    return sum(tier_total(i) for i in range(tier))

def phase_start_total(tier: int, stage: int) -> int:
    # 当前阶段在“全局累计 exp”中的起点
    off = tier_offset(tier)
    if stage == 1:
        return off
    if stage == 2:
        return off + phase_cap(tier, 1)
    return off + phase_cap(tier, 1) + phase_cap(tier, 2)

def exp_view_in_phase(exp_total: int, tier: int, stage: int) -> tuple[int, int]:
    # 返回 (阶段内当前显示值, 阶段内上限)
    start = phase_start_total(tier, stage)
    cap = phase_cap(tier, stage)
    return max(0, exp_total - start), cap


def realm_name(tier: int, stage: int) -> str:
    tier = max(0, min(tier, len(REALM_TIERS) - 1))
    stage = max(1, min(stage, STAGES_PER_TIER))
    return f"{REALM_TIERS[tier]}{stage_to_phase(stage)}"

def stage_threshold(tier: int, stage: int) -> int:
    """
    返回“推进到下一阶段所需的全局累计修为阈值”
    stage=1：达到前期满 -> 进入中期
    stage=2：达到中期满 -> 进入后期
    stage=3：达到后期满 -> 进入下一境界前期
    """
    stage = max(1, min(stage, STAGES_PER_TIER))
    return phase_start_total(tier, stage) + phase_cap(tier, stage)


async def maybe_rank_up(user_id: int):
    p = await get_player(user_id)
    if not p:
        return
    # row layout matches schema order; quick index mapping
    exp = p[6]
    tier = p[4]
    stage = p[5]

    # 可能连升多级
    upgraded = False
    while tier < len(REALM_TIERS):
        need = stage_threshold(tier, stage)
        if exp >= need:
            upgraded = True
            stage += 1
            if stage > STAGES_PER_TIER:
                tier += 1
                stage = 1
        else:
            break

    if upgraded:
        await set_player_field(user_id, tier=tier, stage=stage)


def parse_cmd(text: str) -> Optional[Tuple[str, str]]:
    if not text:
        return None
    t = text.strip()
    if not t.startswith(PREFIX):
        return None
    body = t[1:].strip()
    if not body:
        return ("帮助", "")
    # cmd 为第一个空格前；后面是参数原串
    parts = body.split(maxsplit=1)
    cmd = parts[0]
    rest = parts[1] if len(parts) > 1 else ""
    return (cmd, rest)


def parse_item_qty(spec: str) -> Tuple[str, int]:
    """
    支持：
      .服用 聚气丹*2
      .服用 聚气丹 2
    """
    s = spec.strip()
    if "*" in s:
        name, qty = s.split("*", 1)
        name = name.strip()
        qty = int(qty.strip())
        return name, qty
    m = re.match(r"^(.+?)\s+(\d+)$", s)
    if m:
        return m.group(1).strip(), int(m.group(2))
    # 默认数量1
    return s, 1


def apply_toxicity_effect(toxic_points: int) -> Tuple[float, float]:
    """
    返回 (收益倍率, 成功率修正) —— 只是MVP默认值，你后续可按模板细化
    模板只说“丹毒影响闭关收益和炼制成功率”，没给具体公式，所以这里给可调实现。
    """
    gain_mul = max(0.5, 1.0 - 0.08 * toxic_points)
    success_penalty = min(0.25, 0.03 * toxic_points)  # 最多降低25%
    return gain_mul, success_penalty


async def do_train(user_id: int) -> str:
    p = await get_player(user_id)
    if not p:
        return "你尚未入道，请先发送 .检测灵体。"

    now = int(time.time())
    train_ready_ts = p[8]
    if now < train_ready_ts:
        left = train_ready_ts - now
        return f"灵气尚未平复，无法立即再次闭关。请在 {left//60}分{left%60}秒 后再试。"

    tier, stage, exp = p[4], p[5], p[6]
    toxic_points = p[14]

    # 基础收益：境界越高越大（符合模板描述）
    base = 40 + tier * 35 + stage * 6 + random.randint(0, 20)

    gain_mul, success_penalty = apply_toxicity_effect(toxic_points)
    base = int(base * gain_mul)

    # 三种结果：成功 / 失败 / 走火入魔（模板描述）
    success_rate = 0.72 - success_penalty
    devil_rate = 0.06 + min(0.10, 0.01 * toxic_points)  # 丹毒高更容易出事（可调）
    r = random.random()

    delta = 0
    extra = ""
    if r < devil_rate:
        # 走火入魔：扣一点修为
        delta = -max(10, base // 2)
        extra = "走火入魔！道心震荡，修为受损。"
    elif r < devil_rate + (1 - devil_rate) * (1 - success_rate):
        # 失败：小收益
        delta = max(5, base // 5)
        extra = "闭关受阻，收效甚微。"
    else:
        # 成功：大收益
        delta = base
        extra = "吐纳有成，灵气入体！"
        # 奇遇（模板描述“有几率触发奇遇”）
        if random.random() < 0.08:
            bonus = random.randint(30, 120)
            delta += bonus
            extra += f"\n奇遇触发：额外获得修为 {bonus} 点。"
            # 小概率掉落1颗聚气丹（示例）
            if random.random() < 0.25:
                await inv_add(user_id, "聚气丹", 1)
                extra += "\n你在奇遇中得了一枚【聚气丹】。"

    await add_exp(user_id, delta)
    await maybe_rank_up(user_id)

    # 设置下一次随机冷却 10-15分钟（模板描述）
    cd = random.randint(TRAIN_CD_MIN, TRAIN_CD_MAX)
    await set_player_field(user_id, train_ready_ts=now + cd)

    p2 = await get_player(user_id)
tier2, stage2, exp2 = p2[4], p2[5], p2[6]

cur_in_phase, cap_in_phase = exp_view_in_phase(exp2, tier2, stage2)
mins = (cd + 59) // 60

return (
    f"{extra}\n"
    f"本次修为变化：{delta:+d}\n"
    f"当前境界：{realm_name(tier2, stage2)}\n"
    f"当前修为：{cur_in_phase}/{cap_in_phase}\n"
    f"你感到一阵疲惫，需要打坐调息{mins}分钟方可再次闭关。"
)

async def start_deep(user_id: int) -> str:
    p = await get_player(user_id)
    if not p:
        return "你尚未入道，请先发送 .检测灵体。"
    now = int(time.time())
    if p[9] == 1:
        return "你正在深度闭关中，可发送 .查看闭关 查看剩余时间。"
    if now < p[12]:
        left = p[12] - now
        return f"今日机缘已尽，尚需 {left//3600}小时{(left%3600)//60}分钟 才可再次深度闭关。"

    await set_player_field(
        user_id,
        deep_active=1,
        deep_start_ts=now,
        deep_end_ts=now + DEEP_DURATION,
        deep_next_ts=now + DEEP_COOLDOWN,
    )
    return "已开启【深度闭关】（8小时）。结束后，下次发言/指令将自动结算。"


async def deep_status(user_id: int) -> str:
    p = await get_player(user_id)
    if not p:
        return "你尚未入道，请先发送 .检测灵体。"
    if p[9] != 1:
        return "你当前未在深度闭关中。"
    now = int(time.time())
    left = max(0, p[11] - now)
    return f"深度闭关剩余：{left//3600}小时{(left%3600)//60}分钟{left%60}秒。"


def simulate_one_train(tier: int, stage: int, toxic_points: int) -> int:
    base = 35 + tier * 30 + stage * 5 + random.randint(0, 18)
    gain_mul, success_penalty = apply_toxicity_effect(toxic_points)
    base = int(base * gain_mul)

    success_rate = 0.72 - success_penalty
    devil_rate = 0.06 + min(0.10, 0.01 * toxic_points)

    r = random.random()
    if r < devil_rate:
        return -max(8, base // 2)
    elif r < devil_rate + (1 - devil_rate) * (1 - success_rate):
        return max(4, base // 5)
    else:
        return base


async def settle_deep_if_due(msg: Message) -> Optional[str]:
    if not msg.from_user:
        return None
    user_id = msg.from_user.id
    p = await get_player(user_id)

    # deep_active 在索引 9
    if not p or p[9] != 1:
        return None

    now = int(time.time())
    end_ts = p[11]  # deep_end_ts 在索引 11
    if now < end_ts:
        return None

    tier, stage = p[4], p[5]
    toxic_points = p[14]  # toxic_points 在索引 14

    loops = random.randint(36, 42)
    total = 0
    for _ in range(loops):
        total += simulate_one_train(tier, stage, toxic_points)

    await add_exp(user_id, total)
    await maybe_rank_up(user_id)

    # 结算完关闭深度闭关
    await set_player_field(user_id, deep_active=0, deep_start_ts=0, deep_end_ts=0)

    p2 = await get_player(user_id)
    return f"【深度闭关结算】模拟闭关 {loops} 次，修为变化：{total:+d}\n当前境界：{realm_name(p2[4], p2[5])}"


async def force_end_deep(user_id: int) -> str:
    p = await get_player(user_id)
    if not p:
        return "你尚未入道，请先发送 .检测灵体。"
    if p[9] != 1:
        return "你当前未在深度闭关中。"

    now = int(time.time())
    start_ts = p[10]
    end_ts = p[11]
    tier, stage = p[4], p[5]
    toxic_points = p[14]

    elapsed = max(0, min(now, end_ts) - start_ts)
    ratio = max(0.05, elapsed / DEEP_DURATION)

    loops = max(3, int(ratio * random.randint(36, 42)))
    total = 0
    for _ in range(loops):
        total += simulate_one_train(tier, stage, toxic_points)

    # 强行出关：收益大打折扣（模板描述）
    total = int(total * 0.30)

    await add_exp(user_id, total)
    await maybe_rank_up(user_id)
    await set_player_field(user_id, deep_active=0, deep_start_ts=0, deep_end_ts=0)

    p2 = await get_player(user_id)
    return f"你强行出关，收益大打折扣。\n结算：模拟 {loops} 次，修为变化：{total:+d}\n当前境界：{realm_name(p2[4], p2[5])}"


async def do_passive(msg: Message):
    if not msg.from_user:
        return
    # 仅群聊/超级群生效
    if msg.chat.type not in ("group", "supergroup"):
        return
    text = msg.text or ""
    if len(text.strip()) < PASSIVE_MIN_LEN:
        return
    if text.strip().startswith(PREFIX):
        return  # 指令不算

    user_id = msg.from_user.id
    p = await get_player(user_id)
    if not p:
        return  # 未建号不加

    now = int(time.time())
    if now < p[13]:
        return

    await add_exp(user_id, PASSIVE_GAIN)
    await set_player_field(user_id, passive_ready_ts=now + PASSIVE_CD)
    await maybe_rank_up(user_id)


# ----------------------------
# 指令处理
# ----------------------------
async def handle_cmd(msg: Message, cmd: str, rest: str) -> Optional[str]:
    if not msg.from_user:
        return None
    user_id = msg.from_user.id
    nick = msg.from_user.full_name or "道友"

    if cmd == "帮助":
        return (
            "基础指令（全部以 . 开头）：\n"
            ".检测灵体\n"
            ".我的灵体\n"
            ".闭关修炼\n"
            ".深度闭关 / .查看闭关 / .强行出关\n"
            ".储物袋\n"
            ".服用 丹药名*数量\n"
        )

    if cmd == "检测灵体":
        p = await get_player(user_id)
        if p:
            return "你已检测过灵体，可发送 .我的灵体 查看档案。"
        daohao = gen_daohao()
        lingti = weighted_choice(LINGTI_POOL)
        await create_player(user_id, nick, daohao, lingti)
        return f"天机显化：道友\n先天灵体：{lingti}\n已入仙途：{realm_name(0,1)}\n可发送 .闭关修炼 开始修行。"

    if cmd == "我的灵体":
        p = await get_player(user_id)
        if not p:
            return "你尚未入道，请先发送 .检测灵体。"
        cur_in_phase, cap_in_phase = exp_view_in_phase(p[6], p[4], p[5])
        return (
            f"道友：{p[1]}\n道号：{p[2]}\n灵体：{p[3]}\n"
            f"境界：{realm_name(p[4], p[5])}\n当前修为：{cur_in_phase}/{cap_in_phase}\n灵石：{p[7]}\n"
        )


    if cmd == "闭关修炼":
        return await do_train(user_id)

    if cmd == "深度闭关":
        return await start_deep(user_id)

    if cmd == "查看闭关":
        return await deep_status(user_id)

    if cmd == "强行出关":
        return await force_end_deep(user_id)

    if cmd == "储物袋":
        p = await get_player(user_id)
        if not p:
            return "你尚未入道，请先发送 .检测灵体。"
        items = await inv_get_all(user_id)
        if not items:
            return "储物袋空空如也。"
        lines = ["储物袋："]
        for it, qty in items:
            if qty > 0:
                lines.append(f"- {it} × {qty}")
        return "\n".join(lines)

    if cmd == "服用":
        p = await get_player(user_id)
        if not p:
            return "你尚未入道，请先发送 .检测灵体。"
        if not rest.strip():
            return "用法：.服用 丹药名*数量  （例如：.服用 聚气丹*2）"
        name, qty = parse_item_qty(rest)
        qty = max(1, qty)

        have = await inv_get(user_id, name)
        if have < qty:
            return f"储物袋中不足（拥有 {have}）。"

        pill = PILLS.get(name)
        if not pill:
            return f"未知丹药：{name}（MVP仅内置：{', '.join(PILLS.keys())}）"

        tier, stage = p[4], p[5]
        if (tier < pill["min_tier"]) or (tier == pill["min_tier"] and stage < pill["min_stage"]):
            return f"境界不足，无法承受药力。"

        # 扣库存
        await inv_add(user_id, name, -qty)

        now = int(time.time())
        toxic_points = p[14]
        last_name = p[15]
        last_ts = p[16]

        if pill.get("clear_toxic"):
            await set_player_field(user_id, toxic_points=0, last_pill_name="", last_pill_ts=0)
            return "清灵丹入腹，丹毒尽消，道心澄明。"

        # 同类丹药24小时内连续服用→丹毒累积（模板描述）
        if last_name == name and (now - last_ts) <= 24 * 60 * 60:
            toxic_points += qty
        else:
            toxic_points = qty  # 新起一轮同类丹药

        await set_player_field(user_id, toxic_points=toxic_points, last_pill_name=name, last_pill_ts=now)

        gain = pill["exp"] * qty
        await add_exp(user_id, gain)
        await maybe_rank_up(user_id)

        p2 = await get_player(user_id)
        return f"服用×{qty}，修为 +{gain}。\n当前境界：{realm_name(p2[4], p2[5])}\n丹毒层数：{toxic_points}"

    return None


# ----------------------------
# Bot
# ----------------------------
async def main():
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("缺少 TELEGRAM_BOT_TOKEN")

    await db_init()

    bot = Bot(token=token)
    dp = Dispatcher()

    @dp.message(F.text)
    async def on_text(msg: Message):
        # 深度闭关到期自动结算（模板描述）
        settled = await settle_deep_if_due(msg)
        if settled:
            await msg.reply(settled)

        # 解析 .指令
        parsed = parse_cmd(msg.text or "")
        if parsed:
            cmd, rest = parsed
            res = await handle_cmd(msg, cmd, rest)
            if res:
                await msg.reply(res)
            else:
                await msg.reply("未知指令。发送 .帮助 查看可用指令。")
            return

        # 被动修为（模板描述：群内有效发言自动增加微量修为）
        await do_passive(msg)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

