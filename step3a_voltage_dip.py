# -*- coding: utf-8 -*-
"""
第三步 · 前置：给 810 s 的电压凹陷定性
==========================================
前面已经确认 700 s 是数据替换、350 s 是真实负载脉冲，
只剩 810 s 的电压凹陷没定论。本脚本只做这一件事。

要判的问题：这个凹陷是「内阻压降」还是「单节电芯/采样异常」？

判据（来自字段物理含义字典）：
  端电压 = 开路电压 E − 内阻压降 I·R
  · 若凹陷由大电流引起 → 凹陷时刻电流应显著上升
  · 若电流没变而电压掉了 → 不是内阻，是电芯或采样问题
  · 若只有单帧 → 采样毛刺
  · 若持续多帧后回升 → 真实的瞬时压降
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

from pathlib import Path
import numpy as np
import pandas as pd

DATA = Path(r"D:\college documents\python数据分析 项目\题1_无人机飞行遥测.csv")
df = pd.read_csv(DATA)
df["t"] = df["timestamp_ms"] / 1000.0

COLS = ["t", "battery_voltage_v", "battery_current_a", "motor_rpm",
        "altitude_agl_m", "ground_speed_mps", "imu_accel_z_g"]

# ============================================================
# 1. 找到凹陷的中心与宽度
# ============================================================
v = df["battery_voltage_v"]
print("== 1. 凹陷定位 ==")
vmin_idx = v.idxmin()
print(f"全序列最低电压 : {v.loc[vmin_idx]:.2f} V  at t = {df.loc[vmin_idx,'t']:.1f} s")
print()

# 用局部基线判断：滚动中位数
base = v.rolling(101, center=True, min_periods=20).median()
resid = v - base
dip = resid < -0.5          # 比局部中位数低 0.5 V 以上
print(f"显著低于局部中位数的帧数(|残差|>0.5V) : {int(dip.sum())}")
print()

# 连续段
mask = dip.values
segs = []
i = 0
while i < len(mask):
    if mask[i]:
        j = i
        while j < len(mask) and mask[j]:
            j += 1
        segs.append((i, j - 1))
        i = j
    else:
        i += 1
print(f"连续凹陷段数 : {len(segs)}")
print()
print("按长度排序的前 8 段：")
segs_sorted = sorted(segs, key=lambda s: -(s[1] - s[0] + 1))
for a, b in segs_sorted[:8]:
    n = b - a + 1
    t0, t1 = df.loc[a, "t"], df.loc[b, "t"]
    vmin = df.loc[a:b, "battery_voltage_v"].min()
    imean = df.loc[a:b, "battery_current_a"].mean()
    print(f"  {t0:7.1f} → {t1:7.1f} s   共 {n:4d} 帧({n*0.1:4.1f}s)   最低电压 {vmin:.2f} V   该段电流均值 {imean:.2f} A")
print()

# ============================================================
# 2. 凹陷时刻 vs 全局的电流对比
# ============================================================
print("== 2. 凹陷时刻的电流是否异常 ==")
print()
if segs_sorted:
    a, b = segs_sorted[0]
    t0, t1 = df.loc[a, "t"], df.loc[b, "t"]
    w = df.loc[a:b]
    print(f"最长凹陷段 {t0:.1f}–{t1:.1f} s 的统计：")
    print(f"  电压  min {w['battery_voltage_v'].min():.2f}  均值 {w['battery_voltage_v'].mean():.2f} V")
    print(f"  电流  min {w['battery_current_a'].min():.2f}  均值 {w['battery_current_a'].mean():.2f}  最大 {w['battery_current_a'].max():.2f} A")
    print(f"  转速  min {w['motor_rpm'].min()}      均值 {w['motor_rpm'].mean():.0f} rpm")
    print(f"  高度  均值 {w['altitude_agl_m'].mean():.2f} m")
    print(f"  z轴   均值 {w['imu_accel_z_g'].mean():.3f} g")
    print()
    # 对比前后 20 秒
    pre = df[(df["t"] >= t0 - 20) & (df["t"] < t0)]
    post = df[(df["t"] > t1) & (df["t"] <= t1 + 20)]
    print(f"  前 20 秒：电压均值 {pre['battery_voltage_v'].mean():.2f} V   电流均值 {pre['battery_current_a'].mean():.2f} A")
    print(f"  凹陷段：  电压均值 {w['battery_voltage_v'].mean():.2f} V   电流均值 {w['battery_current_a'].mean():.2f} A")
    print(f"  后 20 秒：电压均值 {post['battery_voltage_v'].mean():.2f} V   电流均值 {post['battery_current_a'].mean():.2f} A")
    print()
    dv = w["battery_voltage_v"].mean() - pre["battery_voltage_v"].mean()
    di = w["battery_current_a"].mean() - pre["battery_current_a"].mean()
    print(f"  电压变化 {dv:+.3f} V    电流变化 {di:+.3f} A")
    if abs(di) < 1.0 and dv < -0.3:
        print("  → 电流基本没变而电压明显下降：")
        print("    不符合「内阻压降」的特征（内阻压降必须伴随电流上升）")
        print("    指向：电芯瞬时压降 或 采样异常")
    elif di > 1.0 and dv < -0.3:
        print("  → 电流上升同时电压下降：符合内阻压降特征")
    print()

# ============================================================
# 3. 凹陷的逐帧明细
# ============================================================
print("== 3. 最长凹陷段的逐帧明细 ==")
if segs_sorted:
    a, b = segs_sorted[0]
    # 前后各扩 5 帧
    a2, b2 = max(0, a - 5), min(len(df) - 1, b + 5)
    print(df.loc[a2:b2, COLS].to_string(index=False))
print()

# ============================================================
# 4. 结论
# ============================================================
print("== 4. 判读 ==")
print()
print("综合上面的数据，本脚本给出的判读写在命令行末尾；")
print("真实结论请看运行输出。")
