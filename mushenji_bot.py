import os
import re
import time
import random
import asyncio
import math
import html
from dataclasses import dataclass
from typing import Optional, Tuple, Dict

import aiosqlite
from dotenv import load_dotenv
load_dotenv()
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message

# ----------------------------
# 配置
# ----------------------------
DB_PATH = "data/mushenji.sqlite3"
PREFIX = "."
ADMIN_USER_IDS = {
    int(uid)
    for uid in os.getenv("ADMIN_USER_IDS", "").split(",")
    if uid.strip().isdigit()
}

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

# 任务冷却（默认6小时）
TASK_COOLDOWN = 6 * 60 * 60

# 闭关掉落
TRAIN_LOOT_CHANCE = 0.12
DEEP_LOOT_CHANCE = 0.25
TRAIN_LOOT_POOL = [
    ("灵木", 35),
    ("星砂", 30),
    ("玄铁矿", 25),
    ("黑曜石", 20),
    ("灵泉露", 18),
    ("玄玉", 12),
    ("天蚕丝", 8),
    ("龙鳞", 4),
    ("四灵血", 2),
]

# 一些基础丹药（用于MVP测试；后续你可以完全换成模板里的物品体系）
PILLS: Dict[str, dict] = {
    "聚气丹": {"exp": 120, "min_tier": 0, "min_stage": 1, "price": 18, "desc": "聚拢灵气"},
    "培元丹": {"exp": 90, "min_tier": 0, "min_stage": 1, "price": 15, "desc": "稳固根基"},
    "凝元丹": {"exp": 220, "min_tier": 0, "min_stage": 2, "price": 38, "desc": "凝聚真元"},
    "化元丹": {"exp": 360, "min_tier": 0, "min_stage": 3, "price": 55, "desc": "化元提纯"},
    "金髓丹": {"exp": 260, "min_tier": 0, "min_stage": 2, "price": 42, "desc": "淬炼筋骨"},
    "灵台丹": {"exp": 520, "min_tier": 1, "min_stage": 1, "price": 90, "desc": "稳固灵台"},
    "玄灵丹": {"exp": 420, "min_tier": 1, "min_stage": 1, "price": 75, "desc": "引动玄灵"},
    "破境丹": {"exp": 900, "min_tier": 1, "min_stage": 3, "price": 180, "desc": "冲击瓶颈"},
    "回春丹": {"exp": 60, "min_tier": 0, "min_stage": 1, "price": 12, "desc": "回春养息"},
    "清心丹": {"exp": 0, "min_tier": 0, "min_stage": 1, "price": 30, "desc": "清心祛躁", "reduce_toxic": 1},
    "解厄丹": {"exp": 0, "min_tier": 0, "min_stage": 2, "price": 60, "desc": "化解丹毒", "reduce_toxic": 3},
    "洗髓丹": {"exp": 0, "min_tier": 0, "min_stage": 1, "price": 120, "desc": "洗练根骨", "clear_toxic": True},
    "归元丹": {"exp": 180, "min_tier": 0, "min_stage": 2, "price": 36, "desc": "回归元气"},
    "凝神丹": {"exp": 210, "min_tier": 0, "min_stage": 2, "price": 40, "desc": "凝神静气"},
    "养魂丹": {"exp": 260, "min_tier": 0, "min_stage": 3, "price": 58, "desc": "温养神魂"},
    "灵露丹": {"exp": 300, "min_tier": 0, "min_stage": 3, "price": 62, "desc": "灵露洗脉"},
    "九转培元丹": {"exp": 480, "min_tier": 1, "min_stage": 1, "price": 95, "desc": "九转培元"},
    "御风丹": {"exp": 140, "min_tier": 0, "min_stage": 1, "price": 22, "desc": "御风提速"},
    "雷纹丹": {"exp": 520, "min_tier": 1, "min_stage": 2, "price": 110, "desc": "雷纹护体"},
    "玄阳丹": {"exp": 600, "min_tier": 1, "min_stage": 2, "price": 130, "desc": "玄阳护脉"},
    "清虚丹": {"exp": 80, "min_tier": 0, "min_stage": 1, "price": 20, "desc": "清虚养息"},
    "玉华丹": {"exp": 320, "min_tier": 0, "min_stage": 3, "price": 70, "desc": "玉华润脉"},
    "金阳丹": {"exp": 680, "min_tier": 1, "min_stage": 3, "price": 150, "desc": "金阳炼体"},
    "冰魄丹": {"exp": 520, "min_tier": 1, "min_stage": 1, "price": 115, "desc": "冰魄凝心"},
    "归真丹": {"exp": 760, "min_tier": 2, "min_stage": 1, "price": 220, "desc": "归真复元"},
    "紫霞丹": {"exp": 840, "min_tier": 2, "min_stage": 2, "price": 260, "desc": "紫霞淬体"},
    "天罡丹": {"exp": 980, "min_tier": 2, "min_stage": 3, "price": 320, "desc": "天罡护体"},
    "灵息丹": {"exp": 240, "min_tier": 0, "min_stage": 2, "price": 45, "desc": "灵息护脉"},
    "云纹丹": {"exp": 360, "min_tier": 1, "min_stage": 1, "price": 88, "desc": "云纹凝气"},
    "丹心丹": {"exp": 420, "min_tier": 1, "min_stage": 1, "price": 92, "desc": "丹心守气"},
    "沉香丹": {"exp": 180, "min_tier": 0, "min_stage": 2, "price": 32, "desc": "沉香宁神"},
    "金露丹": {"exp": 500, "min_tier": 1, "min_stage": 2, "price": 105, "desc": "金露润脉"},
}

SUPER_RARE_PILLS: Dict[str, dict] = {
    "生死轮回丹": {"exp": 1800, "min_tier": 4, "min_stage": 1, "price": 2200, "desc": "轮回生死，重铸道基"},
    "太虚返命丹": {"exp": 1500, "min_tier": 3, "min_stage": 3, "price": 1800, "desc": "太虚归命，洗炼心神"},
    "神桥造化丹": {"exp": 2200, "min_tier": 5, "min_stage": 1, "price": 2600, "desc": "神桥造化，破境登阶"},
    "无相归墟丹": {"exp": 2000, "min_tier": 4, "min_stage": 2, "price": 2400, "desc": "无相归墟，真元归一"},
    "天道补天丹": {"exp": 2600, "min_tier": 5, "min_stage": 2, "price": 3200, "desc": "补天之力，天道洗礼"},
}

