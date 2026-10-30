# -*- coding: utf-8 -*-
"""
题目一 · 步骤 A：定位高度跳变点（修订版）
============================================
第一版把阈值设成 0.8 m，结果命中 1600 帧——因为正常爬升每帧就有 0.3–0.6 m 的变化。
正确的做法不是拍一个绝对阈值，而是先看差分的分布，再按分位数定界。

本版做法：
  1. 先描述差分分布（分位数报表）
  2. 用各列 99.9 分位数作为「异常判据」（自适应，不用人猜）
  3. 找「多列同时跳」的帧 —— 单列跳多半是噪声，多列同跳才指向系统性事件
  4. 对每个候选点，检查「高度跳变」是否与「加速度计读数」自洽
     这是区分「真机动」与「数据替换」的关键判据

判据原理：
  若机体真的在 0.1 秒内上升 12 m，垂直加速度必须极大，
  imu_accel_z_g 应出现远超 1.0 的读数。
  若高度跳了而 z 轴平稳，说明高度这一路数据被替换，机体并未移动。

输出：
  · 差分分布报表
  · 多列同时跳变清单
  · 每个候选点的自洽性检查
  · 一张标注图
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

for cand in [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"]:
    if Path(cand).exists():
        fm.fontManager.addfont(cand)
        plt.rcParams["font.family"] = fm.FontProperties(fname=cand).get_name()
        break
plt.rcParams["axes.unicode_minus"] = False

DATA = Path(r"D:\college documents\python数据分析 项目\题1_无人机飞行遥测.csv")
OUT = Path(r"D:\college documents\python数据分析 项目")
FIG = OUT / "关系图"

df = pd.read_csv(DATA)
df["t"] = df["timestamp_ms"] / 1000.0

COLS = ["altitude_agl_m", "ground_speed_mps", "battery_current_a", "motor_rpm"]
for c in COLS:
    df[c + "_d"] = df[c].diff()

# ============================================================
# 1. 差分分布
# ============================================================
print("== 1. 相邻帧差分分布（用于定阈值）==")
print()
for c in COLS:
    d = df[c + "_d"].abs().dropna()
    print(f"{c}")
    print(f"  中位数 {d.median():.3f}　95% {np.percentile(d,95):.3f}　"
          f"99% {np.percentile(d,99):.3f}　99.9% {np.percentile(d,99.9):.3f}　最大 {d.max():.3f}")
print()
print("用 0.8 m 这种绝对阈值会把正常爬升（每帧 0.3–0.6 m）也算进来，")
print("  所以改用各列的 99.9 分位数作为自适应阈值。")
print()

THR = {c: float(np.percentile(df[c + "_d"].abs().dropna(), 99.9)) for c in COLS}
print("各列 99.9% 阈值：")
for c, t in THR.items():
    print(f"  {c:22s} {t:8.3f}")
print()

# ============================================================
# 2. 多列同时跳变
# ============================================================
n_hit = pd.Series(0, index=df.index)
for c in COLS:
    n_hit += (df[c + "_d"].abs() > THR[c]).astype(int)

print("== 2. 多列同时跳变的帧（≥2 列超阈值）==")
cand = df[n_hit >= 2].copy()
show = ["t", "altitude_agl_m", "altitude_agl_m_d", "ground_speed_mps", "ground_speed_mps_d",
        "battery_current_a", "battery_current_a_d", "motor_rpm", "motor_rpm_d"]
print(cand[show].round(2).to_string(index=False))
print()

# ============================================================
# 3. 自洽性检查
# ============================================================
print("== 3. 自洽性检查：高度跳变是否与加速度计一致 ==")
print()
print("物理要求：若机体在 0.1 s 内上升 Δh，垂直速度变化 Δv = Δh/0.1 = 10Δh。")
print("         以 12.59 m 为例，Δv = 125.9 m/s，远超任何小型多旋翼的能力。")
print("         同时加速度计 z 轴应出现远超 1.0 g 的读数。")
print()

for _, r in cand.iterrows():
    dh = r["altitude_agl_m_d"]
    dv = r["ground_speed_mps_d"]
    z = r["imu_accel_z_g"]
    v_now = r["ground_speed_mps"]
    # 若高度真是爬升，需要的垂直速度
    need_v = dh / 0.1
    verdict = "数据替换（机体未动）" if abs(dh) > 5 and abs(z - 1.0) < 0.3 else "需进一步判断"
    print(f"  {r['t']:7.1f} s")
    print(f"    高度差 {dh:+7.2f} m　→ 若为真爬升，需垂直速度 {need_v:+8.1f} m/s")
    print(f"    地速差 {dv:+7.2f} m/s　z 轴 {z:.3f} g")
    print(f"    判读：{verdict}")
    print()

# ============================================================
# 4. 700 秒前后的均值对比（核心发现）
# ============================================================
print("== 4. 700 秒前后的均值对比（各取 50 秒）==")
print()
for lo, hi, lab in [(650, 699.9, "700 前"), (700, 749, "700 后")]:
    w = df[(df["t"] >= lo) & (df["t"] <= hi)]
    print(f"{lab}：高度 {w['altitude_agl_m'].mean():7.2f} m　"
          f"速度 {w['ground_speed_mps'].mean():5.2f} m/s　"
          f"电流 {w['battery_current_a'].mean():5.2f} A　"
          f"转速 {w['motor_rpm'].mean():6.0f} rpm")
print()
print("高度 +12.9 m、速度 −5.6 m/s，但转速只 +196 rpm、电流只 +2.0 A。")
print("  速度下降这么多而电流不降反升，与「减速」的物理过程矛盾。")
print("  → 700 s 处的突变不是飞行事件，而是数据拼接或传感器重连。")
print()

# ============================================================
# 5. 350 秒负载脉冲（与 700 s 对照）
# ============================================================
print("== 5. 350 s 附近的负载脉冲（与 700 s 形成对照）==")
print()
w350 = df[(df["t"] >= 340) & (df["t"] <= 365)]
print(f"350 s 段（340–365 s）：")
print(f"  高度范围 {w350['altitude_agl_m'].min():.2f} – {w350['altitude_agl_m'].max():.2f} m"
      f"（变化 {w350['altitude_agl_m'].max()-w350['altitude_agl_m'].min():.2f} m）")
print(f"  转速范围 {w350['motor_rpm'].min()} – {w350['motor_rpm'].max()} rpm")
print(f"  电流范围 {w350['battery_current_a'].min():.1f} – {w350['battery_current_a'].max():.1f} A")
print()
print("转速与电流大幅波动，但高度几乎不动 —— 这是真实的负载脉冲，")
print("  机体在保持不变高度的前提下加大功率。与 700 s 的数据替换性质不同。")
print()

# ============================================================
# 6. 出图
# ============================================================
fig, axes = plt.subplots(3, 1, figsize=(13, 8), sharex=True, dpi=160)

ax = axes[0]
ax.plot(df["t"], df["altitude_agl_m"], lw=0.7, color="#2F5D3A")
ax.scatter(cand["t"], cand["altitude_agl_m"], s=60, facecolors="none",
           edgecolors="#9E2B25", lw=1.6, zorder=5, label="多列同时跳变")
ax.axvline(700, color="#9E2B25", lw=1, linestyle="--", alpha=0.6)
ax.set_ylabel("高度 AGL (m)")
ax.set_title("高度序列与多列同时跳变点", fontsize=13, fontweight="bold")
ax.legend(loc="upper left", fontsize=9, frameon=False)
ax.grid(True, alpha=0.3)

ax = axes[1]
ax.plot(df["t"], df["ground_speed_mps"], lw=0.6, color="#9E2B25", label="地速")
ax.plot(df["t"], df["battery_current_a"], lw=0.5, color="#A8854A", alpha=0.7, label="电流")
ax.axvline(700, color="#9E2B25", lw=1, linestyle="--", alpha=0.6)
ax.set_ylabel("速度 (m/s) / 电流 (A)")
ax.legend(loc="upper right", fontsize=9, frameon=False)
ax.grid(True, alpha=0.3)

ax = axes[2]
ax.plot(df["t"], df["motor_rpm"], lw=0.5, color="#5B4B8A")
ax.axvline(700, color="#9E2B25", lw=1, linestyle="--", alpha=0.6)
ax.set_ylabel("转速 (rpm)")
ax.set_xlabel("时间 (秒)")
ax.grid(True, alpha=0.3)

fig.tight_layout()
fig.savefig(FIG / "E_高度跳变定位.png", facecolor="white")
plt.close()
print("已保存 E_高度跳变定位.png")
