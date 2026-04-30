# 本地图片与 OCR 工具箱

一个基于 `Tkinter` 的本地桌面工具，主要用于：

- 批量处理护照 PDF / 图片
- 自动裁剪和压缩图片
- 证件照换白底
- 使用 PipeLLM 进行 OCR / AI 辅助识别

## Python 版本

推荐使用：

- `Python 3.11`

也可以尝试：

- `Python 3.12`

不建议优先使用过新的 `Python 3.13`，以免遇到 `numpy`、`scipy`、`PyMuPDF` 等依赖的兼容性问题。

## 当前功能

- 图片工具
  - 批量扫描文件夹
  - PDF 转 JPG
  - 自动裁剪护照区域
  - 图片压缩到指定大小
  - 可选换白底
- 设置
  - 保存 PipeLLM API Key
  - 测试 PipeLLM 连接
  - 安装 `rembg`
  - 下载 `U2Net` 模型

## 安装

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 运行

### 方式一：直接运行启动文件

```powershell
python koko_gui.py
```

### 方式二：运行包入口

```powershell
python -m koko_app
```

## macOS 源码运行

如果不打包成 `.app`，在 macOS 上直接运行源码通常更稳：

### 推荐运行标准

建议使用以下组合：

- `Python 3.11`
- `Tk 8.6`

如果 `Tk` 版本过旧，或者当前 `Python 3.11` 没有正确接上 `tkinter`，界面在 macOS 上可能会出现：

- 页面切换后控件残留 / 叠加
- 布局错位
- 原生按钮样式过亮、和 Windows 表现差异很大

这次在本机实际验证通过的方案是：

- Homebrew `python@3.11`
- Homebrew `python-tk@3.11`
- Homebrew `tcl-tk@8`

仅安装 `python@3.11` 不一定够用；有些机器上它可以运行 Python，但 `import tkinter` 会失败，或者会退回到不合适的 Tk 版本。

### 先检查当前环境

先在终端确认：

```bash
python3.11 --version
python3.11 -c "import tkinter; print(tkinter.TkVersion)"
```

期望结果：

- 能正常 `import tkinter`
- 输出的 `TkVersion` 为 `8.6`

如果这里报错，或者版本不是 `8.6`，不要继续按旧流程直接跑项目。

### 用 Homebrew 安装推荐环境

如果你的 Mac 还没有安装 Homebrew，可以先执行：

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

然后安装：

```bash
brew install python@3.11 python-tk@3.11 tcl-tk@8
```

安装完成后再次确认：

```bash
python3.11 -c "import tkinter; print(tkinter.TkVersion)"
```

如果输出是 `8.6`，再继续下面步骤。

### 再运行项目源码

推荐单独使用一个 macOS 运行环境，例如：

```bash
python3.11 -m venv .venv311
source .venv311/bin/activate
pip install -r requirements.txt
python koko_gui.py
```

也可以运行包入口：

```bash
python -m koko_app
```

### 之前的旧流程为什么在这台机器上跑不通

之前 `README` 里写的思路是：

- 安装 `python@3.11`
- 建虚拟环境
- `pip install -r requirements.txt`
- `python koko_gui.py`

这在某些 macOS 机器上不成立，原因是：

- `python3.11` 可能没有可用的 `tkinter`
- 或者实际连到的不是合适的 `Tk 8.6`
- 项目本身能装依赖，但 GUI 启动后布局和行为会异常

在这台机器上，实际情况就是：

- Homebrew 的 `python3.11` 一开始不能正常加载 `tkinter`
- 系统自带 Python 虽然能跑 `tkinter`，但对应的是旧版 `Tk 8.5`
- 旧版 `Tk 8.5` 会导致界面和 Windows 差异明显，甚至出现页面切换异常

所以现在推荐把 macOS 运行标准固定为：

```bash
Python 3.11 + Tk 8.6
```

说明：

- 不建议在 macOS 上继续依赖系统自带旧版 `Tk`
- 推荐先验证 `python3.11 -c "import tkinter; print(tkinter.TkVersion)"`
- 如果要用 OCR，在“设置”中填写 `PipeLLM API Key`
- 如果要获得更好的白底处理效果，建议额外安装 `rembg[cpu]` 并下载 `U2Net` 模型

## 可选依赖

- `rembg[cpu]`
  用于更高质量的人像抠图和白底处理
- `pdf2image`
  作为 `PyMuPDF` 之外的 PDF 转图备用方案
- `PipeLLM API Key`
  用于 OCR / AI 辅助能力

## 分享给别人

如果要发给普通用户，建议分享打包后的 Windows 应用，而不是源码。

### Windows 打包

```powershell
.\build_windows.ps1
```

打包完成后，把整个目录发给别人：

- `dist\LocalImageOcrToolbox\`

不要只发送 `.exe`，程序依赖同目录下的 `_internal` 和其他运行文件。

### 首次使用说明

- 基础图片处理功能可直接使用
- OCR 功能需要在“设置”中填写 `PipeLLM API Key`
- 白底处理最佳效果依赖：
  - 安装 `rembg[cpu]`
  - 下载 `U2Net` 模型

### 当前批量处理规则

- 支持处理护照 `PDF / JPG / JPEG / PNG`
- `PDF` 会先转成图片，再按护照页进行裁剪
- 普通图片不会全部强制裁剪
  - 只有判断为疑似护照页的图片才会执行护照裁剪
  - 证件照默认不走护照裁剪
- 选择“直接覆盖原文件”时：
  - 图片会覆盖原图
  - `PDF` 不会覆盖回 PDF，而是输出为同名 `JPG`

## macOS 说明

项目代码本身基本跨平台，但 `.app` 需要在 macOS 上单独构建。Windows 不能可靠地产出最终可分发的 macOS 桌面应用。

当前仓库里的界面调整没有改动 Windows 打包脚本，也没有引入仅限 macOS 的运行时依赖。按钮和布局改动仍然基于标准 `Tkinter` / `Canvas`，原则上不会阻断 Windows 部署。

但需要注意：

- Windows 上的视觉样式会和之前不一样，因为按钮已经改成项目自绘样式
- `PyInstaller` 打包前，仍然建议在 Windows 机器上实际跑一遍界面并做一次打包验证

## 项目结构

- `koko_gui.py`
  薄启动入口
- `build_windows.ps1`
  Windows 一键打包脚本
- `local_image_ocr_toolbox.spec`
  `PyInstaller` 打包配置
- `koko_app/config.py`
  运行时常量
- `koko_app/config_store.py`
  本地配置读写
- `koko_app/image_service.py`
  图片处理能力
- `koko_app/ocr_service.py`
  OCR / PipeLLM 能力
- `koko_app/pages/`
  GUI 页面模块