WEAPONS: Dict[str, dict] = {
    "飞星剑": {"atk": 26, "min_tier": 0, "price": 80, "desc": "青芒飞星"},
    "斩神刀": {"atk": 38, "min_tier": 0, "price": 120, "desc": "刀气凌冽"},
    "玄铁重剑": {"atk": 55, "min_tier": 1, "price": 260, "desc": "沉重如山"},
    "紫霄剑": {"atk": 72, "min_tier": 1, "price": 420, "desc": "紫霄雷纹"},
    "赤霄枪": {"atk": 90, "min_tier": 2, "price": 700, "desc": "赤霄烈焰"},
    "太虚神弓": {"atk": 120, "min_tier": 3, "price": 1200, "desc": "太虚裂空"},
    "青锋剑": {"atk": 22, "min_tier": 0, "price": 60, "desc": "剑光如青"},
    "玄冰剑": {"atk": 34, "min_tier": 0, "price": 110, "desc": "寒意逼人"},
    "赤炎刀": {"atk": 44, "min_tier": 1, "price": 180, "desc": "炎纹狂刀"},
    "紫电枪": {"atk": 58, "min_tier": 1, "price": 260, "desc": "紫电破空"},
    "玄影刺": {"atk": 48, "min_tier": 1, "price": 210, "desc": "影袭无声"},
    "龙纹戟": {"atk": 70, "min_tier": 2, "price": 520, "desc": "龙纹大戟"},
    "星河剑": {"atk": 82, "min_tier": 2, "price": 680, "desc": "星河流转"},
    "碧落刀": {"atk": 76, "min_tier": 2, "price": 600, "desc": "碧落寒光"},
    "玄羽弓": {"atk": 62, "min_tier": 1, "price": 300, "desc": "玄羽贯空"},
    "天璇剑": {"atk": 88, "min_tier": 2, "price": 720, "desc": "天璇曜芒"},
    "破军斧": {"atk": 96, "min_tier": 2, "price": 780, "desc": "破军开山"},
    "太一剑": {"atk": 130, "min_tier": 3, "price": 1400, "desc": "太一归元"},
    "玄霜枪": {"atk": 104, "min_tier": 3, "price": 1280, "desc": "玄霜破阵"},
    "赤霄刀": {"atk": 118, "min_tier": 3, "price": 1320, "desc": "赤霄焚天"},
    "天音琴刃": {"atk": 90, "min_tier": 2, "price": 760, "desc": "琴刃破心"},
    "白虹剑": {"atk": 58, "min_tier": 1, "price": 250, "desc": "白虹贯日"},
    "玄星锤": {"atk": 100, "min_tier": 3, "price": 1250, "desc": "星锤镇岳"},
    "天罡枪": {"atk": 112, "min_tier": 3, "price": 1350, "desc": "天罡破阵"},
    "流光刃": {"atk": 66, "min_tier": 1, "price": 280, "desc": "流光疾斩"},
    "九霄剑": {"atk": 140, "min_tier": 3, "price": 1500, "desc": "九霄凌云"},
}

LIMITED_WEAPONS: Dict[str, dict] = {
    "三公子的枪": {
        "atk": 180,
        "min_tier": 4,
        "price": 3800,
        "desc": "三公子执枪破阵，枪势贯天，主破甲与突阵",
        "use": "破阵突袭，压制护具",
    },
    "四公子的琴": {
        "atk": 165,
        "min_tier": 4,
        "price": 3600,
        "desc": "琴音摄魂，音律化刃，主控场与镇神",
        "use": "镇魂控场，削弱心神",
    },
    "七公子的剑": {
        "atk": 190,
        "min_tier": 5,
        "price": 4200,
        "desc": "剑光寒彻九州，七星剑势，主斩杀与追击",
        "use": "斩杀追击，剑意穿透",
    },
    "无涯道人的世界树": {
        "atk": 210,
        "min_tier": 5,
        "price": 4600,
        "desc": "世界树镇世，枝叶可化万兵，主镇压与护道",
        "use": "镇压领域，护道守阵",
    },
    "二公子的十六品莲台": {
        "atk": 200,
        "min_tier": 5,
        "price": 4400,
        "desc": "归墟之道化莲台，毁灭之力绽放，主吞噬与湮灭",
        "use": "归墟湮灭，崩坏万物",
    },
}

ARMORS: Dict[str, dict] = {
    "青木衣": {"def": 16, "min_tier": 0, "price": 60, "desc": "轻灵护体"},
    "玄铁甲": {"def": 32, "min_tier": 0, "price": 140, "desc": "玄铁护身"},
    "流火战甲": {"def": 55, "min_tier": 1, "price": 320, "desc": "火纹护体"},
    "玄鳞护心镜": {"def": 78, "min_tier": 2, "price": 620, "desc": "鳞甲护心"},
    "太虚道袍": {"def": 110, "min_tier": 3, "price": 980, "desc": "太虚护道"},
    "白虹甲": {"def": 20, "min_tier": 0, "price": 80, "desc": "白虹护身"},
    "玄鳞甲": {"def": 36, "min_tier": 0, "price": 160, "desc": "玄鳞覆体"},
    "飞云衣": {"def": 28, "min_tier": 0, "price": 120, "desc": "飞云轻灵"},
    "寒月披风": {"def": 40, "min_tier": 1, "price": 240, "desc": "寒月护体"},
    "赤炎护肩": {"def": 46, "min_tier": 1, "price": 260, "desc": "赤炎护肩"},
    "紫电甲": {"def": 58, "min_tier": 1, "price": 320, "desc": "紫电雷纹"},
    "玄霜战衣": {"def": 62, "min_tier": 2, "price": 420, "desc": "玄霜御寒"},
    "碧霞衣": {"def": 52, "min_tier": 1, "price": 300, "desc": "碧霞护身"},
    "星辰护甲": {"def": 70, "min_tier": 2, "price": 520, "desc": "星辰守护"},
    "天璇护甲": {"def": 74, "min_tier": 2, "price": 560, "desc": "天璇护体"},
    "破军战甲": {"def": 88, "min_tier": 2, "price": 680, "desc": "破军护身"},
    "青冥战甲": {"def": 82, "min_tier": 2, "price": 640, "desc": "青冥之力"},
    "玄光护甲": {"def": 90, "min_tier": 2, "price": 720, "desc": "玄光护身"},
    "归元道袍": {"def": 98, "min_tier": 3, "price": 820, "desc": "归元护体"},
    "金阳护甲": {"def": 108, "min_tier": 3, "price": 920, "desc": "金阳护体"},
    "太上云衣": {"def": 116, "min_tier": 3, "price": 1020, "desc": "太上云气"},
    "玄星法袍": {"def": 124, "min_tier": 3, "price": 1100, "desc": "玄星护道"},
    "天罡护甲": {"def": 130, "min_tier": 3, "price": 1180, "desc": "天罡护身"},
    "九霄战衣": {"def": 136, "min_tier": 3, "price": 1260, "desc": "九霄护体"},
    "青鸾羽衣": {"def": 96, "min_tier": 2, "price": 760, "desc": "青鸾护身"},
}

LIMITED_ARMORS: Dict[str, dict] = {
    "玄武帝甲": {"def": 150, "min_tier": 4, "price": 3600, "desc": "玄武护体，水寒不侵", "use": "抗寒抗冲击"},
    "朱雀霓裳": {"def": 142, "min_tier": 4, "price": 3400, "desc": "朱雀焰裳，烈火护身", "use": "抗火灼护体"},
    "白虎战铠": {"def": 160, "min_tier": 5, "price": 3800, "desc": "白虎战意，肃杀森然", "use": "提升杀伐抗压"},
    "青龙鳞衣": {"def": 156, "min_tier": 5, "price": 3700, "desc": "青龙鳞甲，风雷护身", "use": "抗雷风护体"},
    "太虚道衣": {"def": 168, "min_tier": 5, "price": 4000, "desc": "太虚护身，道意自成", "use": "道意护体，防御提升"},
}

