# -*- coding: utf-8 -*-
"""
第四步 · 前置：为阶段识别做参数探查
=====================================
阶段识别不能凭感觉定阈值。本脚本只做探查，不产出最终结果。

要回答四个问题：
  1. 高度变化率（alt_rate_mps）的分布如何？「上升 / 平飞 / 下降」的界在哪？
  2. yaw 是否绕圈？绕了几圈？—— 这决定「盘旋」能不能用 yaw 变化率识别
  3. 地速分布如何？有没有真正的「低速悬停」阶段？
  4. 高度在地面附近的帧有多少？「地面 / 降落」的界在哪？
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

from pathlib import Path
import numpy as np
import pandas as pd

DATA = Path(r"D:\college documents\python数据分析 项目\题1_标注版.csv")
df = pd.read_csv(DATA)
df["yaw_unwrap"] = np.nan

# ============================================================
# 1. 高度变化率分布（按段）
# ============================================================
print("== 1. 高度变化率 alt_rate_mps 分布（按段）==")
print()
for seg in ["S1", "S2"]:
    r = df.loc[df["segment"] == seg, "alt_rate_mps"].dropna()
    print(f"{seg}（{len(r)} 帧）")
    print(f"  min {r.min():7.2f}　1% {np.percentile(r,1):7.2f}　25% {np.percentile(r,25):7.2f}")
    print(f"  median {r.median():7.2f}　75% {np.percentile(r,75):7.2f}　99% {np.percentile(r,99):7.2f}　max {r.max():7.2f}")
    print(f"  |rate| > 0.5 的帧 : {int((r.abs()>0.5).sum())}")
    print(f"  |rate| > 1.0 的帧 : {int((r.abs()>1.0).sum())}")
    print(f"  |rate| > 2.0 的帧 : {int((r.abs()>2.0).sum())}")
    print(f"  rate > +0.5（上升）: {int((r>0.5).sum())}")
    print(f"  rate < -0.5（下降）: {int((r<-0.5).sum())}")
    print()

# ============================================================
# 2. yaw 行为
# ============================================================
print("== 2. yaw 是否绕圈 ==")
print()
for seg in ["S1", "S2"]:
    m = df["segment"] == seg
    y = df.loc[m, "yaw_deg"].reset_index(drop=True)
    # 角度解缠：相邻帧差值规范化到 [-180, 180)，然后累加
    d = np.diff(y.values)
    d = (d + 180.0) % 360.0 - 180.0
    unwrapped = np.concatenate([[y.iloc[0]], y.iloc[0] + np.cumsum(d)])
    df.loc[m, "yaw_unwrap"] = unwrapped
    total = unwrapped[-1] - unwrapped[0]
    print(f"{seg}")
    print(f"  首帧 yaw {y.iloc[0]:8.2f}　末帧 yaw {y.iloc[-1]:8.2f}")
    print(f"  原始差分绝对值最大 : {np.abs(np.diff(y.values)).max():8.2f}°（说明有环绕跳变）")
    print(f"  解缠后差分绝对值最大: {np.abs(np.diff(unwrapped)).max():8.2f}°")
    print(f"  解缠后累计变化量   : {total:+9.1f}° = {total/360:+.2f} 圈")
    print(f"  解缠后范围         : {unwrapped.min():9.1f} – {unwrapped.max():9.1f}°")
    # 平均角速度（度/秒），一段 700s
    dur = len(y) * 0.1
    print(f"  平均角速度         : {total/dur:+6.2f} °/s（{total/dur*60/360:+.2f} 圈/分）")
    print()

# ============================================================
# 3. 地速分布
# ============================================================
print("== 3. 地速 ground_speed_mps 分布 ==")
print()
for seg in ["S1", "S2"]:
    s = df.loc[df["segment"] == seg, "ground_speed_mps"]
    print(f"{seg}：min {s.min():5.2f}　5% {np.percentile(s,5):5.2f}　median {s.median():5.2f}　"
          f"95% {np.percentile(s,95):5.2f}　max {s.max():5.2f}")
    for thr in [1, 2, 5, 10, 14, 15, 16, 20, 25]:
        n = int((s < thr).sum())
        if n:
            print(f"    < {thr:2d} m/s : {n:5d} 帧（{n/len(s)*100:5.2f}%）")
    print()

# ============================================================
# 4. 高度在地面附近的帧
# ============================================================
print("== 4. 高度分布与地面判定 ==")
print()
alt = df["altitude_agl_m"]
print(f"全序列：min {alt.min():6.2f}　median {alt.median():6.2f}　max {alt.max():6.2f} m")
for thr in [0.5, 1, 2, 5, 10]:
    n = int((alt < thr).sum())
    print(f"  高度 < {thr:4.1f} m : {n:4d} 帧")
print()
print("高度 < 5 m 的帧，时间位置：")
low = df[df["altitude_agl_m"] < 5]
if len(low):
    print(f"  共 {len(low)} 帧，时间范围 {low['t'].min():.1f} – {low['t'].max():.1f} s")
    # 分成连续的簇
    ts = low["t"].values
    clusters = []
    start = ts[0]
    prev = ts[0]
    for x in ts[1:]:
        if x - prev > 1.0:
            clusters.append((start, prev))
            start = x
        prev = x
    clusters.append((start, prev))
    print(f"  连续簇数 {len(clusters)}：")
    for a, b in clusters:
        print(f"    {a:7.1f} – {b:7.1f} s")
print()

# ============================================================
# 5. 粗粒度时间趋势（每 10 秒一个点，看整体形状）
# ============================================================
print("== 5. 粗粒度趋势（每 10 秒取均值）==")
print()
df["bin10"] = (df["t"] // 10 * 10).astype(int)
g = df.groupby("bin10").agg(
    seg=("segment", "first"),
    alt=("altitude_agl_m", "mean"),
    spd=("ground_speed_mps", "mean"),
    rate=("alt_rate_mps", "mean"),
    yaw=("yaw_unwrap", "mean"),
).round(1)
# 只打印每 30 秒一行，避免太长
print(g.iloc[::3].to_string())
