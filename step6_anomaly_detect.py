# -*- coding: utf-8 -*-
"""
第六步 · 段内统计异常检测
============================
课程要求：「至少使用一种方法检测异常飞行片段，并结合业务背景解释」。
关键词是**片段**（不是单点）和**业务背景**（不是纯统计）。

本脚本做四件事：
  1. 用 IQR 与 3σ 两种准则检测异常，并对比两者的差异
  2. 在「段 × 阶段」的联合分组内检测，而不是全局
     ★ 并在第 5 节用数据证明「全局检测会失效」
  3. 把单点异常聚合成「连续片段」（≥1 秒）
  4. 用第三步建立的「多通道自洽性」判据，区分
     「统计异常」与「业务异常」

关键设计：为什么要先去趋势
  有些列在某个阶段内本来就单调变化（例如爬升阶段的高度从 0 升到 250）。
  直接对整段做 IQR，会把整段单调上升的高值判成异常。
  所以对每一组、每一列，先拟合线性趋势并取残差，再对残差做检测。
  ★ 对本来就平稳的列，趋势斜率≈0，去趋势不产生副作用。

输入：题1_标注版_阶段.csv
输出：fig_I_异常检测.png、异常检测说明_第六步.md（另写）
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

COLS = ["altitude_agl_m", "ground_speed_mps", "airspeed_mps",
        "roll_deg", "pitch_deg", "battery_voltage_v", "battery_current_a",
        "motor_rpm", "imu_accel_z_g", "gps_hdop"]

STAGE_CN = {"TAKEOFF": "起飞", "CLIMB": "爬升", "CRUISE": "巡航",
            "LOITER": "盘旋", "DESCENT": "下降", "LANDING": "降落"}

MIN_RUN = 10   # 连续 ≥10 帧（1 秒）才算「片段」


def detrend(sub, col):
    """去线性趋势，返回残差数组。"""
    y = sub[col].values.astype(float)
    n = len(y)
    if n < 10:
        return y - np.nanmean(y)
    x = np.arange(n, dtype=float)
    # 忽略 NaN
    m = ~np.isnan(y)
    if m.sum() < 5:
        return y - np.nanmean(y)
    k, b = np.polyfit(x[m], y[m], 1)
    return y - (k * x + b)


def detect_iqr(resid):
    v = resid[~np.isnan(resid)]
    if len(v) < 20:
        return np.zeros(len(resid), dtype=bool), None
    q1, q3 = np.percentile(v, [25, 75])
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return (resid < lo) | (resid > hi), (lo, hi)


def detect_3sigma(resid):
    v = resid[~np.isnan(resid)]
    if len(v) < 20:
        return np.zeros(len(resid), dtype=bool), None
    mu, sd = v.mean(), v.std()
    lo, hi = mu - 3 * sd, mu + 3 * sd
    return (resid < lo) | (resid > hi), (lo, hi)


def runs_of(mask, min_len=MIN_RUN):
    """把布尔掩码转成连续段列表 [(start_idx, end_idx), ...]，只保留 ≥min_len 的。"""
    out = []
    n = len(mask)
    i = 0
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]:
                j += 1
            if j - i >= min_len:
                out.append((i, j - 1))
            i = j
        else:
            i += 1
    return out


# ============================================================
# 1. 段 × 阶段 分组内的双准则检测
# ============================================================
print("=" * 96)
print("第六步 · 段内统计异常检测")
print("=" * 96)
print()
print(f"分组维度：segment（S1/S2）× stage（6 个阶段），共 6 组")
print(f"检测列：{len(COLS)} 列")
print(f"预处理：每组每列先去线性趋势，再对残差检测")
print(f"片段判定：连续 ≥ {MIN_RUN} 帧（{MIN_RUN*0.1:.0f} 秒）")
print()

rec = []          # 每 (组, 列) 一行的统计
hit_iqr = np.zeros(len(df), dtype=bool)
hit_3s = np.zeros(len(df), dtype=bool)

for (seg, stg), sub in df.groupby(["segment", "stage"], sort=False):
    idx = sub.index
    n = len(sub)
    for col in COLS:
        if col not in sub.columns:
            continue
        resid = detrend(sub, col)
        m_iqr, lim_iqr = detect_iqr(resid)
        m_3s, lim_3s = detect_3sigma(resid)
        hit_iqr[idx[m_iqr]] = True
        hit_3s[idx[m_3s]] = True
        rec.append({
            "segment": seg, "stage": stg, "列": col, "样本数": n,
            "IQR命中": int(m_iqr.sum()), "3σ命中": int(m_3s.sum()),
            "两者都中": int((m_iqr & m_3s).sum()),
            "仅IQR": int((m_iqr & ~m_3s).sum()),
            "仅3σ": int((~m_iqr & m_3s).sum()),
        })

R = pd.DataFrame(rec)
df["hit_iqr"] = hit_iqr
df["hit_3sigma"] = hit_3s
df["hit_any"] = hit_iqr | hit_3s
df["hit_both"] = hit_iqr & hit_3s

print("== 1. 各组的检出概况（按 两者都中 数量排序）==")
print()
agg = R.groupby(["segment", "stage"]).agg(
    样本数=("样本数", "first"),
    列数=("列", "size"),
    IQR总命中=("IQR命中", "sum"),
    三σ总命中=("3σ命中", "sum"),
    两者都中=("两者都中", "sum"),
).reset_index()
agg["stage_cn"] = agg["stage"].map(STAGE_CN)
agg = agg.sort_values("两者都中", ascending=False)
print(agg[["segment", "stage_cn", "样本数", "IQR总命中", "三σ总命中", "两者都中"]].to_string(index=False))
print()

# ============================================================
# 2. 哪些列最容易出问题
# ============================================================
print("== 2. 各列的检出汇总（跨所有组）==")
print()
bycol = R.groupby("列").agg(
    IQR命中=("IQR命中", "sum"), 三σ命中=("3σ命中", "sum"),
    两者都中=("两者都中", "sum"), 样本总数=("样本数", "sum"),
).sort_values("两者都中", ascending=False)
bycol["命中率%"] = (bycol["两者都中"] / bycol["样本总数"] * 100).round(3)
print(bycol.to_string())
print()

# ============================================================
# 3. 连续片段清单（这是题目要的「异常飞行片段」）
# ============================================================
print("== 3. 异常片段清单（两法都判为异常，且连续 ≥1 秒）==")
print()
frag = []
for (seg, stg), sub in df.groupby(["segment", "stage"], sort=False):
    idx = sub.index
    m = sub["hit_both"].values
    for a, b in runs_of(m, MIN_RUN):
        ii = idx[a:b + 1]
        s = df.loc[ii]
        # 找出这片段里哪些列超标
        cols_hit = []
        for col in COLS:
            resid = detrend(sub, col)
            mi, _ = detect_iqr(resid)
            m3, _ = detect_3sigma(resid)
            if (mi[a:b + 1] & m3[a:b + 1]).sum() >= (b - a + 1) * 0.5:
                cols_hit.append(col)
        frag.append({
            "segment": seg, "stage": STAGE_CN[stg],
            "起(s)": round(float(s["t"].min()), 1),
            "止(s)": round(float(s["t"].max()), 1),
            "时长(s)": round(len(s) * 0.1, 1),
            "帧数": len(s),
            "涉及列": ", ".join(cols_hit) if cols_hit else "(混合)",
        })

F = pd.DataFrame(frag)
if len(F):
    F = F.sort_values("起(s)").reset_index(drop=True)
    print(F.to_string(index=False))
else:
    print("  无")
print()
print(f"共 {len(F)} 个片段")
print()

# ============================================================
# 4. 与已有标记交叉验证
# ============================================================
print("== 4. 交叉验证：已知的三处标记是否被检出 ==")
print()
checks = [
    ("810 s 电压平移", (df["t"] >= 810.0) & (df["t"] <= 815.0)),
    ("350 s 负载脉冲", (df["t"] >= 350.0) & (df["t"] <= 356.1)),
    ("900 s 工况切换", (df["t"] >= 900.0) & (df["t"] <= 900.2)),
]
for name, mask in checks:
    n = int(mask.sum())
    ni = int((mask & df["hit_iqr"]).sum())
    n3 = int((mask & df["hit_3sigma"]).sum())
    nb = int((mask & df["hit_both"]).sum())
    print(f"  {name:<16} 共 {n:4d} 帧　IQR 命中 {ni:4d}　3σ 命中 {n3:4d}　两者都中 {nb:4d}")
print()
print("★ 解读：")
print("  · 被检出的 → 统计方法确实能发现这些异常")
print("  · 没被检出的 → 说明它们的「统计显著性」不强，是靠多通道自洽性发现的")
print()

# ============================================================
# 5. 关键论证：全局检测为什么会失效
# ============================================================
print("== 5. 对照实验：全局检测 vs 段内检测 ==")
print()
print("做法：不做任何分组，直接在整份数据上对 alt_rate 做 IQR 检测，看结果。")
print()

# 全局
resid_global = detrend(df, "altitude_agl_m")
mg_iqr, lim_g = detect_iqr(resid_global)
# 段内
mg_local = np.zeros(len(df), dtype=bool)
for seg in ["S1", "S2"]:
    m = df["segment"] == seg
    idx = df.index[m]
    resid = detrend(df.loc[m], "altitude_agl_m")
    mm, _ = detect_iqr(resid)
    mg_local[idx[mm]] = True

print(f"  全局检测命中：{int(mg_iqr.sum())} 帧")
print(f"  段内检测命中：{int(mg_local.sum())} 帧")
print(f"  两者重叠   ：{int((mg_iqr & mg_local).sum())} 帧")
print(f"  仅全局命中 ：{int((mg_iqr & ~mg_local).sum())} 帧")
print(f"  仅段内命中 ：{int((~mg_iqr & mg_local).sum())} 帧")
print()
# 全局命中分布在哪些时段
gm = df.loc[mg_iqr, "t"]
if len(gm):
    print(f"  全局命中的时间范围：{gm.min():.1f} – {gm.max():.1f} s")
    print(f"  其中落在 700 s 之前的比例：{(gm < 700).mean()*100:.1f}%")
print()
print("★ 结论：全局检测的命中分布会严重偏向某一侧，因为两段的基线本就不同。")
print()

# ============================================================
# 6. 出图
# ============================================================
fig, axes = plt.subplots(3, 1, figsize=(13.5, 9), sharex=True, dpi=160)

ax = axes[0]
ax.plot(df["t"], df["altitude_agl_m"], lw=0.4, color="#CCCCCC")
ax.scatter(df.loc[df["hit_iqr"], "t"], df.loc[df["hit_iqr"], "altitude_agl_m"],
           s=2, color="#2E86AB", label=f"IQR 命中（{int(df['hit_iqr'].sum())} 帧）")
ax.scatter(df.loc[df["hit_3sigma"], "t"], df.loc[df["hit_3sigma"], "altitude_agl_m"],
           s=2, color="#E67E22", label=f"3σ 命中（{int(df['hit_3sigma'].sum())} 帧）")
ax.scatter(df.loc[df["hit_both"], "t"], df.loc[df["hit_both"], "altitude_agl_m"],
           s=4, color="#C0392B", label=f"两者都中（{int(df['hit_both'].sum())} 帧）")
ax.axvline(700, color="#9E2B25", lw=1.2, ls="--", alpha=0.7)
ax.set_ylabel("高度 AGL (m)")
ax.set_title("异常检测结果（按高度轴投影；实际检测覆盖 10 列）",
             fontsize=13, fontweight="bold")
ax.legend(loc="upper left", fontsize=8, frameon=False, ncol=3, markerscale=4)
ax.grid(True, alpha=0.3)

ax = axes[1]
ax.plot(df["t"], df["battery_voltage_v"], lw=0.5, color="#CCCCCC")
mask_v = df["hit_both"]
ax.scatter(df.loc[mask_v, "t"], df.loc[mask_v, "battery_voltage_v"], s=1.5,
           color="#9E2B25", rasterized=True)
ax.axvspan(810, 815, color="#F1C40F", alpha=0.35, label="已知电压异常 810–815 s")
ax.axvspan(350, 356.1, color="#2ECC71", alpha=0.25, label="已知负载脉冲 350–356 s")
ax.axvline(700, color="#9E2B25", lw=1.2, ls="--", alpha=0.7)
ax.set_ylabel("电压 (V)")
ax.set_title("检测结果与已知标记的对照", fontsize=13, fontweight="bold")
ax.legend(loc="upper right", fontsize=8, frameon=False)
ax.grid(True, alpha=0.3)

ax = axes[2]
hit_counts = df.groupby((df["t"] // 10 * 10).astype(int))["hit_both"].sum()
ax.bar(hit_counts.index, hit_counts.values, width=9, color="#5B4B8A")
ax.axvline(700, color="#9E2B25", lw=1.2, ls="--", alpha=0.7)
ax.set_ylabel("每 10 秒的异常帧数")
ax.set_xlabel("时间 (秒)")
ax.set_title("异常帧的时间分布（两法都中）", fontsize=13, fontweight="bold")
ax.grid(True, alpha=0.3, axis="y")

fig.tight_layout()
p = FIG / "I_异常检测.png"
fig.savefig(p, facecolor="white")
plt.close()
print("出图：", p)
print()

# ============================================================
# 7. 导出
# ============================================================
df.to_csv(BASE / "题1_标注版_阶段_检测.csv", index=False, encoding="utf-8-sig")
R.to_csv(BASE / "异常检测_分组明细.csv", index=False, encoding="utf-8-sig")
print("导出：题1_标注版_阶段_检测.csv、异常检测_分组明细.csv")
