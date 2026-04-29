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
  - 自动裁剪护照 / 人像区域
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

### 先安装 Python

推荐方式：

1. 打开 `https://www.python.org/downloads/macos/`
2. 下载并安装 `Python 3.11`
3. 安装完成后，在终端里确认：

```bash
python3 --version
python3 -c "import tkinter; print(tkinter.TkVersion)"
```

如果第二条命令能正常输出版本号，说明当前 Python 自带的 `tkinter` 可用。

也可以用 Homebrew 安装：

```bash
brew install python@3.11
```

### 再运行项目源码

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 koko_gui.py
```

也可以运行包入口：

```bash
python3 -m koko_app
```

说明：

- 需要本机 `python3` 可用
- 需要当前 Python 自带可用的 `tkinter`
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

## macOS 说明

项目代码本身基本跨平台，但 `.app` 需要在 macOS 上单独构建。Windows 不能可靠地产出最终可分发的 macOS 桌面应用。

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
