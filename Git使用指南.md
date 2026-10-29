# Git/GitHub 使用指南（针对题1 无人机项目）

> 给完全没接触过 Git 的同学。只讲这门课**够用**的部分，不讲原理。

---

## 一、一句话理解 Git

**Git = 代码的「存档点」+「谁在什么时候改了什么」的记录。**

老师要的不是 Git 本身，而是**后面那半句——「谁改了什么」**。

因为课程要求里明确写了一句很关键的话：

> 「成员分工与个人承担」章节所写的各人负责模块**应能与提交记录对应**。

翻译过来就是：**老师会打开你们的 GitHub 仓库，看谁提交了哪些代码，来核对是不是 3 个人真的都干活了。** 如果提交记录里只有一个人，老师会怀疑「是不是一个人包办」。

---

## 二、三个核心词（记住这三个就够入门）

| 词 | 大白话 | 类比 |
|---|---|---|
| **commit** | 存一个档 | 游戏存档 |
| **push** | 把存档上传到 GitHub | 把存档传到云盘 |
| **pull** | 把别人上传的存档拉下来 | 从云盘下载 |

**你平时的工作循环就三步：**

```
改代码 → commit（存本地档）→ push（传 GitHub）
```

---

## 三、你们现在的状态（我已经查过）

```
✓ git 已安装（2.55.0）
✗ 没设置身份（user.name / user.email）
✗ 项目目录还没初始化成 git 仓库
✗ 还没登录 GitHub（本机）
✗ GitHub 仓库还没建
```

**所以要按顺序做下面的事。**

---

## 四、第一步：一次性设置身份（每台电脑一次）

这是**最容易被忽略、但最容易翻车**的一步。

```powershell
git config --global user.name "你的真名"
git config --global user.email "你的GitHub注册邮箱"
```

**两个关键点：**

```
① user.name 用真名（或 学号+名字）
   ★ 因为老师要靠 commit 上的名字对应到「是谁」

② user.email 必须填 GitHub 账号绑定的那个邮箱
   ★ 如果填错，你 push 上去的 commit 不会关联到你的 GitHub 账号
   ★ 老师在 contributors（贡献者）里就看不到你，白干
```

**⚠️ 3 个人都要各自在自己电脑上做这一步，用各自的账号。**

---

## 五、第二步：组长建仓库 + 首次提交

### 5.1 本地初始化（在项目目录里）

```powershell
cd "D:\college documents\python数据分析 项目"

# 1. 初始化仓库
git init

# 2. 创建 .gitignore（排除不该传的文件，见第六节）
# （这个文件我会帮你们写）

# 3. 添加所有文件
git add .

# 4. 第一次存档
git commit -m "初始提交：题1 无人机遥测分析全流程代码与文档"
```

### 5.2 建 GitHub 远程仓库

```
1. 浏览器打开 https://github.com
2. 登录组长账号
3. 右上角 + 号 → New repository
4. Repository name 填：例如 dsh-drone-telemetry（随便，英文）
5. 选 Private（私有）或 Public（公开）——见下方建议
6. 不要勾选 "Add a README"（我们要 push 已有的）
7. 点 Create repository
```

### 5.3 关联并推送

```powershell
git remote add origin https://github.com/组长账号/仓库名.git
git branch -M main
git push -u origin main
```

**push 时会弹出登录框，用组长账号登录。** 之后本机会记住。

---

## 六、哪些文件要传、哪些不要（.gitignore）

你们项目现在的文件：

```
要传（代码 + 文档 + 图）：
  *.py          9 个脚本
  *.md          5 个说明文档 + 思路日志
  *.png         总览图 + 关系图/

不传（数据，能重新生成或课程提供）：
  题1_无人机飞行遥测.csv      原始数据（课程发的）
  题1_标注版*.csv             中间产物（跑脚本能重新生成）
  异常检测_分组明细.csv        中间产物
```

**理由：**
```
· Git 管的是「代码」，不是「数据」
· 中间 CSV 都能用脚本重新生成，传了徒增仓库体积
· 原始数据是课程给的，传上去可能涉及版权
```

**对应 .gitignore 内容：**

```
*.csv
```

一行就够了（你们项目里所有 CSV 都是数据，没有需要手写维护的 CSV）。

---

## 七、3 人协作：这是重点

### 7.1 最简单的协作约定（不搞分支，减少出错）

```
· 一共就一个 main 分支，3 人都往上推
· 约定：每人只改自己负责的脚本文件，不碰别人的文件
  ★ 只要不碰同一个文件，就不会冲突
· 每次 push 前，先 pull 一下同步别人的更新
```

### 7.2 每人负责一块，commit 自己那块

**这是「分工对应提交记录」的落地方式。** 举例（你们可以按实际分工调）：

| 成员 | 负责模块 | 对应的文件 |
|---|---|---|
| 甲 | 数据清洗与标记 | step3_mark_data.py, step3a_voltage_dip.py |
| 乙 | 阶段识别与电池 | step4_stages_v3.py, step4a_explore_stages.py, step5_battery_stages.py |
| 丙 | 异常检测与可视化 | step6_anomaly_detect.py, plot_relations.py, stepA_height_jumps.py |

**每个人在自己电脑上，commit 自己负责的文件，然后 push。** 这样 GitHub 上的提交记录自然就对应上了。

### 7.3 组员的操作流程（在组长 push 之后）

```powershell
# 1. 组员把仓库拉到自己电脑
git clone https://github.com/组长账号/仓库名.git

# 2. 进目录，设置自己的身份（如果还没设过全局身份）
cd 仓库名
git config user.name "组员真名"
git config user.email "组员GitHub邮箱"

# 3. 改自己负责的脚本
# ...编辑代码...

# 4. 存档 + 上传
git add 自己改的文件
git commit -m "描述：我改了什么"
git push
```

---

## 八、常见坑（新手必踩，提前知道）

| 坑 | 现象 | 解决 |
|---|---|---|
| email 填错 | push 后 contributors 里没有你 | 改 email 后重新 commit |
| 忘了先 pull | push 被拒（rejected） | 先 `git pull` 再 push |
| 改了别人的文件 | 冲突（conflict） | 约定好每人只管自己的文件 |
| push 时反复要密码 | 没记住登录 | 装 GitHub 登录缓存，或改用 SSH |
| 传了大 CSV | 仓库 6MB+ | 用 .gitignore 排除 |

---

## 九、这门课 Git 部分的「及格线」

**老师真正要看的就三样：**

```
① 附录里有一个 GitHub 仓库链接，能点开
② 仓库里有代码，有 commit 历史（不是一次性的空壳）
③ contributors 里有 3 个人（不是 1 个人）
```

**做到这三点就稳了。** 不需要学分支、merge、rebase 这些——对这门课用不上。

---

## 十、现在最需要先定的三件事

```
① 3 个人是否都有 GitHub 账号？（没有的去注册，免费）
② 谁是组长？（组长建仓库）
③ 分工定了吗？（决定谁 commit 哪些文件）
```

**定完这三件，就可以开始实操了。我可以一步步帮你把本地的 init + 首次 commit 做掉。**
