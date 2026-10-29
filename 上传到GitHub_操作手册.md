# 把项目上传到 GitHub · 操作手册

> 针对本项目（题1 无人机遥测分析）的实际条件编写
> 你的环境：Git 2.55.0 + Git Credential Manager **都已装好** → push 时自动弹浏览器登录，不用配 token

---

## 零、你的现状（已确认）

```
✓ Git 已安装             C:\Program Files\Git\cmd\git.exe
✓ Credential Manager 已装 C:\Program Files\Git\mingw64\bin\git-credential-manager.exe
✗ user.name / user.email 未设置
✗ 项目目录未初始化
✗ 尚无 GitHub 仓库
✓ .gitignore 已创建（已排除 *.csv 约 6.3 MB 数据）
```

**准备上传的内容约 2.2 MB：**

```
*.py   9 个脚本
*.md   7 个文档（含报告 Markdown）
*.png  总览图 + 关系图/ 内 9 张
*.docx 报告 Word 版
```

**被排除的：5 个 CSV（原始数据 + 中间产物，共 6.3 MB）**

---

## 一、第一步：设置身份（**最关键，做错会白干**）

打开 PowerShell，执行：

```powershell
git config --global user.name "你的真名"
git config --global user.email "你的GitHub注册邮箱"
```

### ⚠️ 两个必须注意的点

**① `user.email` 必须填 GitHub 账号绑定的那个邮箱**

```
如果填错 → push 上去的 commit 不关联到你的账号
        → 老师在仓库的 Contributors 里看不到你
        → 「分工与提交记录对应」这条要求就落空了
```

**② `user.name` 建议用真名**

```
因为老师要靠 commit 上的名字对应到「是谁做了哪部分」
★ 用真名（或「学号-姓名」）最稳妥
```

**验证是否设置成功：**

```powershell
git config --global --list
```

应能看到 `user.name=...` 和 `user.email=...` 两行。

---

## 二、第二步：本地初始化仓库

```powershell
cd "D:\college documents\python数据分析 项目"

# 初始化仓库
git init

# 查看哪些文件会被纳入（此时应该只有 .py/.md/.png/.docx，没有 .csv）
git status

# 添加全部文件
git add .

# 第一次提交
git commit -m "初始提交：题1 无人机遥测分析全流程"
```

**★ 执行 `git status` 时请确认：**

```
应该出现：.gitignore、*.py、*.md、*.png、.docx
不应该出现：任何 .csv
```

如果 `.csv` 出现了，说明 `.gitignore` 没生效（文件名拼写、或位置不对）。

**★ 如果 `git init` 后默认分支名是 `master`，改一下（GitHub 默认用 main）：**

```powershell
git branch -M main
```

---

## 三、第三步：在 GitHub 上建仓库（网页操作）

```
1. 浏览器打开 https://github.com
2. 登录你的账号（没有账号就去 Sign up 注册，免费）
3. 右上角「+」 → New repository
4. Repository name 填一个英文名，例如：drone-telemetry-analysis
5. 选择 Public（公开）或 Private（私有）
   ★ 建议 Private —— 数据和课程信息不外泄
   ★★ 但 Private 需要确认老师能看（附录里给链接，老师可能没有权限）
   ★★★ 折中：先用 Private，交作业前改 Public，或把老师加为 Collaborator
6. ⚠️ 下面的三个复选框（README / .gitignore / license）全部【不要勾】
   ★ 因为本地已经有内容了，勾了会造成冲突
7. 点 Create repository
```

**创建成功后，页面会显示仓库地址，形如：**

```
https://github.com/你的用户名/drone-telemetry-analysis.git
```

**★ 把这个地址复制下来，下一步要用。**

---

## 四、第四步：关联远程仓库并推送

回到 PowerShell（仍在项目目录）：

```powershell
# 关联远程仓库（把 URL 换成你自己的）
git remote add origin https://github.com/你的用户名/drone-telemetry-analysis.git

# 推送
git push -u origin main
```

### ★ 此时会发生什么

```
1. 弹出 Git Credential Manager 的登录窗口
2. 选「Sign in with your browser」
3. 浏览器打开 GitHub 授权页 → 点「Authorize」
4. 回到 PowerShell，推送自动完成

★ 之后本机会记住凭据，第二次 push 不用再登录
```

**推送成功的输出大致是：**

```
Enumerating objects: 35, done.
Writing objects: 100% (35/35), 2.2 MiB
To https://github.com/...
 * [new branch]      main -> main
branch 'main' set up to track 'origin/main'.
```

