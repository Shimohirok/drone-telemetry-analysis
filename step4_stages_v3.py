# -*- coding: utf-8 -*-
"""
第四步 · 飞行阶段识别（终版 · v3）
=====================================
三版演进记录（这一步踩了两个坑，都值得写进报告）：

  第 1 版：直接对逐帧高度求差分
    → 爬升被切成 144 段、下降切成 145 段
    → 原因：高度序列本身带巨大逐帧噪声
       S1 逐帧差分均值 0.291 m、S2 为 1.043 m（相当于 10.4 m/s 的表观速率）

  第 2 版：先对高度取 5 秒滚动中位数，再差分
    → 碎片化消失，但「起飞」识别不出来，且 S2 被误判为大部分在下降
    → 两个原因：
      a) 中心窗口的边界偏置：开头几帧速率被压到 0.2 m/s（真实约 1.6）
      b) 高度噪声不是零均值随机噪声，而是有结构的，
         中位数压不掉，导致 S2 平飞段算出 −1.10 m/s 的系统偏差

  第 3 版（本版）：改用「5 秒滑动窗口的线性回归斜率」
    → 实测各窗口速率极干净：
       S1   0–30 s   +1.665      S2  700–750 s    0.000
       S1  30–60 s   +2.224      S2  750–800 s    0.001
       S1  60–90 s   +2.221      S2  800–850 s    0.001
       S1  90–120 s  +2.222      S2  850–900 s   −0.008
       S1 120–150 s  −0.357      S2  900–950 s   −2.500
       S1 150–700 s  ≈ 0         S2  950–1000 s  −2.500

设计原则：
  垂直与水平是无人机两个独立的自由度 → 两层分类
    第 1 层：垂直状态（地面 / 起飞 / 爬升 / 平飞 / 下降 / 降落）
    第 2 层：只对「平飞」按 yaw 角速度细分（盘旋 / 巡航）
  这样不会出现「下降 + 绕圈」这种无法归类的组合。

输入：题1_标注版.csv
输出：题1_标注版_阶段.csv、阶段汇总（打印）、fig_阶段时间线.png
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
DATA = BASE / "题1_标注版.csv"
OUT_CSV = BASE / "题1_标注版_阶段.csv"
FIG = BASE / "关系图"

df = pd.read_csv(DATA)

SLOPE_WIN = 50
H_GROUND = 2.0
H_LOW = 10.0
RATE_THR = 0.6
YAW_THR = 5.0
MIN_DUR = 2.0
LAST_N = 150


def rolling_slope(y, win):
    """滑动窗口线性回归斜率（m/s）。窗口以当前点为中心，边界用可用部分。"""
    n = len(y)
    out = np.full(n, np.nan)
    half = win // 2
    for i in range(n):
        lo = max(0, i - half)
        hi = min(n, i + half + 1)
        seg = y[lo:hi]
        m = len(seg)
        if m < 5:
            continue
        x = np.arange(m) * 0.1
        xm = x.mean()
        denom = ((x - xm) ** 2).sum()
        if denom <= 0:
            continue
        out[i] = ((x - xm) * (seg - seg.mean())).sum() / denom
    return out


# ------------------------------------------------------------
# 1. yaw 解缠 + 角速度（段内）
# ------------------------------------------------------------
df["yaw_unwrap"] = np.nan
df["yaw_rate_dps"] = np.nan
for seg in ["S1", "S2"]:
    m = df["segment"] == seg
    idx = df.index[m]
    y = df.loc[m, "yaw_deg"].values
    d = np.diff(y)
    d = (d + 180.0) % 360.0 - 180.0
    uw = np.concatenate([[y[0]], y[0] + np.cumsum(d)])
    df.loc[idx, "yaw_unwrap"] = uw
    df.loc[idx, "yaw_rate_dps"] = np.abs(pd.Series(uw).diff(5).values) / 0.5

# ------------------------------------------------------------
# 2. 垂直速率：滑动回归斜率（段内）
# ------------------------------------------------------------
df["alt_smooth"] = np.nan
df["alt_rate_smooth"] = np.nan
for seg in ["S1", "S2"]:
    m = df["segment"] == seg
    idx = df.index[m]
    alt = df.loc[m, "altitude_agl_m"].values
    df.loc[idx, "alt_smooth"] = pd.Series(alt).rolling(
        SLOPE_WIN, center=True, min_periods=1).median().values
    df.loc[idx, "alt_rate_smooth"] = rolling_slope(alt, SLOPE_WIN)

# ------------------------------------------------------------
# 3. 两层分类
# ------------------------------------------------------------
def classify(sub):
    n = len(sub)
    height = sub["altitude_agl_m"].values
    speed = sub["ground_speed_mps"].values
    rate = sub["alt_rate_smooth"].values
    yawr = sub["yaw_rate_dps"].values

    is_last = np.zeros(n, dtype=bool)
    is_last[-LAST_N:] = True

    stage = np.array(["CRUISE"] * n, dtype=object)
    filled = np.zeros(n, dtype=bool)

    def put(mask, name):
        m = mask & ~filled
        stage[m] = name
        filled[m] = True

    put((height < H_GROUND) & (speed < 1.0), "GROUND")
    put((height < H_LOW) & is_last & (rate <= 0), "LANDING")
    put((height < H_LOW) & ~is_last & (rate > 0.5), "TAKEOFF")
    put(rate > RATE_THR, "CLIMB")
    put(rate < -RATE_THR, "DESCENT")
    put(yawr > YAW_THR, "LOITER")
    put(np.isnan(yawr), "CRUISE")
    return stage


def merge_short(stage, min_frames):
    s = stage.copy()
    n = len(s)
    for _ in range(300):
        runs = []
        a = 0
        for i in range(1, n + 1):
            if i == n or s[i] != s[a]:
                runs.append((a, i - 1, s[a]))
                a = i
        short = [k for k, (x, y, _) in enumerate(runs) if (y - x + 1) < min_frames]
        if not short:
            break
        k = short[0]
        x, y, _ = runs[k]
        if k > 0:
            s[x:y + 1] = runs[k - 1][2]
        elif k + 1 < len(runs):
            s[x:y + 1] = runs[k + 1][2]
        else:
            break
    return s


MIN_FRAMES = int(MIN_DUR / 0.1)
stage_all = np.array([""] * len(df), dtype=object)
for seg in ["S1", "S2"]:
    m = df["segment"] == seg
    sub = df.loc[m].reset_index(drop=True)
    stage_all[m.values] = merge_short(classify(sub), MIN_FRAMES)
df["stage"] = stage_all

# ------------------------------------------------------------
# 4. 汇总
# ------------------------------------------------------------
NAME = {
    "GROUND": "地面待命", "TAKEOFF": "起飞", "CLIMB": "爬升",
    "CRUISE": "巡航（直线）", "LOITER": "盘旋（绕圈）",
    "DESCENT": "下降", "LANDING": "降落",
}
ORDER = ["GROUND", "TAKEOFF", "CLIMB", "CRUISE", "LOITER", "DESCENT", "LANDING"]

print("=" * 82)
print("第四步 · 飞行阶段识别（终版 v3：滑动回归斜率）")
print("=" * 82)
print()
print(f"参数：高度<{H_GROUND}m 地面｜<{H_LOW}m 低空｜斜率窗口 {SLOPE_WIN*0.1:.0f}s｜"
      f"rate ±{RATE_THR} m/s｜yaw >{YAW_THR} °/s｜最短阶段 {MIN_DUR}s")
print()

for seg in ["S1", "S2"]:
    sub = df[df["segment"] == seg]
    print(f"── {seg}（{sub['t'].min():.1f} – {sub['t'].max():.1f} s，"
          f"{len(sub)} 帧 = {len(sub)*0.1:.0f} s）──")
    print(f"{'阶段':<14}{'帧数':>7}{'时长(s)':>10}{'占比':>9}")
    print("-" * 50)
    for k in ORDER:
        s = sub[sub["stage"] == k]
        if len(s) == 0:
            continue
        print(f"{NAME[k]:<14}{len(s):>7}{len(s)*0.1:>10.1f}{len(s)/len(sub)*100:>8.1f}%")
    print()

print("── 阶段序列（按时间顺序）──")
print()
seq = df[["t", "segment", "stage"]].copy()
seq["grp"] = (seq["stage"] != seq["stage"].shift()).cumsum()
runs = seq.groupby("grp").agg(
    stage=("stage", "first"), seg=("segment", "first"),
    t0=("t", "min"), t1=("t", "max"), n=("t", "size"),
).reset_index(drop=True)
runs["dur"] = runs["n"] * 0.1
print(f"{'#':>3}  {'段':<3}{'阶段':<14}{'起':>8}{'止':>8}{'时长':>8}{'占比':>8}")
print("-" * 66)
tot = runs["dur"].sum()
for i, r in runs.iterrows():
    print(f"{i+1:>3}  {r['seg']:<3}{NAME[r['stage']]:<14}{r['t0']:>8.1f}{r['t1']:>8.1f}"
          f"{r['dur']:>8.1f}{r['dur']/tot*100:>7.1f}%")
print()
print(f"共 {len(runs)} 个阶段段")
print()

# ------------------------------------------------------------
# 5. 导出
# ------------------------------------------------------------
df["stage_cn"] = df["stage"].map(NAME)
df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
print("导出：", OUT_CSV)
print()

# ------------------------------------------------------------
# 6. 出图
# ------------------------------------------------------------
COLORS = {
    "GROUND": "#6B6B6B", "TAKEOFF": "#C0392B", "CLIMB": "#E67E22",
    "CRUISE": "#2F5D3A", "LOITER": "#2E86AB", "DESCENT": "#9B59B6",
    "LANDING": "#34495E",
}

fig, axes = plt.subplots(4, 1, figsize=(13.5, 10), sharex=True, dpi=160)

ax = axes[0]
ax.plot(df["t"], df["altitude_agl_m"], lw=0.35, color="#DDDDDD")
for k, c in COLORS.items():
    m = df["stage"] == k
    if m.sum():
        ax.scatter(df.loc[m, "t"], df.loc[m, "altitude_agl_m"], s=1.5, color=c, rasterized=True)
ax.axvline(700, color="#9E2B25", lw=1.2, ls="--", alpha=0.8)
ax.set_ylabel("高度 AGL (m)")
ax.set_title("飞行阶段识别（颜色 = 阶段；灰线 = 原始高度）", fontsize=13, fontweight="bold")
handles = []
for k, c in COLORS.items():
    if (df["stage"] == k).sum():
        handles.append(plt.Line2D([], [], marker="o", ls="", color=c, ms=7, label=NAME[k]))
ax.legend(handles=handles, loc="upper left", fontsize=8, frameon=False, ncol=4)
ax.grid(True, alpha=0.3)

ax = axes[1]
for k, c in COLORS.items():
    m = df["stage"] == k
    if m.sum():
        ax.scatter(df.loc[m, "t"], df.loc[m, "ground_speed_mps"], s=1.5, color=c, rasterized=True)
ax.axvline(700, color="#9E2B25", lw=1.2, ls="--", alpha=0.8)
ax.set_ylabel("地速 (m/s)")
ax.grid(True, alpha=0.3)

ax = axes[2]
ax.plot(df["t"], df["yaw_unwrap"], lw=0.6, color="#5B4B8A")
ax.axvline(700, color="#9E2B25", lw=1.2, ls="--", alpha=0.8)
ax.set_ylabel("yaw 解缠 (°)")
ax.grid(True, alpha=0.3)

ax = axes[3]
ax.plot(df["t"], df["alt_rate_smooth"], lw=0.8, color="#A8854A")
ax.axhline(RATE_THR, color="#9E2B25", lw=1, ls=":")
ax.axhline(-RATE_THR, color="#9E2B25", lw=1, ls=":")
ax.axvline(700, color="#9E2B25", lw=1.2, ls="--", alpha=0.8)
ax.set_ylabel("垂直速率 (m/s，5s 回归斜率)")
ax.set_xlabel("时间 (秒)")
ax.grid(True, alpha=0.3)

fig.tight_layout()
p = FIG / "F_阶段时间线.png"
fig.savefig(p, facecolor="white")
plt.close()
print("出图：", p)
