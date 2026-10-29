# -*- coding: utf-8 -*-
"""
题目一 · 第 2 层可视化：属性关系图
=====================================
用途：为「异常标记与清洗」提供判据依据。
      第 1 层总览图（fig_总览.png）只能定位可疑区间，
      真正判断「哪个异常是真的、属于哪种脏因」，要看属性之间的关系。

四张图各自回答一个问题：
  图 A  电压 vs 电流   → 电池内阻是否随时间变化？810s 的凹陷是内阻还是噪声？
  图 B  转速 vs 电流   → 350s 的转速尖峰是真实负载，还是转速计故障？
  图 C  高度 vs 地速   → 这趟飞行一共几条航线段？阶段边界在哪？
  图 D  加速度 vs 高度变化率 → 高度数据与惯性数据是否自洽？

输出：4 个 PNG + 一份数值摘要（打印到终端）。
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

# ---------- 中文字体 ----------
for cand in [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"]:
    if Path(cand).exists():
        fm.fontManager.addfont(cand)
        plt.rcParams["font.family"] = fm.FontProperties(fname=cand).get_name()
        break
plt.rcParams["axes.unicode_minus"] = False

DATA = Path(r"D:\college documents\python数据分析 项目\题1_无人机飞行遥测.csv")
OUT = Path(r"D:\college documents\python数据分析 项目")
FIG = OUT / "关系图"
FIG.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(DATA)
df["t"] = df["timestamp_ms"] / 1000.0          # 秒

# 高度变化率（m/s）：中心差分，10 Hz
df["alt_rate"] = df["altitude_agl_m"].diff().rolling(5, center=True).mean() / 0.1

# 时间归一化，用于着色
tnorm = (df["t"] - df["t"].min()) / (df["t"].max() - df["t"].min())

CMAP = "viridis"


# ============================================================
# 图 A：电压 vs 电流
# ------------------------------------------------------------
# 判读逻辑：
#   若电池只是「正常放电」，电压与电流的关系应是一条斜率恒定的负相关直线
#   （电流越大，内阻压降越大，端电压越低）。
#   把颜色设为时间后：
#     · 曲线整体随时间整体下滑  → 容量在减少（正常）
#     · 曲线斜率随时间变陡      → 内阻在升高（电池老化）
#     · 个别点远离主带          → 该帧的电压或电流是野值
# ============================================================
print("== 图 A 电压 vs 电流 ==")

fig, ax = plt.subplots(figsize=(8.5, 6.2), dpi=170)
sc = ax.scatter(df["battery_current_a"], df["battery_voltage_v"],
                c=df["t"], cmap=CMAP, s=6, alpha=0.65)
cb = fig.colorbar(sc, ax=ax)
cb.set_label("时间 (秒)", fontsize=11)

# 分段线性拟合：前 1/3、中 1/3、后 1/3，看斜率是否变化
for lo, hi, label, color in [
    (0.00, 0.33, "前 1/3", "#9E2B25"),
    (0.33, 0.66, "中 1/3", "#A8854A"),
    (0.66, 1.00, "后 1/3", "#2F5D3A"),
]:
    m = (tnorm >= lo) & (tnorm < hi)
    if m.sum() < 10:
        continue
    k, b = np.polyfit(df.loc[m, "battery_current_a"],
                      df.loc[m, "battery_voltage_v"], 1)
    xs = np.linspace(df.loc[m, "battery_current_a"].min(),
                     df.loc[m, "battery_current_a"].max(), 50)
    ax.plot(xs, k * xs + b, lw=2, color=color,
            label=f"{label}　斜率 = {k:.4f} V/A")
    print(f"  {label}：斜率 {k:.4f} V/A")

ax.set_xlabel("电流 (A)", fontsize=12)
ax.set_ylabel("电压 (V)", fontsize=12)
ax.set_title("图 A　电压 vs 电流（颜色 = 时间）", fontsize=13, fontweight="bold")
ax.legend(loc="upper right", fontsize=10, frameon=False)
ax.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig(FIG / "A_电压vs电流.png", facecolor="white")
plt.close()
print("  已保存 A_电压vs电流.png")


# ============================================================
# 图 B：转速 vs 电流
# ------------------------------------------------------------
# 判读逻辑：
#   电机转速与母线电流应正相关（转速越高，负载越大，电流越大）。
#   若某批点「转速明显偏离但电流没跟上」，说明转速读数本身有问题，
#   而不是机体真的在加速——这是把「真异常」与「传感器故障」区分开的关键。
# ============================================================
print("== 图 B 转速 vs 电流 ==")

fig, ax = plt.subplots(figsize=(8.5, 6.2), dpi=170)
sc = ax.scatter(df["motor_rpm"], df["battery_current_a"],
                c=df["t"], cmap=CMAP, s=6, alpha=0.6)
cb = fig.colorbar(sc, ax=ax)
cb.set_label("时间 (秒)", fontsize=11)

# 标出 350s 附近（疑点①）
m350 = (df["t"] >= 330) & (df["t"] <= 380)
ax.scatter(df.loc[m350, "motor_rpm"], df.loc[m350, "battery_current_a"],
           s=26, facecolors="none", edgecolors="#9E2B25",
           lw=1.4, label="330–380 s（疑点①）")

# 相关系数
r = df[["motor_rpm", "battery_current_a"]].corr().iloc[0, 1]
ax.set_xlabel("电机转速 (rpm)", fontsize=12)
ax.set_ylabel("电流 (A)", fontsize=12)
ax.set_title(f"图 B　转速 vs 电流（相关系数 r = {r:.3f}）",
             fontsize=13, fontweight="bold")
ax.legend(loc="upper left", fontsize=10, frameon=False)
ax.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig(FIG / "B_转速vs电流.png", facecolor="white")
plt.close()
print(f"  相关系数 r = {r:.4f}")
print("  已保存 B_转速vs电流.png")


# ============================================================
# 图 C：高度 vs 地速
# ------------------------------------------------------------
# 判读逻辑：
#   这是飞行状态的「相图」。不同飞行阶段在这张图上占据不同区域：
#     地面待命   高度≈0，速度≈0（左下角）
#     爬升/下降   高度与速度同时变化（对角带）
#     巡航        高度高、速度大（右上）
#     盘旋/悬停   高度高、速度小（右下）
#   若某个阶段的人群在图上分成几簇，说明存在多条航线或模式切换。
# ============================================================
print("== 图 C 高度 vs 地速 ==")

fig, ax = plt.subplots(figsize=(8.5, 6.2), dpi=170)
sc = ax.scatter(df["ground_speed_mps"], df["altitude_agl_m"],
                c=df["t"], cmap=CMAP, s=5, alpha=0.55)
cb = fig.colorbar(sc, ax=ax)
cb.set_label("时间 (秒)", fontsize=11)

# 标出三个台阶突变时刻（疑点③）
for tt, lab in [(110, "110 s"), (700, "700 s"), (900, "900 s")]:
    m = (df["t"] >= tt - 8) & (df["t"] <= tt + 8)
    ax.scatter(df.loc[m, "ground_speed_mps"], df.loc[m, "altitude_agl_m"],
               s=30, facecolors="none", edgecolors="#9E2B25", lw=1.2)
    ax.annotate(lab, (df.loc[m, "ground_speed_mps"].mean(),
                      df.loc[m, "altitude_agl_m"].mean()),
                textcoords="offset points", xytext=(8, 8),
                fontsize=10, color="#9E2B25")

ax.set_xlabel("地速 (m/s)", fontsize=12)
ax.set_ylabel("高度 AGL (m)", fontsize=12)
ax.set_title("图 C　高度 vs 地速（颜色 = 时间）", fontsize=13, fontweight="bold")
ax.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig(FIG / "C_高度vs地速.png", facecolor="white")
plt.close()
print("  已保存 C_高度vs地速.png")


# ============================================================
# 图 D：imu_accel_z_g vs 高度变化率
# ------------------------------------------------------------
# 判读逻辑：
#   加速度计测的是「比力」。无人机垂直方向受力为：
#     升力 − 重力 = m·a
#     而 z 轴读数为 (a + g)/g，即静止悬停时 ≈ 1.0 g。
#   所以：
#     · 高度快速上升时，z 轴读数应 > 1
#     · 高度快速下降时，z 轴读数应 < 1
#   若高度在变但 z 轴始终 ≈ 1.0，说明其中一路数据不可信。
#   注意：高度变化率做了 0.5 s 滚动平滑，z 轴未平滑，所以是趋势性检验，
#         不能逐点严格对应。
# ============================================================
print("== 图 D 加速度 vs 高度变化率 ==")

d = df.dropna(subset=["alt_rate"])
fig, ax = plt.subplots(figsize=(8.5, 6.2), dpi=170)
sc = ax.scatter(d["alt_rate"], d["imu_accel_z_g"],
                c=d["t"], cmap=CMAP, s=6, alpha=0.55)
cb = fig.colorbar(sc, ax=ax)
cb.set_label("时间 (秒)", fontsize=11)

ax.axhline(1.0, color="#777", lw=1, linestyle="--", label="静止参考 1.0 g")
ax.set_xlabel("高度变化率 (m/s，0.5 s 平滑)", fontsize=12)
ax.set_ylabel("imu_accel_z_g", fontsize=12)
ax.set_title("图 D　垂直加速度 vs 高度变化率", fontsize=13, fontweight="bold")
ax.legend(loc="upper left", fontsize=10, frameon=False)
ax.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig(FIG / "D_加速度vs高度变化率.png", facecolor="white")
plt.close()

r_ac = d[["alt_rate", "imu_accel_z_g"]].corr().iloc[0, 1]
print(f"  高度变化率与 z 轴读数相关系数 r = {r_ac:.4f}")
print("  已保存 D_加速度vs高度变化率.png")


# ============================================================
# 数值摘要（供日志引用）
# ============================================================
print()
print("== 数值摘要 ==")
print(f"电压范围 : {df['battery_voltage_v'].min():.2f} – {df['battery_voltage_v'].max():.2f} V")
print(f"电流范围 : {df['battery_current_a'].min():.2f} – {df['battery_current_a'].max():.2f} A")
print(f"转速范围 : {df['motor_rpm'].min()} – {df['motor_rpm'].max()} rpm")
print(f"高度范围 : {df['altitude_agl_m'].min():.2f} – {df['altitude_agl_m'].max():.2f} m")
print(f"地速范围 : {df['ground_speed_mps'].min():.2f} – {df['ground_speed_mps'].max():.2f} m/s")

# 810s 凹陷的定量描述
m810 = (df["t"] >= 800) & (df["t"] <= 820)
seg = df.loc[m810]
print()
print("== 810 s 附近电压凹陷的定量描述 ==")
print(f"该段电压最小 : {seg['battery_voltage_v'].min():.2f} V（出现在 {seg.loc[seg['battery_voltage_v'].idxmin(), 't']:.1f} s）")
print(f"该段电压均值 : {seg['battery_voltage_v'].mean():.2f} V")
print(f"该段电流均值 : {seg['battery_current_a'].mean():.2f} A")
print(f"该段电流最大 : {seg['battery_current_a'].max():.2f} A")
print("→ 若凹陷处电流并未同步升高，则不是「大电流拉低端电压」，而应怀疑内阻或单节压降。")

# 350s 尖峰的定量描述
m350b = (df["t"] >= 340) & (df["t"] <= 370)
seg2 = df.loc[m350b]
print()
print("== 350 s 附近转速尖峰的定量描述 ==")
print(f"该段转速最大 : {seg2['motor_rpm'].max()} rpm（出现在 {seg2.loc[seg2['motor_rpm'].idxmax(), 't']:.1f} s）")
print(f"该段电流最大 : {seg2['battery_current_a'].max():.2f} A")
print(f"该段高度变化 : {seg2['altitude_agl_m'].min():.2f} – {seg2['altitude_agl_m'].max():.2f} m")
print("→ 若转速尖峰伴随电流同步尖峰，说明是真实负载；若电流没动，则更像转速读数问题。")

print()
print("全部图像已输出到:", FIG)
