## 注意：

1.在flts目录下运行，并确保FAULTS命令在电脑的path路径中

2.请确保flts文件中的
!layer 4 to layer 7
类型的注释字段存在，否则transition字段识别异常。


# Magia_faults_GUI

简洁的 PyQt5 GUI，用于查看与编辑 Faults 软件使用的 .flts 配置文件，并运行 Faults 生成并显示模拟的 XRD 谱图。

## 功能概述
- 解析 .flts 文件（TITLE、INSTRUMENTAL AND SIZE BROADENING、STRUCTURAL、STACKING、TRANSITIONS、CALCULATION / SIMULATION 等段落）。
- 在图形界面中以可编辑表单显示主要参数（例如 Wavelength、Aberrations、Pseudo-Voigt、结构层与原子、STACKING、TRANSITIONS 下的 LT / FW 等）。
- 支持对特殊参数的智能写回：
  - Aberrations 仅更新前三个数值；
  - Pseudo-Voigt 仅允许修改前 7 个参数并保留 TRIM 标记；
  - TRANSITIONS 下的 LT/FW 行只更新本行并自动删除多余的独立“0”行；
  - STACKING 中 RECURSIVE / INFINITE 支持多行/第二行编辑。
- 提供“全局 FW”面板，可将一组 FW 值应用到所有 TRANSITIONS 中的 FW 条目。
- 将修改写回 .flts 文件后调用外部 Faults 可执行程序运行计算，并寻找最新生成的 .dat 文件读取并用 matplotlib 展示模拟谱图。

## 适用场景
开发者或研究人员使用 Faults 进行模拟时快速调整 .flts 参数并实时查看结果的轻量 GUI 工具。

## 依赖
- Python 3.8+
- PyQt5
- numpy
- matplotlib
- 外部命令行可执行程序 `Faults`（需在 PATH 中或在工作目录可调用）

安装依赖示例（Windows，PowerShell / CMD）：
```powershell
python -m pip install pyqt5 numpy matplotlib
```

## 运行（示例，假设在项目目录）
1. 将 Faults 可执行程序保证可从命令行调用（加入 PATH 或放在同一目录）。
2. 编辑代码顶部的默认文件名（可直接在 GUI 调用 main 前替换）或将目标 .flts 放到运行目录并修改 main() 中路径。
3. 运行：
```powershell
python Magia_FAULTS_GUI.py
```

## 文件说明
- Magia_FAULTS_GUI.py — 主程序和 GUI，实现 .flts 解析、编辑、写回与调用 Faults 并显示 .dat 谱图。
- （运行后）生成的 .dat 文件由程序自动搜索并用于绘图显示。

## 注意事项
- 本工具不自带 Faults；Faults 是外部专用程序，需由用户自行安装并可通过命令行调用。
- 在写回 .flts 前请确保已备份原始文件以防意外覆盖。
- 解析器对 .flts 文件格式有基本假设（常见段落与关键字）；对非常规或极为自由的格式可能解析不完全。

## 许可
MIT，知识应该共享而不是商用。

欢迎在 GitHub 上提交 issue 与 PR。  
