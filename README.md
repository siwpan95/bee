# Bee（蜜蜂挂机 RPG / 无尽的进度条）

一款蜜蜂主题的挂机 RPG（放置进度条）游戏，支持系统托盘与实时音频。

## 语言 / 类型
- Python / tkinter 图形界面挂机游戏（含系统托盘）

## 目录要点
- `main.pyw` —— 窗口入口
- `src/` —— app、config、sim_core、resources 等模块
- `data/`、`docs/`、`tests/`、`godot/`（Godot 相关资源）
- `build_exe.py`、`BeeIdleRPG.spec` —— 打包脚本；`excel_to_json.py`、`gen_new_excels.py` 等数据工具
- `无尽的进度条3.0.exe` —— 已打包可执行文件

## 运行方式与依赖
- 运行：`F:\Python314\python.exe main.pyw`
- 依赖（`requirements.txt`）：numpy、scipy（音频合成，必需）；pystray、Pillow、openpyxl、sounddevice（可选）

## 测试状态
- py_compile 语法检查通过（全部 .py）
- pytest：`python -m pytest tests`（7 个用例全绿，含黄金基准、IPC 桥接；基准生成器 `tests/test_sim_reference.py`）
- 冒烟测试：`python smoke_test.py [对局数]`（DDA 战斗模拟，词缀/稀有度/Boss 全覆盖）
- 回归脚本：`python test_refactor.py`（DDA 语义）、`python test_tag_system.py`（标签系统）
- 无头引擎 2 小时长时模拟通过（战斗/商店/合成/地牢/区域推进/阵亡重开/名人堂结算）
- GUI 窗口游戏：未运行（无显示环境，仅无头验证）

## PQ 致敬特性（v3 借鉴 Progress Quest）
- 戏谑前缀池：107 个物品前缀兼敌人词缀（含「双倍伍基人的」「巫毒公主的」「非酋的」等 PQ 风格梗，同步 Excel 前缀表）
- 精炼叙事：环境氛围每场战斗只播报一次，吸血状态不再逐帧刷屏，战斗日志密度向 PQ 靠拢（黄金基准 145 行 → 17 行）
- 本地名人堂：阵亡自动结算生涯战绩至存档旁 `hall_of_fame.json`（最高等级/击杀/金币/最长存活，跨重开累积并播报新纪录）
