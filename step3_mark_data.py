# -*- coding: utf-8 -*-
"""
第三步 · 数据标记
====================
把前面所有判断固化成数据里的标记列。这一步不做分析，只做三件事：
  1. 给每一行打上「属于哪一段」「有没有被标记为可疑」
  2. 对每个标记写明「依据是什么、处理方式是什么」
  3. 导出标注版 CSV，供后续分析直接使用

所有标记的依据都来自前面已完成的三步：
  · 数据体检（step 0）
  · 关系图 A–D（plot_relations.py）
  · 高度跳变定位（stepA_height_jumps.py）
  · 电压凹陷定性（step3a_voltage_dip.py）

标记清单与决定：
  segment         S1/S2          700 s 处数据被替换，必须分段
  is_segment_break 布尔           700.0 s 那一帧
  is_load_pulse    布尔           350.0–356.1 s，真实负载脉冲（有效数据，保留）
  is_voltage_glitch 布尔          810.0–815.0 s，电压读数被平移 −1.826 V（5.1 s）
  is_mode_switch   布尔           30 / 116.4 / 120 / 900 s，工况切换（有效数据，保留）

输出：
  · 题1_标注版.csv
  · 标记摘要（打印）
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

from pathlib import Path
import numpy as np
import pandas as pd

DATA = Path(r"D:\college documents\python数据分析 项目\题1_无人机飞行遥测.csv")
OUT = Path(r"D:\college documents\python数据分析 项目\题1_标注版.csv")

df = pd.read_csv(DATA)
df["t"] = df["timestamp_ms"] / 1000.0

# ============================================================
# 1. 分段标记
# ============================================================
# 依据：700.0 s 处高度 +12.59 m、地速 −7.07 m/s，但电流 +1.9 A、转速 +29 rpm、
#       z 轴 0.905 g（全部正常）。若为真爬升需 126 m/s 垂直速度，物理不可能。
#       且 700 s 前后 50 秒的均值系统性偏移（高度 237→250、速度 19.7→14.0）。
# → 判定：两条飞行记录拼接 / 传感器重连后基线漂移。
# → 处理：不分段无法做任何跨 700 s 的差分与趋势分析，因此切成 S1 / S2。
SEG_BREAK_T = 700.0
df["segment"] = np.where(df["t"] < SEG_BREAK_T, "S1", "S2")
df["is_segment_break"] = np.isclose(df["t"], SEG_BREAK_T)

# ============================================================
# 2. 真实负载脉冲（保留，不是异常）
# ============================================================
# 依据：350.0 s 电流 +18.1 A、转速 +1550 rpm 同时跳变，方向一致；
#       356.1 s 反向恢复（−18.1 A / −1516 rpm）；期间高度仅变 10.65 m。
#       能量通道与动力通道同步、方向一致、量级匹配 → 物理自洽。
# → 判定：真实的负载脉冲（机体在保持高度的前提下加大功率）。
# → 处理：不剔除，只标记，因为它是有效飞行事件。
df["is_load_pulse"] = (df["t"] >= 350.0) & (df["t"] <= 356.1)

# ============================================================
# 3. 电压读数矩形异常（剔除，不可用于电池分析）
# ============================================================
# 依据：810.0 s 电压从 22.27 跳到 20.46（−1.81 V），815.1 s 跳回 22.26（+1.81 V）。
#       凹陷窗 5.1 秒内电压稳定在 20.45–20.48，而
#         电流均值变化 +0.016 A（22.04 → 22.06）
#         转速均值变化 +1 rpm
#       若为内阻压降，电流必须同步上升；若为电量耗尽，应单调下降而非矩形。
#       两个跳变幅度几乎相等（−1.81 / +1.81），是典型的「矩形平移」。
# → 判定：电压通道的读数被整体平移 1.826 V，持续 5.1 秒后精确恢复。
#         属于采集链路异常，不是电池电学现象。
# → 处理：标记并剔除（该窗内的电压值不可信），但保留其他通道。
VOL_START, VOL_END = 810.0, 815.0
df["is_voltage_glitch"] = (df["t"] >= VOL_START) & (df["t"] <= VOL_END)

# ============================================================
# 4. 工况切换（保留，不是异常）
# ============================================================
# 依据：30.0 / 116.4 / 120.0 / 900.0 s 四处，电流与转速大幅跳变
#       （最高 ±18.1 A、±1550 rpm），而高度基本不动（±0.5 m 内）。
#       能量与动力通道同步变化、运动通道不动 → 物理自洽。
# → 判定：飞行模式切换（例如切换航线、改变速度上限）。
# → 处理：不剔除，标记即可。
MODE_SWITCH = [(30.0, 30.2), (116.4, 116.6), (120.0, 120.2), (900.0, 900.2)]
df["is_mode_switch"] = False
for a, b in MODE_SWITCH:
    df.loc[(df["t"] >= a) & (df["t"] <= b), "is_mode_switch"] = True

# ============================================================
# 5. 供后续使用的派生列
# ============================================================
# 5.1 高度变化率（按段内计算，避免跨 700 s 产生假跳变）
df["alt_rate_mps"] = np.nan
for seg in ["S1", "S2"]:
    m = df["segment"] == seg
    # 段内 0.5 s 平滑后除以 0.1 s
    df.loc[m, "alt_rate_mps"] = (
        df.loc[m, "altitude_agl_m"].rolling(5, center=True, min_periods=1).mean().diff() / 0.1
    )

# 5.2 电压「可用」标记（凹陷窗内不可用）
df["voltage_usable"] = ~df["is_voltage_glitch"]

# 5.3 高度「可用」标记（段内首帧差分为 NaN，其余可用）
df["height_usable"] = df["alt_rate_mps"].notna()

# ============================================================
# 6. 导出
# ============================================================
out_cols = [
    "timestamp_ms", "t", "segment",
    "altitude_agl_m", "ground_speed_mps", "airspeed_mps",
    "roll_deg", "pitch_deg", "yaw_deg",
    "battery_voltage_v", "battery_current_a", "motor_rpm", "imu_accel_z_g",
    "gps_satellites", "gps_hdop",
    "alt_rate_mps",
    "is_segment_break", "is_load_pulse", "is_voltage_glitch", "is_mode_switch",
    "voltage_usable", "height_usable",
]
df[out_cols].to_csv(OUT, index=False, encoding="utf-8-sig")

# ============================================================
# 7. 摘要
# ============================================================
print("=" * 70)
print("第三步 · 数据标记完成")
print("=" * 70)
print()
print(f"总行数 : {len(df)}")
print()
print("== 分段 ==")
for seg, g in df.groupby("segment"):
    print(f"  {seg} ：{g['t'].min():7.1f} – {g['t'].max():7.1f} s　共 {len(g):5d} 帧（{len(g)*0.1:.1f} s）")
print()
print("== 各标记命中数 ==")
for c in ["is_segment_break", "is_load_pulse", "is_voltage_glitch", "is_mode_switch"]:
    n = int(df[c].sum())
    print(f"  {c:20s} {n:4d} 帧")
print()
print("== 可用性 ==")
print(f"  电压可用 ：{int(df['voltage_usable'].sum())} / {len(df)} 帧")
print(f"  高度可用 ：{int(df['height_usable'].sum())} / {len(df)} 帧")
print()
print("== 三处标记的对照 ==")
print(f"{'项目':<14}{'时刻(s)':<16}{'跳变通道':<22}{'未变通道':<18}{'判定':<16}{'处理'}")
print("-" * 104)
rows = [
    ("350 s 负载脉冲", "350.0–356.1", "电流 转速", "高度 地速", "真实负载", "保留+标记"),
    ("700 s 数据替换", "700.0", "高度 地速", "电流 转速 z轴", "数据拼接", "分段"),
    ("810 s 电压平移", "810.0–815.0", "电压", "电流 转速 高度", "采集链路异常", "剔除+标记"),
]
for r in rows:
    print(f"{r[0]:<14}{r[1]:<16}{r[2]:<22}{r[3]:<18}{r[4]:<16}{r[5]}")
print()
print("导出：", OUT)