ITEMS: Dict[str, dict] = {
    "灵木": {"rarity": "凡", "price": 6, "desc": "炼器辅材"},
    "玄铁矿": {"rarity": "玄", "price": 18, "desc": "炼器灵矿"},
    "星砂": {"rarity": "稀", "price": 80, "desc": "炼丹辅料"},
    "魂玉": {"rarity": "珍", "price": 180, "desc": "温养神魂"},
    "龙鳞": {"rarity": "珍", "price": 260, "desc": "护身奇材"},
    "妖丹": {"rarity": "珍", "price": 120, "desc": "妖兽精魄"},
    "玄金": {"rarity": "稀", "price": 150, "desc": "炼器主材"},
    "玄冰晶": {"rarity": "稀", "price": 140, "desc": "寒属性辅材"},
    "紫玉髓": {"rarity": "珍", "price": 240, "desc": "精纯灵髓"},
    "黑曜石": {"rarity": "玄", "price": 40, "desc": "护具炼材"},
    "赤金": {"rarity": "稀", "price": 90, "desc": "炼器主材"},
    "灵玉髓": {"rarity": "稀", "price": 110, "desc": "淬体灵髓"},
    "玄火晶": {"rarity": "稀", "price": 130, "desc": "火属性灵晶"},
    "星曜石": {"rarity": "珍", "price": 200, "desc": "星曜辅材"},
    "云纹石": {"rarity": "玄", "price": 50, "desc": "纹路炼材"},
    "雷晶": {"rarity": "稀", "price": 120, "desc": "雷属性晶核"},
    "天蚕丝": {"rarity": "珍", "price": 180, "desc": "炼衣灵丝"},
    "玄玉": {"rarity": "玄", "price": 70, "desc": "温润灵玉"},
    "幽冥砂": {"rarity": "稀", "price": 140, "desc": "幽冥辅材"},
    "金雷石": {"rarity": "珍", "price": 210, "desc": "金雷辅材"},
    "凤羽": {"rarity": "珍", "price": 260, "desc": "灵禽之羽"},
    "寒铁": {"rarity": "玄", "price": 60, "desc": "寒属性矿材"},
    "灵泉露": {"rarity": "凡", "price": 20, "desc": "灵泉凝露"},
    "幻灵晶": {"rarity": "稀", "price": 150, "desc": "幻灵晶石"},
    "星魄": {"rarity": "珍", "price": 230, "desc": "星魄精华"},
    "碧霞纱": {"rarity": "稀", "price": 110, "desc": "碧霞灵纱"},
    "玄星铁": {"rarity": "珍", "price": 240, "desc": "星铁主材"},
    "紫金砂": {"rarity": "稀", "price": 160, "desc": "紫金炼材"},
    "龙血晶": {"rarity": "珍", "price": 280, "desc": "龙血精晶"},
    "天罡石": {"rarity": "珍", "price": 260, "desc": "天罡灵石"},
    "四灵血": {"rarity": "传", "price": 520, "desc": "四灵真血，炼器炼丹奇材"},
}

RECIPES: Dict[str, dict] = {
    "凝元丹丹方": {"kind": "丹方", "target": "凝元丹", "tier": 0, "price": 120, "desc": "凝元引气"},
    "破境丹丹方": {"kind": "丹方", "target": "破境丹", "tier": 1, "price": 260, "desc": "破境冲关"},
    "玄灵丹丹方": {"kind": "丹方", "target": "玄灵丹", "tier": 1, "price": 220, "desc": "玄灵入体"},
    "飞星剑剑谱": {"kind": "武器方", "target": "飞星剑", "tier": 0, "price": 150, "desc": "星芒剑谱"},
    "玄铁重剑锻谱": {"kind": "武器方", "target": "玄铁重剑", "tier": 1, "price": 380, "desc": "重剑锻造"},
    "紫霄剑剑谱": {"kind": "武器方", "target": "紫霄剑", "tier": 1, "price": 460, "desc": "雷纹剑谱"},
    "青木衣护具方": {"kind": "护具方", "target": "青木衣", "tier": 0, "price": 130, "desc": "青木护衣"},
    "玄铁甲护具方": {"kind": "护具方", "target": "玄铁甲", "tier": 0, "price": 220, "desc": "玄铁护甲"},
    "流火战甲护具方": {"kind": "护具方", "target": "流火战甲", "tier": 1, "price": 420, "desc": "流火护甲"},
    "归元丹丹方": {"kind": "丹方", "target": "归元丹", "tier": 0, "price": 140, "desc": "归元炼制"},
    "凝神丹丹方": {"kind": "丹方", "target": "凝神丹", "tier": 0, "price": 150, "desc": "凝神入定"},
    "养魂丹丹方": {"kind": "丹方", "target": "养魂丹", "tier": 0, "price": 180, "desc": "养魂凝神"},
    "灵露丹丹方": {"kind": "丹方", "target": "灵露丹", "tier": 0, "price": 190, "desc": "灵露润脉"},
    "九转培元丹丹方": {"kind": "丹方", "target": "九转培元丹", "tier": 1, "price": 240, "desc": "九转培元"},
    "雷纹丹丹方": {"kind": "丹方", "target": "雷纹丹", "tier": 1, "price": 260, "desc": "雷纹凝丹"},
    "玄阳丹丹方": {"kind": "丹方", "target": "玄阳丹", "tier": 1, "price": 280, "desc": "玄阳炼体"},
    "玉华丹丹方": {"kind": "丹方", "target": "玉华丹", "tier": 0, "price": 200, "desc": "玉华炼制"},
    "金阳丹丹方": {"kind": "丹方", "target": "金阳丹", "tier": 1, "price": 300, "desc": "金阳淬体"},
    "冰魄丹丹方": {"kind": "丹方", "target": "冰魄丹", "tier": 1, "price": 260, "desc": "冰魄凝心"},
    "归真丹丹方": {"kind": "丹方", "target": "归真丹", "tier": 2, "price": 420, "desc": "归真化元"},
    "紫霞丹丹方": {"kind": "丹方", "target": "紫霞丹", "tier": 2, "price": 460, "desc": "紫霞炼体"},
    "天罡丹丹方": {"kind": "丹方", "target": "天罡丹", "tier": 2, "price": 520, "desc": "天罡凝丹"},
    "青锋剑剑谱": {"kind": "武器方", "target": "青锋剑", "tier": 0, "price": 170, "desc": "青锋剑谱"},
    "玄冰剑剑谱": {"kind": "武器方", "target": "玄冰剑", "tier": 0, "price": 190, "desc": "玄冰剑谱"},
    "赤炎刀刀谱": {"kind": "武器方", "target": "赤炎刀", "tier": 1, "price": 260, "desc": "赤炎刀谱"},
    "紫电枪枪谱": {"kind": "武器方", "target": "紫电枪", "tier": 1, "price": 280, "desc": "紫电枪谱"},
    "龙纹戟锻谱": {"kind": "武器方", "target": "龙纹戟", "tier": 2, "price": 420, "desc": "龙纹锻谱"},
    "星河剑剑谱": {"kind": "武器方", "target": "星河剑", "tier": 2, "price": 460, "desc": "星河剑谱"},
    "白虹甲护具方": {"kind": "护具方", "target": "白虹甲", "tier": 0, "price": 180, "desc": "白虹护甲"},
    "玄鳞甲护具方": {"kind": "护具方", "target": "玄鳞甲", "tier": 0, "price": 220, "desc": "玄鳞护甲"},
    "寒月披风护具方": {"kind": "护具方", "target": "寒月披风", "tier": 1, "price": 320, "desc": "寒月护具"},
    "紫电甲护具方": {"kind": "护具方", "target": "紫电甲", "tier": 1, "price": 340, "desc": "紫电护甲"},
    "星辰护甲护具方": {"kind": "护具方", "target": "星辰护甲", "tier": 2, "price": 480, "desc": "星辰护甲"},
    "九霄战衣护具方": {"kind": "护具方", "target": "九霄战衣", "tier": 3, "price": 680, "desc": "九霄护衣"},
}


def ensure_recipe_materials() -> None:
    for name, info in RECIPES.items():
        if info.get("mats"):
            continue
        kind = info["kind"]
        tier = info.get("tier", 0)
        mats = RECIPE_MATERIALS.get(kind, {}).get(tier)
        if mats:
            info["mats"] = mats


SUPER_RARE: Dict[str, dict] = {
    "混元天书": {"rarity": "限量", "price": 8800, "desc": "记载天道秘术"},
    "太虚残镜": {"rarity": "限量", "price": 7600, "desc": "映照太虚之力"},
    "九霄龙印": {"rarity": "限量", "price": 9800, "desc": "龙印镇世"},
    "玄冥古钟": {"rarity": "限量", "price": 10500, "desc": "玄冥镇魂"},
    "万象归一碑": {"rarity": "限量", "price": 12000, "desc": "万象归一"},
}

PILLS.update(SUPER_RARE_PILLS)
WEAPONS.update(LIMITED_WEAPONS)
ARMORS.update(LIMITED_ARMORS)

LIMITED_DEFAULT_STOCK = 10
LIMITED_ITEMS = {
    **{name: LIMITED_DEFAULT_STOCK for name in LIMITED_WEAPONS},
    **{name: LIMITED_DEFAULT_STOCK for name in LIMITED_ARMORS},
    **{name: LIMITED_DEFAULT_STOCK for name in SUPER_RARE},
}


