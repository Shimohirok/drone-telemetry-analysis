# -*- coding: utf-8 -*-
"""
第五步 · 电池与飞行阶段的关系
================================
课程要求：「分析电池电压、电流随时间的变化，研究其与电机转速、飞行阶段的关系」。

这一步要回答四个问题：
  1. 每个飞行阶段消耗多少电？（电压 / 电流 / 功率 / 能量）
  2. 电压的下降里，有多少是「电量耗尽」，有多少是「内阻压降」？
  3. 电压与电流到底是什么关系？（前面全序列算出的斜率是**正的**，被时间趋势污染了）
  4. 电流与转速的关系在各阶段是否一致？

做法要点（每一步的理由）：
  · 电压统计一律先剔除 voltage_usable == False 的 51 帧
    （810.0–815.0 s 的读数被整体平移 −1.826 V，不可用）
  · 电压的长期趋势用「段内线性拟合」估计——它近似代表开路电压随电量下降
  · 趋势的残差近似代表「内阻压降 + 负载波动」，再用它与电流求相关
    只有残差与电流显著负相关，才能说「内阻是可测的」
  · 短阶段（起飞 6 s、降落 3.8 s）样本少，统计量只作参考，不做强解释

输入：题1_标注版_阶段.csv
输出：fig_G_电池与阶段.png、fig_H_电压电流关系.png、电池与阶段说明_第五步.md（另写）
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

BASE = Path(r"D:\college documents\python数据分析 项目")
DATA = BASE / "题1_标注版_阶段.csv"
FIG = BASE / "关系图"

df = pd.read_csv(DATA)
df["power_w"] = df["battery_voltage_v"] * df["battery_current_a"]

ORDER = ["起飞", "爬升", "巡航（直线）", "盘旋（绕圈）", "下降", "降落"]
STAGE_KEYS = ["TAKEOFF", "CLIMB", "CRUISE", "LOITER", "DESCENT", "LANDING"]

# ============================================================
# 1. 按阶段统计
# ============================================================
print("=" * 92)
print("第五步 · 电池与飞行阶段的关系")
print("=" * 92)
print()

rows = []
for key in STAGE_KEYS:
    sub = df[df["stage"] == key]
    if len(sub) == 0:
        continue
    vu = sub[sub["voltage_usable"]]
    dur = len(sub) * 0.1
    # 能量：Σ V·I·dt，单位 J；换算 Wh
    e_j = float((vu["battery_voltage_v"] * vu["battery_current_a"] * 0.1).sum())
    e_wh = e_j / 3600.0
    rows.append({
        "阶段": key,
        "帧数": len(sub),
        "时长(s)": round(dur, 1),
        "电压均值(V)": round(vu["battery_voltage_v"].mean(), 3) if len(vu) else np.nan,
        "电压min": round(vu["battery_voltage_v"].min(), 2) if len(vu) else np.nan,
        "电压max": round(vu["battery_voltage_v"].max(), 2) if len(vu) else np.nan,
        "电流均值(A)": round(sub["battery_current_a"].mean(), 2),
        "电流min": round(sub["battery_current_a"].min(), 2),
        "电流max": round(sub["battery_current_a"].max(), 2),
        "转速均值(rpm)": round(sub["motor_rpm"].mean(), 0),
        "功率均值(W)": round((vu["battery_voltage_v"] * sub.loc[vu.index, "battery_current_a"]).mean(), 1) if len(vu) else np.nan,
        "能量(Wh)": round(e_wh, 3),
        "电压可用帧": len(vu),
    })

stat = pd.DataFrame(rows)
print("== 1. 按阶段统计（电压已剔除不可用帧）==")
print()
show = stat[["阶段", "时长(s)", "电压均值(V)", "电压min", "电压max",
             "电流均值(A)", "转速均值(rpm)", "功率均值(W)", "能量(Wh)"]]
print(show.to_string(index=False))
print()

total_wh = stat["能量(Wh)"].sum()
print(f"全飞行能量合计（按阶段累加）：{total_wh:.2f} Wh")
print()

# 单位时间能耗（W）与能量占比
print("== 2. 各阶段的能量占比 ==")
print()
for _, r in stat.iterrows():
    print(f"  {r['阶段']:<12} 时长 {r['时长(s)']:>6.1f} s　"
          f"功率 {r['功率均值(W)']:>6.1f} W　能量 {r['能量(Wh)']:>6.2f} Wh　"
          f"占 {r['能量(Wh)']/total_wh*100:>5.1f}%")
print()

# ============================================================
# 2. 电压趋势分离：开路电压 vs 内阻压降
# ============================================================
print("== 3. 电压趋势分离（段内线性拟合）==")
print()
print("思路：端电压 = 开路电压(随时间下降) − 内阻压降(随电流变化)")
print("      先用线性趋势近似开路电压，再看残差与电流的关系。")
print()

resid_all = pd.Series(index=df.index, dtype=float)
for seg in ["S1", "S2"]:
    m = (df["segment"] == seg) & df["voltage_usable"]
    sub = df.loc[m]
    if len(sub) < 50:
        continue
    t = sub["t"].values
    v = sub["battery_voltage_v"].values
    k, b = np.polyfit(t, v, 1)
    pred = k * t + b
    resid_all.loc[sub.index] = v - pred
    print(f"{seg}（{len(sub)} 帧）：")
    print(f"  线性趋势 V = {b:.3f} + ({k:+.6f})·t　→ 每 100 s 变化 {k*100:+.4f} V")
    print(f"  趋势下降总量（段内）：{k*(t.max()-t.min()):+.3f} V")
    print(f"  残差 std：{np.std(v-pred):.4f} V　残差范围 {np.min(v-pred):+.3f} ~ {np.max(v-pred):+.3f} V")

    # 残差与电流相关
    i_now = sub["battery_current_a"].values
    r = np.corrcoef(v - pred, i_now)[0, 1]
    print(f"  残差与电流的相关系数 r = {r:+.4f}")
    if r < -0.2:
        kv, _ = np.polyfit(i_now, v - pred, 1)
        print(f"  残差对电流的斜率 = {kv:+.4f} V/A　→ 近似内阻 {abs(kv)*1000:.1f} mΩ")
        print(f"  → 残差随电流增大而下降，符合内阻压降特征")
    elif abs(r) < 0.2:
        print(f"  → 残差与电流几乎无关，说明残差主要来自测量噪声，内阻不可测")
    else:
        print(f"  → 残差随电流增大而上升，不符合内阻压降特征（可能是电量回升/温度效应）")
    print()

df["voltage_trend_resid"] = resid_all

# ============================================================
# 3. 电流与转速的关系（分阶段）
# ============================================================
print("== 4. 电流 vs 转速（分阶段）==")
print()
print(f"{'阶段':<14}{'样本数':>7}{'相关系数 r':>12}{'斜率(A/rpm)':>14}")
print("-" * 50)
for key in STAGE_KEYS:
    sub = df[df["stage"] == key]
    if len(sub) < 30:
        print(f"{key:<14}{len(sub):>7}   样本不足")
        continue
    x = sub["motor_rpm"].values
    y = sub["battery_current_a"].values
    r = np.corrcoef(x, y)[0, 1]
    k, _ = np.polyfit(x, y, 1)
    print(f"{key:<14}{len(sub):>7}{r:>12.4f}{k*1000:>14.4f}")
print()
print("斜率单位换算：A per 1000 rpm。若各阶段斜率接近，说明「每转一千转需要多少电流」是恒定的。")
print()

# ============================================================
# 4. 图 G：电池与阶段
# ============================================================
NAMECN = dict(zip(STAGE_KEYS, ORDER))
present = [k for k in STAGE_KEYS if (df["stage"] == k).sum() > 0]
labels = [NAMECN[k] for k in present]
colors = ["#C0392B", "#E67E22", "#2F5D3A", "#2E86AB", "#9B59B6", "#34495E"]
cmap = dict(zip(present, colors[:len(present)]))

fig, axes = plt.subplots(3, 1, figsize=(12.5, 9), dpi=160)

# (a) 电压时序 + 趋势
ax = axes[0]
vu = df[df["voltage_usable"]]
ax.plot(df["t"], df["battery_voltage_v"], lw=0.4, color="#DDDDDD", label="原始电压")
ax.scatter(vu["t"], vu["battery_voltage_v"], s=1.2, c=vu["stage"].map(cmap),
           rasterized=True, label="按阶段着色")
for seg in ["S1", "S2"]:
    m = (df["segment"] == seg) & df["voltage_usable"]
    sub = df.loc[m]
    k, b = np.polyfit(sub["t"], sub["battery_voltage_v"], 1)
    ax.plot(sub["t"], k * sub["t"] + b, lw=1.8, color="#111111",
            label=f"{seg} 线性趋势" if seg == "S1" else "_nolegend_")
ax.axvline(700, color="#9E2B25", lw=1.2, ls="--", alpha=0.8)
ax.set_ylabel("电压 (V)")
ax.set_title("电池电压随时间与阶段的变化（灰线为原始，黑线为段内趋势）",
             fontsize=13, fontweight="bold")
ax.legend(loc="upper right", fontsize=8, frameon=False)
ax.grid(True, alpha=0.3)

# (b) 电流时序
ax = axes[1]
for k in present:
    m = df["stage"] == k
    ax.scatter(df.loc[m, "t"], df.loc[m, "battery_current_a"], s=1.2,
               color=cmap[k], rasterized=True, label=NAMECN[k])
ax.axvline(700, color="#9E2B25", lw=1.2, ls="--", alpha=0.8)
ax.set_ylabel("电流 (A)")
ax.set_title("电流随时间与阶段的变化", fontsize=13, fontweight="bold")
ax.legend(loc="upper right", fontsize=8, frameon=False, ncol=3)
ax.grid(True, alpha=0.3)

# (c) 按阶段的电流箱线图
ax = axes[2]
data = [df.loc[df["stage"] == k, "battery_current_a"].values for k in present]
try:
    # matplotlib >= 3.9 用 tick_labels，旧版用 labels
    bp = ax.boxplot(data, tick_labels=labels, patch_artist=True, showfliers=False,
                    medianprops=dict(color="#111", lw=1.6))
except TypeError:
    bp = ax.boxplot(data, labels=labels, patch_artist=True, showfliers=False,
                    medianprops=dict(color="#111", lw=1.6))
for patch, k in zip(bp["boxes"], present):
    patch.set_facecolor(cmap[k])
    patch.set_alpha(0.75)
ax.set_ylabel("电流 (A)")
ax.set_xlabel("飞行阶段")
ax.set_title("各阶段的电流分布（箱线图，已隐藏离群点）", fontsize=13, fontweight="bold")
ax.grid(True, alpha=0.3, axis="y")

fig.tight_layout()
p1 = FIG / "G_电池与阶段.png"
fig.savefig(p1, facecolor="white")
plt.close()
print("出图：", p1)
print()

# ============================================================
# 5. 图 H：电压-电流关系
# ============================================================
fig, axes = plt.subplots(1, 2, figsize=(13, 5.2), dpi=160)

# (a) 残差 vs 电流
ax = axes[0]
m = df["voltage_usable"] & df["voltage_trend_resid"].notna()
sub = df.loc[m]
ax.scatter(sub["battery_current_a"], sub["voltage_trend_resid"],
           c=sub["t"], cmap="viridis", s=5, alpha=0.6)
ax.axhline(0, color="#777", lw=1, ls=":")
ax.set_xlabel("电流 (A)")
ax.set_ylabel("电压残差 (V)　= 实测 − 段内线性趋势")
ax.set_title("电压残差 vs 电流（判断内阻是否可测）", fontsize=12, fontweight="bold")
r_all = np.corrcoef(sub["battery_current_a"], sub["voltage_trend_resid"])[0, 1]
ax.text(0.03, 0.95, f"r = {r_all:+.4f}", transform=ax.transAxes,
        fontsize=11, va="top", color="#9E2B25", fontweight="bold")
ax.grid(True, alpha=0.3)

# (b) 电压 vs 电流，按段着色 + 段内拟合
ax = axes[1]
for seg, c in [("S1", "#2F5D3A"), ("S2", "#9E2B25")]:
    m = (df["segment"] == seg) & df["voltage_usable"]
    s2 = df.loc[m]
    ax.scatter(s2["battery_current_a"], s2["battery_voltage_v"],
               s=3, alpha=0.35, color=c, label=seg)
    k, b = np.polyfit(s2["battery_current_a"], s2["battery_voltage_v"], 1)
    xs = np.linspace(s2["battery_current_a"].min(), s2["battery_current_a"].max(), 30)
    ax.plot(xs, k * xs + b, lw=2, color=c, label=f"{seg} 拟合 斜率 {k:+.4f}")
ax.set_xlabel("电流 (A)")
ax.set_ylabel("电压 (V)")
ax.set_title("电压 vs 电流（分段时间序列，斜率受电量趋势污染）",
             fontsize=12, fontweight="bold")
ax.legend(fontsize=9, frameon=False)
ax.grid(True, alpha=0.3)

fig.tight_layout()
p2 = FIG / "H_电压电流关系.png"
fig.savefig(p2, facecolor="white")
plt.close()
print("出图：", p2)
print()

# ============================================================
# 6. 结论摘要
# ============================================================
print("=" * 92)
print("结论摘要")
print("=" * 92)
print()
mx = stat.loc[stat["功率均值(W)"].idxmax()]
mn = stat.loc[stat["功率均值(W)"].idxmin()]
print(f"① 功率最高的阶段：{mx['阶段']}（{mx['功率均值(W)']} W）")
print(f"   功率最低的阶段：{mn['阶段']}（{mn['功率均值(W)']} W）")
print()
print(f"② 能量消耗最大的阶段：", end="")
big = stat.loc[stat["能量(Wh)"].idxmax()]
print(f"{big['阶段']}（{big['能量(Wh)']:.2f} Wh，占 {big['能量(Wh)']/total_wh*100:.1f}%）")
print(f"   该阶段时长 {big['时长(s)']} s，占全程 {big['时长(s)']/999.9*100:.1f}%")
print(f"   时长占比与能量占比的差异，说明「时间长的阶段」不等于「耗电多的阶段」")
print()
print("③ 电压下降的构成：")
for seg in ["S1", "S2"]:
    m = (df["segment"] == seg) & df["voltage_usable"]
    s2 = df.loc[m]
    k, b = np.polyfit(s2["t"], s2["battery_voltage_v"], 1)
    print(f"   {seg}：段内趋势 {k*100:+.4f} V/100s，"
          f"全段 {k*(s2['t'].max()-s2['t'].min()):+.3f} V")
print("   趋势项 ≈ 开路电压随电量下降；残差项 ≈ 内阻压降 + 噪声")
print()
print("④ 内阻是否可测：见上文第 3 节各段的残差-电流相关系数。")
print()
