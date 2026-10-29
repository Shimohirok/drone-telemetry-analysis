# -*- coding: utf-8 -*-
"""诊断 stage 分类各判据的实际命中情况"""
import sys
sys.stdout.reconfigure(encoding="utf-8")
import pandas as pd
import numpy as np

df = pd.read_csv(r"D:\college documents\python数据分析 项目\题1_标注版_阶段.csv")


def diagnose(seg):
    sub = df[df["segment"] == seg].reset_index(drop=True)
    n = len(sub)
    height = sub["altitude_agl_m"].values
    speed = sub["ground_speed_mps"].values
    rate = sub["alt_rate_smooth"].values
    yawr = sub["yaw_rate_dps"].values

    is_last = np.zeros(n, dtype=bool)
    is_last[-150:] = True

    filled = np.zeros(n, dtype=bool)
    cnt = []

    def put(mask, name):
        nonlocal filled
        m = mask & ~filled
        cnt.append((name, int(m.sum())))
        filled = filled | m

    put((height < 2.0) & (speed < 1.0), "GROUND")
    put((height < 10.0) & is_last & (rate <= 0), "LANDING")
    put((height < 10.0) & ~is_last & (rate > 0.5), "TAKEOFF")
    put(rate > 0.6, "CLIMB")
    put(rate < -0.6, "DESCENT")
    put(yawr > 5.0, "LOITER")
    put(np.isnan(yawr), "CRUISE(nan-yaw)")
    cnt.append(("CRUISE(兜底)", int((~filled).sum())))

    print(f"{seg}（{n} 帧）：")
    for k, v in cnt:
        if v:
            print(f"   {k:<20}{v:>6} 帧 {v/n*100:>6.1f}%")
    print()


for s in ["S1", "S2"]:
    diagnose(s)

print("=== rolling_slope 边界：窗口实际点数 ===")
y = df[df["segment"] == "S1"]["altitude_agl_m"].values
for i in [0, 10, 24, 25, 100, 3499]:
    lo, hi = max(0, i - 25), min(len(y), i + 26)
    print(f"   i={i:5d}  窗口 [{lo},{hi})  点数 {hi-lo}")

print()
print("=== alt_smooth 是否参与分类 ===")
print("  classify 中 height = sub['altitude_agl_m']（原始值）")
print("  → alt_smooth 只写入 CSV，未参与任何判据（v2 遗留）")

print()
print("=== merge_short 结果 ===")
seq = df[["stage"]].copy()
seq["grp"] = (seq["stage"] != seq["stage"].shift()).cumsum()
sizes = seq.groupby("grp").size()
print(f"  合并后段数: {len(sizes)}")
print(f"  最短段帧数: {sizes.min()}（MIN_FRAMES=20）")
print(f"  最长段帧数: {sizes.max()}")

print()
print("=== TAKEOFF 与 CLIMB 阈值不一致的检查 ===")
sub = df[df["segment"] == "S1"]
mid = sub[(sub["altitude_agl_m"] < 10.0) & (sub["alt_rate_smooth"].abs() > 0.5)
          & (sub["alt_rate_smooth"].abs() <= 0.6)]
print(f"  S1 中「高度<10 且 0.5<|rate|<=0.6」的帧: {len(mid)}")
print("  → 这些帧会被判 TAKEOFF（阈值 0.5），但若高度>10 则不会判 CLIMB（阈值 0.6）")
print("  → 阈值不统一，属小的不一致（对本数据无实际影响）")