def ensure_recipes() -> None:
    def has_recipe(kind: str, target: str) -> bool:
        return any(info["kind"] == kind and info["target"] == target for info in RECIPES.values())

    for name, pill in PILLS.items():
        if has_recipe("丹方", name):
            continue
        price = max(80, pill.get("price", 0) * 3)
        RECIPES[f"{name}丹方"] = {
            "kind": "丹方",
            "target": name,
            "tier": pill.get("min_tier", 0),
            "price": price,
            "desc": f"{name}炼制法门",
        }

    for name, info in WEAPONS.items():
        if has_recipe("武器方", name):
            continue
        price = max(200, int(info.get("price", 0) * 1.5))
        RECIPES[f"{name}锻谱"] = {
            "kind": "武器方",
            "target": name,
            "tier": info.get("min_tier", 0),
            "price": price,
            "desc": f"{name}锻造法门",
        }

    for name, info in ARMORS.items():
        if has_recipe("护具方", name):
            continue
        price = max(180, int(info.get("price", 0) * 1.4))
        RECIPES[f"{name}护具方"] = {
            "kind": "护具方",
            "target": name,
            "tier": info.get("min_tier", 0),
            "price": price,
            "desc": f"{name}护具法门",
        }


# 灵体示例（后续你可以按模板更细化）
LINGTI_POOL = [
    ("青龙灵体", 21.5),
    ("朱雀灵体", 21.5),
    ("白虎灵体", 21.5),
    ("玄武灵体", 21.5),
    ("日耀灵体", 6.0),
    ("月华灵体", 6.0),
    ("霸体", 1.5),
    ("剑心通明", 0.5),
]

LORE = {
    "世界观": [
        "大墟风沙如海，残老村的灯火却从未熄灭。",
        "延康皇朝方兴未艾，世间诸教暗流涌动。",
        "古神低语回荡在黑暗中，谁也说不清是福是祸。",
        "太虚深处偶现神桥残影，疑是上古遗泽。",
    ],
    "人物": [
        "有游侠踏入大墟，誓要解开古神之谜。",
        "有人自称来自延康，口口声声要重塑旧日秩序。",
    ],
    "势力": [
        "延康皇朝",
        "天道圣教",
        "残老村",
    ],
    "地名": [
        "大墟",
        "太虚",
        "延康",
    ],
    "传闻": [
        "旧日遗迹重现，传闻有神兵出世。",
        "黑暗中传来钟声，似在召唤沉睡的古神。",
        "有人在风沙中见到不该存在的城池。",
    ],
}

SECTS = {
    "延康皇朝": {"desc": "军阵炼体，重器道统", "starter_kind": "武器方"},
    "天道圣教": {"desc": "丹道传承，护道镇魂", "starter_kind": "丹方"},
    "残老村": {"desc": "隐世炼器，守护之道", "starter_kind": "护具方"},
}

RECIPE_MATERIALS = {
    "丹方": {
        0: [("星砂", 2), ("灵泉露", 1)],
        1: [("星砂", 3), ("玄玉", 1)],
        2: [("星砂", 4), ("魂玉", 1)],
        3: [("星砂", 5), ("魂玉", 2)],
        4: [("星砂", 6), ("龙血晶", 1)],
        5: [("星砂", 7), ("龙血晶", 2)],
    },
    "武器方": {
        0: [("玄铁矿", 2), ("灵木", 1)],
        1: [("玄铁矿", 3), ("赤金", 1)],
        2: [("玄金", 2), ("黑曜石", 1)],
        3: [("玄金", 3), ("玄星铁", 1)],
        4: [("玄星铁", 2), ("龙血晶", 1)],
        5: [("龙血晶", 2), ("天罡石", 1)],
    },
    "护具方": {
        0: [("黑曜石", 2), ("灵木", 1)],
        1: [("黑曜石", 3), ("天蚕丝", 1)],
        2: [("玄玉", 2), ("天蚕丝", 1)],
        3: [("玄星铁", 1), ("天蚕丝", 2)],
        4: [("玄星铁", 2), ("凤羽", 1)],
        5: [("龙鳞", 2), ("凤羽", 1)],
    },
}


ensure_recipes()
ensure_recipe_materials()

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

REALM_TIERS = ["灵胎", "五曜", "六合", "七星", "天道人","生死","神桥"]  # MVP占位
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
  last_pill_ts INTEGER DEFAULT 0,

  sect TEXT DEFAULT '',
  task_ready_ts INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS inv (
  user_id INTEGER,
  item TEXT,
  qty INTEGER,
  PRIMARY KEY (user_id, item)
);