---

## 五、第五步：验证

```powershell
# 查看提交历史
git log --oneline

# 查看远程地址
git remote -v

# 查看最后一次提交改了哪些文件
git show --stat HEAD
```

**然后浏览器刷新你的仓库页面，应该能看到：**

```
✓ 9 个 .py 文件
✓ 7 个 .md 文档
✓ 关系图/ 目录（9 张 PNG）
✓ 总览图 + 报告 Word
✓ 没有 .csv（被 .gitignore 排除）
✓ 提交历史里有你的 commit
```

---

## 六、以后日常怎么用（改了就传）

**核心循环只有三步：**

```powershell
git add .
git commit -m "说明这次改了什么"
git push
```

**★ 建议在 `commit -m` 里写清楚改了什么，例如：**

```powershell
git commit -m "修正阶段识别阈值，S2 下降段边界从 899.1 调到 900.0"
```

**★ 不要写「update」「修改」这种毫无信息量的说明——老师会看提交记录，写清楚显得认真。**

---

## 七、★★★ 三个人怎么协作（这是课程要求的关键）

**老师明确写了：「成员分工所写的各人负责模块**应能与提交记录对应**」。**

### 现状问题

```
如果只有你一个人 commit → 仓库的 Contributors 只有 1 人
→ 老师会怀疑「是不是一个人包办」
```

### 正确做法

**推荐方案：一个仓库，三个人都是 Collaborator，各自 commit 自己负责的文件。**

**步骤：**

```
1. 你在 GitHub 仓库页面 → Settings → Collaborators
   → Add people → 输入组员的 GitHub 用户名 → 邀请
2. 组员接受邀请
3. 组员在自己电脑上：
   git clone https://github.com/你的用户名/仓库名.git
   cd 仓库名
   git config user.name  "组员真名"
   git config user.email "组员GitHub邮箱"
4. 组员改自己负责的脚本 → git add → git commit → git push
```

### 避免冲突的约定（很重要）

```
★ 每人只改自己负责的文件，不要碰别人的
★★ 每次开始干活前，先 git pull 同步最新内容
★★★ 如果 push 报错「rejected」，先 git pull 再 push
```

### 分工与文件的对应建议

| 成员 | 负责模块 | 对应文件 |
|---|---|---|
| 甲 | 数据清洗与标记 | `step3_mark_data.py`、`step3a_voltage_dip.py`、`stepA_height_jumps.py` |
| 乙 | 阶段识别与电池 | `step4a_explore_stages.py`、`step4_stages_v3.py`、`step5_battery_stages.py` |
| 丙 | 异常检测与可视化 | `step6_anomaly_detect.py`、`plot_relations.py`、`md2docx.py` |

**★ 这样每个人的 commit 记录里就只有自己那几个文件，和报告第 8 章的分工表天然对应。**

---

## 八、常见报错与解决

| 报错 | 原因 | 解决 |
|---|---|---|
| `fatal: not a git repository` | 不在项目目录 | `cd` 到项目目录再执行 |
| `remote origin already exists` | 已经关联过了 | `git remote set-url origin 新地址` |
| `failed to push some refs` / `rejected` | 远程有你本地没有的提交 | `git pull --rebase` 后再 `git push` |
| `Please tell me who you are` | 身份没设置 | 回到第一步 |
| `Support for password authentication was removed` | 用了密码而不是 token | 删掉旧凭据：控制面板→凭据管理器→删除 github 相关项，重新 push |
| 中文文件名显示乱码 | git 默认转义 | `git config --global core.quotepath false` |
| 误把 CSV 提交了 | .gitignore 没生效 | `git rm --cached *.csv` 再 commit |

---

## 九、附录里要写什么

报告第 9.1 节「代码仓库」填：

```
GitHub 仓库链接：https://github.com/你的用户名/drone-telemetry-analysis
```

**★ 如果仓库是 Private，记得在报告里说明「已邀请老师/助教为 Collaborator」，或者交作业前改成 Public。**

---

## 十、一句话总结

```powershell
# 一次性（做一次）
git config --global user.name "真名"
git config --global user.email "GitHub邮箱"
cd "D:\college documents\python数据分析 项目"
git init
git branch -M main
git add .
git commit -m "初始提交"

# 建 GitHub 仓库（网页），然后
git remote add origin https://github.com/用户名/仓库名.git
git push -u origin main

# 以后每次改完
git add . && git commit -m "改了什么" && git push
```