CREATE TABLE IF NOT EXISTS limited_stock (
  item TEXT PRIMARY KEY,
  qty INTEGER DEFAULT 0
);
"""


async def db_init():
    os.makedirs("data", exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        cur = await db.execute("PRAGMA table_info(player)")
        cols = {row[1] for row in await cur.fetchall()}
        if "sect" not in cols:
            await db.execute("ALTER TABLE player ADD COLUMN sect TEXT DEFAULT ''")
        if "task_ready_ts" not in cols:
            await db.execute("ALTER TABLE player ADD COLUMN task_ready_ts INTEGER DEFAULT 0")
        if LIMITED_ITEMS:
            await db.executemany(
                "INSERT OR IGNORE INTO limited_stock(item, qty) VALUES(?, ?)",
                [(name, qty) for name, qty in LIMITED_ITEMS.items()],
            )
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
        await db.execute("INSERT OR IGNORE INTO inv(user_id,item,qty) VALUES(?,?,?)", (user_id, "洗髓丹", 1))
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


async def limited_stock_get(item: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT qty FROM limited_stock WHERE item=?", (item,))
        row = await cur.fetchone()
        return row[0] if row else 0


async def limited_stock_all() -> dict[str, int]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT item, qty FROM limited_stock ORDER BY item")
        rows = await cur.fetchall()
        return {item: qty for item, qty in rows}


async def limited_stock_set(item: str, qty: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO limited_stock(item, qty) VALUES(?, ?) "
            "ON CONFLICT(item) DO UPDATE SET qty=excluded.qty",
            (item, max(0, qty)),
        )
        await db.commit()


async def limited_stock_add(item: str, delta: int) -> int:
    current = await limited_stock_get(item)
    new_qty = max(0, current + delta)
    await limited_stock_set(item, new_qty)
    return new_qty


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


def weighted_choice_with_weight(pool: list[tuple[str, int]]) -> tuple[str, int]:
    total = sum(w for _, w in pool)
    r = random.uniform(0, total)
    upto = 0
    for item, w in pool:
        if upto + w >= r:
            return item, w
        upto += w
    return pool[-1]


def gen_daohao() -> str:
    return random.choice(DAOHAO_PREFIX) + random.choice(DAOHAO_SUFFIX)


def format_materials(mats: list[tuple[str, int]]) -> str:
    return "、".join([f"{name}×{qty}" for name, qty in mats])


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


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_USER_IDS


def parse_admin_args(text: str) -> Tuple[str, str]:
    if not text:
        return "", ""
    parts = text.strip().split(maxsplit=1)
    action = parts[0] if parts else ""
    rest = parts[1] if len(parts) > 1 else ""
    return action, rest


def parse_user_id(value: str) -> Optional[int]:
    if not value:
        return None
    if value.isdigit():
        return int(value)
    return None


def lore_pick(category: str) -> Optional[str]:
    lines = LORE.get(category, [])
    if not lines:
        return None
    return random.choice(lines)


def lore_list(category: str) -> Optional[str]:
    lines = LORE.get(category, [])
    if not lines:
        return None
    return "、".join(lines)

def format_realm_requirement(min_tier: int, min_stage: int) -> str:
    tier = max(0, min(min_tier, len(REALM_TIERS) - 1))
    stage = max(1, min(min_stage, STAGES_PER_TIER))
    return f"{REALM_TIERS[tier]}{stage_to_phase(stage)}"


async def catalog_lines(category: str) -> Optional[list[str]]:
    if category == "丹药":
        lines = []
        for name, pill in sorted(
            PILLS.items(),
            key=lambda item: (item[1].get("min_tier", 0), item[1].get("min_stage", 1), item[1].get("price", 0)),
        ):
            req = format_realm_requirement(pill["min_tier"], pill["min_stage"])
            exp = pill.get("exp", 0)
            price = pill.get("price", 0)
            desc = pill.get("desc", "")
            extra = []
            if exp:
                extra.append(f"修为+{exp}")
            if pill.get("clear_toxic"):
                extra.append("清除丹毒")
            if pill.get("reduce_toxic"):
                extra.append(f"丹毒-{pill['reduce_toxic']}")
            extra_info = "｜".join(extra) if extra else "调息用"
            lines.append(f"{name}｜{extra_info}｜需求:{req}｜售价:{price}灵石｜{desc}")
        return lines
    if category == "超稀有丹药":
        lines = []
        for name, pill in sorted(
            SUPER_RARE_PILLS.items(),
            key=lambda item: (item[1].get("min_tier", 0), item[1].get("min_stage", 1), item[1].get("price", 0)),
        ):
            req = format_realm_requirement(pill["min_tier"], pill["min_stage"])
            exp = pill.get("exp", 0)
            price = pill.get("price", 0)
            desc = pill.get("desc", "")
            lines.append(f"{name}｜修为+{exp}｜需求:{req}｜售价:{price}灵石｜{desc}")
        return lines
    if category == "武器":
        lines = []
        for name, info in sorted(
            WEAPONS.items(), key=lambda item: (item[1].get("min_tier", 0), item[1].get("atk", 0), item[1].get("price", 0))
        ):
            req = format_realm_requirement(info["min_tier"], 1)
            lines.append(
                f"{name}｜攻击{info['atk']}｜需求:{req}｜售价:{info['price']}灵石｜{info['desc']}"
            )
        return lines
    if category == "限量武器":
        lines = []
        stock_map = await limited_stock_all()
        for name, info in sorted(
            LIMITED_WEAPONS.items(),
            key=lambda item: (item[1].get("min_tier", 0), item[1].get("atk", 0), item[1].get("price", 0)),
        ):
            req = format_realm_requirement(info["min_tier"], 1)
            stock = stock_map.get(name, 0)
            use = info.get("use", "")
            use_info = f"｜用途:{use}" if use else ""
            lines.append(
                f"{name}｜攻击{info['atk']}｜需求:{req}｜剩余:{stock}｜售价:{info['price']}灵石｜{info['desc']}{use_info}"
            )
        return lines
    if category == "护具":
        lines = []
        for name, info in sorted(
            ARMORS.items(), key=lambda item: (item[1].get("min_tier", 0), item[1].get("def", 0), item[1].get("price", 0))
        ):
            req = format_realm_requirement(info["min_tier"], 1)
            lines.append(
                f"{name}｜防御{info['def']}｜需求:{req}｜售价:{info['price']}灵石｜{info['desc']}"
            )
        return lines
    if category == "限量防具":
        lines = []
        stock_map = await limited_stock_all()
        for name, info in sorted(
            LIMITED_ARMORS.items(),
            key=lambda item: (item[1].get("min_tier", 0), item[1].get("def", 0), item[1].get("price", 0)),
        ):
            req = format_realm_requirement(info["min_tier"], 1)
            stock = stock_map.get(name, 0)
            use = info.get("use", "")
            use_info = f"｜用途:{use}" if use else ""
            lines.append(
                f"{name}｜防御{info['def']}｜需求:{req}｜剩余:{stock}｜售价:{info['price']}灵石｜{info['desc']}{use_info}"
            )
        return lines
    if category in ("物品", "材料"):
        lines = []
        for name, info in sorted(ITEMS.items(), key=lambda item: (item[1].get("rarity", ""), item[1].get("price", 0))):
            lines.append(
                f"{name}｜稀有度:{info['rarity']}｜售价:{info['price']}灵石｜{info['desc']}"
            )
        return lines
    if category in ("限量道具", "超级稀有"):
        lines = []
        stock_map = await limited_stock_all()
        for name, info in sorted(SUPER_RARE.items(), key=lambda item: (item[1].get("price", 0), item[0])):
            stock = stock_map.get(name, 0)
            lines.append(
                f"{name}｜稀有度:{info['rarity']}｜剩余:{stock}｜售价:{info['price']}灵石｜{info['desc']}"
            )
        return lines
    if category in ("丹方", "武器方", "护具方"):
        lines = []
        for name, info in sorted(
            RECIPES.items(),
            key=lambda item: (item[1].get("tier", 0), item[1].get("price", 0), item[0]),
        ):
            if info["kind"] != category:
                continue
            req = format_realm_requirement(info["tier"], 1)
            mats = format_materials(info.get("mats", []))
            mats_info = f"｜材料:{mats}" if mats else ""
            lines.append(
                f"{name}｜目标:{info['target']}｜需求:{req}｜售价:{info['price']}灵石｜{info['desc']}{mats_info}"
            )
        return lines
    return None


async def fetch_leaderboard(kind: str, limit: int = 10) -> list[tuple]:
    async with aiosqlite.connect(DB_PATH) as db:
        if kind == "灵石":
            cur = await db.execute(
                "SELECT nick, daohao, stone FROM player ORDER BY stone DESC, exp DESC LIMIT ?",
                (limit,),
            )
            return await cur.fetchall()
        if kind == "修为":
            cur = await db.execute(
                "SELECT nick, daohao, exp, tier, stage FROM player ORDER BY exp DESC, stone DESC LIMIT ?",
                (limit,),
            )
            return await cur.fetchall()
    return []


def format_leaderboard_lines(kind: str, rows: list[tuple]) -> list[str]:
    lines = []
    if kind == "灵石":
        for idx, (nick, daohao, stone) in enumerate(rows, start=1):
            name = daohao or nick
            lines.append(f"{idx}. {name}｜灵石：{stone}")
    if kind == "修为":
        for idx, (nick, daohao, exp, tier, stage) in enumerate(rows, start=1):
            name = daohao or nick
            lines.append(f"{idx}. {name}｜境界：{realm_name(tier, stage)}｜修为：{exp}")
    return lines


def format_block(title: str, body_lines: list[str], footer_lines: Optional[list[str]] = None) -> str:
    lines = [f"【<b>{html.escape(title)}</b>】"]
    if body_lines:
        lines.extend(html.escape(line) for line in body_lines)
    if footer_lines:
        lines.append("")
        lines.extend(html.escape(line) for line in footer_lines)
    return "\n".join(lines)


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
        extra = "吐纳有成，灵气入体！大墟灵气回涌，周身一暖。"
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

    loot_lines = await roll_training_loot(user_id, TRAIN_LOOT_CHANCE)

    detail_lines = ["结果："]
    for line in extra.splitlines():
        detail_lines.append(f"- {line}")
    if len(detail_lines) == 1:
        detail_lines.append("- 平淡无奇。")
    detail_lines.append(f"- 修为变化：{delta:+d}")
    detail_lines.append(f"- 当前境界：{realm_name(tier2, stage2)}")
    detail_lines.append(f"- 当前修为：{cur_in_phase}/{cap_in_phase}")
    if loot_lines:
        detail_lines.extend([f"- {line}" for line in loot_lines])

    footer_lines = [f"调息：{mins}分钟后可再次闭关。"]
    return format_block("闭关修炼", detail_lines, footer_lines)


async def pick_recipe_by_kind(kind: str, max_tier: int = 1) -> Optional[str]:
    candidates = [
        name for name, info in RECIPES.items()
        if info["kind"] == kind and info.get("tier", 0) <= max_tier
    ]
    if not candidates:
        return None
    return random.choice(candidates)


def craft_cost(target_name: str, kind: str) -> int:
    if kind == "丹方":
        info = PILLS.get(target_name, {})
        return max(5, int(info.get("price", 0) * 0.35))
    if kind == "武器方":
        info = WEAPONS.get(target_name, {})
        return max(12, int(info.get("price", 0) * 0.25))
    if kind == "护具方":
        info = ARMORS.get(target_name, {})
        return max(10, int(info.get("price", 0) * 0.25))
    return 0


async def roll_training_loot(user_id: int, chance: float) -> list[str]:
    if random.random() > chance:
        return []
    item, weight = weighted_choice_with_weight(TRAIN_LOOT_POOL)
    qty = 1 if weight <= 8 else random.randint(1, 2)
    if item == "四灵血":
        qty = 1
    await inv_add(user_id, item, qty)
    return [f"获得{item}×{qty}"]

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
    return format_block(
        "深度闭关开启",
        [
            "时长：8小时",
            "结算：结束后，下次发言/指令自动结算。",
            "提示：大墟风沙隔绝尘世。",
        ],
    )


async def deep_status(user_id: int) -> str:
    p = await get_player(user_id)
    if not p:
        return "你尚未入道，请先发送 .检测灵体。"
    if p[9] != 1:
        return "你当前未在深度闭关中。"
    now = int(time.time())
    left = max(0, p[11] - now)
    return format_block(
        "深度闭关",
        [f"剩余时间：{left//3600}小时{(left%3600)//60}分钟{left%60}秒"],
    )


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
    loot_lines = await roll_training_loot(user_id, DEEP_LOOT_CHANCE)

    # 结算完关闭深度闭关
    await set_player_field(user_id, deep_active=0, deep_start_ts=0, deep_end_ts=0)

    p2 = await get_player(user_id)
    return format_block(
        "深度闭关结算",
        [
            f"模拟闭关：{loops}次",
            f"修为变化：{total:+d}",
            f"当前境界：{realm_name(p2[4], p2[5])}",
            *(loot_lines or []),
        ],
    )


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
    loot_lines = await roll_training_loot(user_id, DEEP_LOOT_CHANCE * 0.5)
    await set_player_field(user_id, deep_active=0, deep_start_ts=0, deep_end_ts=0)

    p2 = await get_player(user_id)
    return format_block(
        "强行出关",
        [
            "提示：强行出关，收益大打折扣。",
            f"模拟闭关：{loops}次",
            f"修为变化：{total:+d}",
            f"当前境界：{realm_name(p2[4], p2[5])}",
            *(loot_lines or []),
        ],
    )


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

    if cmd == "天道":
        if not is_admin(user_id):
            return "此指令仅天道可用。"

        action, args = parse_admin_args(rest)
        if not action or action == "帮助":
            return (
                "天道指令：\n"
                ".天道 查档 用户ID\n"
                ".天道 设置修为 用户ID 修为值\n"
                ".天道 境界 用户ID 境界序号 阶段(1-3)\n"
                ".天道 设置灵石 用户ID 数量\n"
                ".天道 加灵石 用户ID 数量\n"
                ".天道 扣灵石 用户ID 数量\n"
                ".天道 设置道号 用户ID 道号\n"
                ".天道 设置灵体 用户ID 灵体\n"
                ".天道 查包 用户ID\n"
                ".天道 发放 用户ID 物品名 数量\n"
                ".天道 限量库存\n"
                ".天道 设置限量 物品名 数量\n"
                ".天道 加限量 物品名 数量\n"
                ".天道 扣限量 物品名 数量\n"
                ".天道 清丹毒 用户ID\n"
                ".天道 重置闭关 用户ID\n"
            )

        if action == "查档":
            target_id = parse_user_id(args.strip())
            if target_id is None:
                return "用法：.天道 查档 用户ID"
            p = await get_player(target_id)
            if not p:
                return "目标尚未入道。"
            cur_in_phase, cap_in_phase = exp_view_in_phase(p[6], p[4], p[5])
            return (
                f"道友：{p[1]}\n道号：{p[2]}\n灵体：{p[3]}\n"
                f"境界：{realm_name(p[4], p[5])}\n当前修为：{cur_in_phase}/{cap_in_phase}\n"
                f"灵石：{p[7]}\n丹毒层数：{p[14]}"
            )

        if action == "设置修为":
            parts = args.split()
            if len(parts) != 2:
                return "用法：.天道 设置修为 用户ID 修为值"
            target_id = parse_user_id(parts[0])
            if target_id is None:
                return "用户ID无效。"
            try:
                exp_value = int(parts[1])
            except ValueError:
                return "修为值必须是整数。"
            p = await get_player(target_id)
            if not p:
                return "目标尚未入道。"
            await set_player_field(target_id, exp=max(0, exp_value))
            await maybe_rank_up(target_id)
            return "已调整修为。"

        if action == "境界":
            parts = args.split()
            if len(parts) != 3:
                return "用法：.天道 境界 用户ID 境界序号 阶段(1-3)"
            target_id = parse_user_id(parts[0])
            if target_id is None:
                return "用户ID无效。"
            try:
                tier = int(parts[1])
                stage = int(parts[2])
            except ValueError:
                return "境界序号与阶段必须是整数。"
            tier = max(0, min(tier, len(REALM_TIERS) - 1))
            stage = max(1, min(stage, STAGES_PER_TIER))
            p = await get_player(target_id)
            if not p:
                return "目标尚未入道。"
            await set_player_field(target_id, tier=tier, stage=stage)
            return f"已调整境界为：{realm_name(tier, stage)}"

        if action == "设置灵石":
            parts = args.split()
            if len(parts) != 2:
                return "用法：.天道 设置灵石 用户ID 数量"
            target_id = parse_user_id(parts[0])
            if target_id is None:
                return "用户ID无效。"
            try:
                stone_value = int(parts[1])
            except ValueError:
                return "数量必须是整数。"
            p = await get_player(target_id)
            if not p:
                return "目标尚未入道。"
            await set_player_field(target_id, stone=max(0, stone_value))
            return "已调整灵石。"

        if action == "加灵石":
            parts = args.split()
            if len(parts) != 2:
                return "用法：.天道 加灵石 用户ID 数量"
            target_id = parse_user_id(parts[0])
            if target_id is None:
                return "用户ID无效。"
            try:
                delta = int(parts[1])
            except ValueError:
                return "数量必须是整数。"
            p = await get_player(target_id)
            if not p:
                return "目标尚未入道。"
            await set_player_field(target_id, stone=max(0, p[7] + delta))
            return "已调整灵石。"

        if action == "扣灵石":
            parts = args.split()
            if len(parts) != 2:
                return "用法：.天道 扣灵石 用户ID 数量"
            target_id = parse_user_id(parts[0])
            if target_id is None:
                return "用户ID无效。"
            try:
                delta = int(parts[1])
            except ValueError:
                return "数量必须是整数。"
            p = await get_player(target_id)
            if not p:
                return "目标尚未入道。"
            await set_player_field(target_id, stone=max(0, p[7] - delta))
            return "已调整灵石。"

        if action == "设置道号":
            parts = args.split(maxsplit=1)
            if len(parts) != 2:
                return "用法：.天道 设置道号 用户ID 道号"
            target_id = parse_user_id(parts[0])
            if target_id is None:
                return "用户ID无效。"
            daohao = parts[1].strip()
            if not daohao:
                return "道号不能为空。"
            p = await get_player(target_id)
            if not p:
                return "目标尚未入道。"
            await set_player_field(target_id, daohao=daohao)
            return "已调整道号。"

        if action == "设置灵体":
            parts = args.split(maxsplit=1)
            if len(parts) != 2:
                return "用法：.天道 设置灵体 用户ID 灵体"
            target_id = parse_user_id(parts[0])
            if target_id is None:
                return "用户ID无效。"
            lingti = parts[1].strip()
            if not lingti:
                return "灵体不能为空。"
            p = await get_player(target_id)
            if not p:
                return "目标尚未入道。"
            await set_player_field(target_id, lingti=lingti)
            return "已调整灵体。"

        if action == "查包":
            target_id = parse_user_id(args.strip())
            if target_id is None:
                return "用法：.天道 查包 用户ID"
            p = await get_player(target_id)
            if not p:
                return "目标尚未入道。"
            items = await inv_get_all(target_id)
            if not items:
                return "储物袋空空如也。"
            return "\n".join(["储物袋："] + [f"{item} × {qty}" for item, qty in items])

        if action == "发放":
            parts = args.split()
            if len(parts) < 3:
                return "用法：.天道 发放 用户ID 物品名 数量"
            target_id = parse_user_id(parts[0])
            if target_id is None:
                return "用户ID无效。"
            try:
                qty = int(parts[-1])
            except ValueError:
                return "数量必须是整数。"
            if qty <= 0:
                return "数量必须为正整数。"
            item = " ".join(parts[1:-1]).strip()
            if not item:
                return "物品名不能为空。"
            p = await get_player(target_id)
            if not p:
                return "目标尚未入道。"
            if item in LIMITED_ITEMS:
                stock = await limited_stock_get(item)
                if stock < qty:
                    return f"限量库存不足：{item} 当前剩余 {stock}。"
                await limited_stock_add(item, -qty)
            await inv_add(target_id, item, qty)
            return f"已发放 {item} × {qty}。"

        if action == "限量库存":
            stocks = await limited_stock_all()
            if not stocks:
                return "暂无限量库存数据。"
            lines = ["限量库存："]
            for name, qty in stocks.items():
                lines.append(f"{name} × {qty}")
            return "\n".join(lines)

        if action in ("设置限量", "加限量", "扣限量"):
            parts = args.split()
            if len(parts) < 2:
                return f"用法：.天道 {action} 物品名 数量"
            try:
                delta = int(parts[-1])
            except ValueError:
                return "数量必须是整数。"
            if action == "设置限量":
                if delta < 0:
                    return "数量必须为非负整数。"
            else:
                if delta <= 0:
                    return "数量必须为正整数。"
            item = " ".join(parts[:-1]).strip()
            if not item:
                return "物品名不能为空。"
            if item not in LIMITED_ITEMS:
                return f"该物品不是限量物品：{item}"
            if action == "设置限量":
                await limited_stock_set(item, delta)
                return f"已设置 {item} 限量库存为 {max(0, delta)}。"
            if action == "加限量":
                new_qty = await limited_stock_add(item, delta)
                return f"已增加 {item} 限量库存，当前 {new_qty}。"
            new_qty = await limited_stock_add(item, -delta)
            return f"已扣减 {item} 限量库存，当前 {new_qty}。"

        if action == "清丹毒":
            target_id = parse_user_id(args.strip())
            if target_id is None:
                return "用法：.天道 清丹毒 用户ID"
            p = await get_player(target_id)
            if not p:
                return "目标尚未入道。"
            await set_player_field(target_id, toxic_points=0, last_pill_name="", last_pill_ts=0)
            return "已清除丹毒。"

        if action == "重置闭关":
            target_id = parse_user_id(args.strip())
            if target_id is None:
                return "用法：.天道 重置闭关 用户ID"
            p = await get_player(target_id)
            if not p:
                return "目标尚未入道。"
            await set_player_field(
                target_id,
                train_ready_ts=0,
                deep_active=0,
                deep_start_ts=0,
                deep_end_ts=0,
                deep_next_ts=0,
                passive_ready_ts=0,
            )
            return "已重置闭关与冷却。"

        return "未知天道指令。发送 .天道 帮助 查看可用指令。"

    if cmd == "帮助":
        return format_block(
            "指令一览",
            [
                ".检测灵体",
                ".我的灵体",
                ".闭关修炼",
                ".深度闭关 / .查看闭关 / .强行出关",
                ".储物袋",
                ".服用 丹药名*数量",
                ".炼制 配方名/目标物品*数量",
                ".图鉴 丹药/武器/护具/材料/丹方/武器方/护具方/限量武器/限量防具/超稀有丹药/限量道具",
                ".宗门 查看/加入 宗门名",
                ".任务",
                ".榜单 灵石/修为",
                ".传闻",
                ".世界观 / .人物 / .势力 / .地名",
                ".天道 帮助（管理员）",
            ],
        )

    if cmd == "检测灵体":
        p = await get_player(user_id)
        if p:
            return "你已检测过灵体，可发送 .我的灵体 查看档案。"
        daohao = gen_daohao()
        lingti = weighted_choice(LINGTI_POOL)
        await create_player(user_id, nick, daohao, lingti)
        return format_block(
            "检测灵体",
            [
                f"道友：{nick}",
                f"先天道灵体：{lingti}",
                f"当前境界：{realm_name(0,1)}",
                "身处大墟，万象皆险。",
            ],
            ["提示：可发送 .闭关修炼 开始修行。"],
        )

    if cmd == "我的灵体":
        p = await get_player(user_id)
        if not p:
            return "你尚未入道，请先发送 .检测灵体。"
        cur_in_phase, cap_in_phase = exp_view_in_phase(p[6], p[4], p[5])
        sect = p[17] if len(p) > 17 else ""
        sect_line = f"宗门：{sect}" if sect else "宗门：暂无"
        return format_block(
            "道友档案",
            [
                f"道友：{p[1]}",
                f"道号：{p[2]}",
                f"灵体：{p[3]}",
                f"境界：{realm_name(p[4], p[5])}",
                f"当前修为：{cur_in_phase}/{cap_in_phase}",
                f"灵石：{p[7]}",
                sect_line,
            ],
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
        lines = []
        for it, qty in items:
            if qty > 0:
                lines.append(f"- {it} × {qty}")
        return format_block("储物袋", lines)

    if cmd == "图鉴":
        category = rest.strip()
        if not category:
            return format_block(
                "图鉴",
                ["可选分类：丹药、武器、护具、材料、丹方、武器方、护具方、限量武器、限量防具、超稀有丹药、限量道具"],
                ["示例：.图鉴 丹药"],
            )
        lines = await catalog_lines(category)
        if not lines:
            return "未知分类。可选：丹药/武器/护具/材料/丹方/武器方/护具方/限量武器/限量防具/超稀有丹药/限量道具"
        return format_block(f"{category}图鉴", lines, ["提示：天道可用 .天道 发放 发放物品。"])

    if cmd == "宗门":
        action = rest.strip()
        if not action or action in ("查看", "列表"):
            lines = []
            for name, info in SECTS.items():
                lines.append(f"{name}｜{info['desc']}")
            return format_block("宗门一览", lines, ["用法：.宗门 加入 宗门名"])
        if action.startswith("加入"):
            parts = action.split(maxsplit=1)
            if len(parts) != 2:
                return "用法：.宗门 加入 宗门名"
            sect_name = parts[1].strip()
            if sect_name not in SECTS:
                return "未知宗门。可用：延康皇朝/天道圣教/残老村"
            p = await get_player(user_id)
            if not p:
                return "你尚未入道，请先发送 .检测灵体。"
            if len(p) > 17 and p[17]:
                return f"你已加入宗门：{p[17]}"
            await set_player_field(user_id, sect=sect_name)
            starter_kind = SECTS[sect_name]["starter_kind"]
            recipe_name = await pick_recipe_by_kind(starter_kind, max_tier=1)
            rewards = []
            if recipe_name:
                have = await inv_get(user_id, recipe_name)
                if have == 0:
                    await inv_add(user_id, recipe_name, 1)
                    rewards.append(f"{recipe_name}×1")
            mats = RECIPE_MATERIALS.get(starter_kind, {}).get(0, [])
            for item, qty in mats:
                await inv_add(user_id, item, qty)
                rewards.append(f"{item}×{qty}")
            reward_line = "、".join(rewards) if rewards else "暂无"
            return format_block("宗门加入成功", [f"宗门：{sect_name}", f"入门奖励：{reward_line}"])
        return "用法：.宗门 查看/加入 宗门名"

    if cmd == "任务":
        p = await get_player(user_id)
        if not p:
            return "你尚未入道，请先发送 .检测灵体。"
        now = int(time.time())
        task_ready_ts = p[18] if len(p) > 18 else 0
        if now < task_ready_ts:
            left = task_ready_ts - now
            return f"任务冷却中，请在 {left//60}分{left%60}秒 后再试。"
        sect = p[17] if len(p) > 17 else ""
        base_stone = random.randint(30, 80)
        materials_pool = ["灵木", "星砂", "玄铁矿", "黑曜石", "灵泉露", "玄玉", "赤金"]
        materials = random.sample(materials_pool, k=3)
        rewards = []
        for item in materials:
            qty = random.randint(1, 3)
            await inv_add(user_id, item, qty)
            rewards.append(f"{item}×{qty}")
        await set_player_field(user_id, stone=p[7] + base_stone, task_ready_ts=now + TASK_COOLDOWN)
        rewards.append(f"灵石×{base_stone}")
        if random.random() < 0.25:
            kind = SECTS.get(sect, {}).get("starter_kind", "丹方")
            recipe_name = await pick_recipe_by_kind(kind, max_tier=2)
            if recipe_name:
                await inv_add(user_id, recipe_name, 1)
                rewards.append(f"{recipe_name}×1")
        return format_block("任务完成", ["奖励：" + "、".join(rewards)], ["提示：任务奖励周期为6小时。"])

    if cmd == "炼制":
        p = await get_player(user_id)
        if not p:
            return "你尚未入道，请先发送 .检测灵体。"
        if not rest.strip():
            return "用法：.炼制 配方名/目标物品*数量"
        name, qty = parse_item_qty(rest)
        qty = max(1, qty)
        recipe_name = name if name in RECIPES else None
        if not recipe_name:
            matches = [k for k, v in RECIPES.items() if v["target"] == name]
            if len(matches) == 1:
                recipe_name = matches[0]
            elif len(matches) > 1:
                return "存在多个配方，请直接填写配方名。"
        if not recipe_name:
            return "未知配方或目标物品。可先用 .图鉴 丹方/武器方/护具方 查询。"
        recipe = RECIPES[recipe_name]
        have_recipe = await inv_get(user_id, recipe_name)
        if have_recipe <= 0:
            return "你尚未获得该配方，可通过宗门/任务/天道获取。"
        tier, stage = p[4], p[5]
        need_tier = recipe.get("tier", 0)
        if tier < need_tier:
            req = format_realm_requirement(need_tier, 1)
            return f"境界不足，需达到 {req} 才可炼制。"
        mats = recipe.get("mats", [])
        if not mats:
            return "配方缺少材料配置，请联系天道修正。"
        missing = []
        for item, amt in mats:
            have = await inv_get(user_id, item)
            need = amt * qty
            if have < need:
                missing.append(f"{item}缺{need - have}")
        if missing:
            return format_block("炼制失败", ["材料不足："] + missing)
        target = recipe["target"]
        cost = craft_cost(target, recipe["kind"]) * qty
        if p[7] < cost:
            return format_block("炼制失败", [f"灵石不足，需要 {cost} 灵石。"])
        for item, amt in mats:
            await inv_add(user_id, item, -amt * qty)
        await set_player_field(user_id, stone=p[7] - cost)
        await inv_add(user_id, target, qty)
        return format_block(
            "炼制成功",
            [
                f"配方：{recipe_name}",
                f"产物：{target} × {qty}",
                f"消耗灵石：{cost}",
                f"材料：{format_materials([(item, amt * qty) for item, amt in mats])}",
            ],
        )

    if cmd == "榜单":
        category = rest.strip() or "灵石"
        if category in ("灵石榜", "灵石"):
            rows = await fetch_leaderboard("灵石")
            if not rows:
                return "暂无灵石榜数据。"
            lines = format_leaderboard_lines("灵石", rows)
            return format_block("灵石榜", lines, ["统计范围：当前玩家灵石总量"])
        if category in ("修为榜", "修为"):
            rows = await fetch_leaderboard("修为")
            if not rows:
                return "暂无修为榜数据。"
            lines = format_leaderboard_lines("修为", rows)
            return format_block("修为榜", lines, ["统计范围：当前玩家修为总量"])
        return "未知榜单。可选：灵石/修为"

    if cmd == "传闻":
        return lore_pick("传闻") or "暂无传闻。"

    if cmd == "世界观":
        return lore_pick("世界观") or "暂无世界观条目。"

    if cmd == "人物":
        return lore_pick("人物") or "暂无人物条目。"

    if cmd == "势力":
        return lore_list("势力") or "暂无势力条目。"

    if cmd == "地名":
        return lore_list("地名") or "暂无地名条目。"

    if cmd == "服用":
        p = await get_player(user_id)
        if not p:
            return "你尚未入道，请先发送 .检测灵体。"
        if not rest.strip():
            return "用法：.服用 丹药名*数量（例如：.服用 聚气丹*2）"
        name, qty = parse_item_qty(rest)
        qty = max(1, qty)

        have = await inv_get(user_id, name)
        if have < qty:
            return format_block("服用失败", [f"储物袋中不足（拥有 {have}）。"])

        pill = PILLS.get(name)
        if not pill:
            return format_block("服用失败", [f"未知丹药：{name}", f"延康丹房仅内置：{', '.join(PILLS.keys())}"])

        tier, stage = p[4], p[5]
        if (tier < pill["min_tier"]) or (tier == pill["min_tier"] and stage < pill["min_stage"]):
            return format_block("服用失败", ["境界不足，无法承受药力。"])

        # 扣库存
        await inv_add(user_id, name, -qty)

        now = int(time.time())
        toxic_points = p[14]
        last_name = p[15]
        last_ts = p[16]

        if pill.get("clear_toxic"):
            await set_player_field(user_id, toxic_points=0, last_pill_name="", last_pill_ts=0)
            return format_block("服用成功", ["洗髓丹入腹，丹毒尽消，道心澄明。"])

        if pill.get("reduce_toxic"):
            toxic_points = max(0, toxic_points - pill["reduce_toxic"] * qty)
            await set_player_field(user_id, toxic_points=toxic_points, last_pill_name="", last_pill_ts=0)
            gain = pill["exp"] * qty
            if gain:
                await add_exp(user_id, gain)
                await maybe_rank_up(user_id)
            p2 = await get_player(user_id)
            cur_in_phase, cap_in_phase = exp_view_in_phase(p2[6], p2[4], p2[5])
            return format_block(
                "服用成功",
                [
                    f"丹药：{name} × {qty}",
                    f"修为变化：+{gain}",
                    f"当前境界：{realm_name(p2[4], p2[5])}",
                    f"当前修为：{cur_in_phase}/{cap_in_phase}",
                    f"丹毒层数：{toxic_points}",
                ],
            )

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
        cur_in_phase, cap_in_phase = exp_view_in_phase(p2[6], p2[4], p2[5])
        return format_block(
            "服用成功",
            [
                f"丹药：{name} × {qty}",
                f"修为变化：+{gain}",
                f"当前境界：{realm_name(p2[4], p2[5])}",
                f"当前修为：{cur_in_phase}/{cap_in_phase}",
                f"丹毒层数：{toxic_points}",
            ],
        )

    return None


# ----------------------------
# Bot
# ----------------------------
async def main():

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
            await msg.reply(settled, parse_mode="HTML")

        # 解析 .指令
        parsed = parse_cmd(msg.text or "")
        if parsed:
            cmd, rest = parsed
            res = await handle_cmd(msg, cmd, rest)
            if res:
                await msg.reply(res, parse_mode="HTML")
            else:
                await msg.reply("未知指令。发送 .帮助 查看可用指令。", parse_mode="HTML")
            return

        # 被动修为（模板描述：群内有效发言自动增加微量修为）
        await do_passive(msg)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())



