import threading
import tkinter as tk
from tkinter import ttk

from ..config import PIPELLM_BASE_URL, PIPELLM_MODEL, U2NET_MODEL_DIR, U2NET_MODEL_PATH
from ..image_service import get_rembg_state
from .image_pages import _build_scrollable_page
from ..widgets import RoundedButton


def build_settings_page(app):
    self = app
    self._clear_content()
    from tkinter import scrolledtext as _st

    inner = _build_scrollable_page(self.content, "#1e1e2e")

    tk.Label(inner, text="⚙️ 设置", font=self.fonts["title"],
             bg="#1e1e2e", fg="#cba6f7").pack(anchor="w", pady=(12, 2))

    def make_section(parent, title):
        frame = tk.Frame(parent, bg="#313244", padx=16, pady=12)
        frame.pack(fill="x", pady=(12, 0))
        tk.Label(
            frame,
            text=title,
            bg="#313244",
            fg="#89b4fa",
            font=self.fonts["section"],
        ).pack(anchor="w", pady=(0, 10))
        return frame

    sec1 = make_section(inner, "PipeLLM API Key（本地 OCR / AI 辅助）")
    box = tk.Frame(sec1, bg="#313244")
    box.pack(fill="x")
    box.grid_columnconfigure(1, weight=1)

    tk.Label(box, text="API Key:", bg="#313244", fg="#cdd6f4",
             font=self.fonts["body"]).grid(row=0, column=0, sticky="w", pady=6)
    key_var = tk.StringVar(value=self.pipellm_api_key)
    key_entry = tk.Entry(box, textvariable=key_var, show="•",
                         bg="#45475a", fg="#cdd6f4", insertbackground="white",
                         relief="flat", font=self.fonts["body"])
    key_entry.grid(row=0, column=1, sticky="ew", pady=6, padx=(12, 0))

    show_var = tk.BooleanVar(value=False)

    def toggle_show():
        key_entry.config(show="" if show_var.get() else "•")

    tk.Checkbutton(box, text="显示", variable=show_var, command=toggle_show,
                   bg="#313244", fg="#cdd6f4", selectcolor="#45475a",
                   activebackground="#313244", font=self.fonts["small"]).grid(row=0, column=2, padx=8)

    tk.Label(box, text="Base URL:", bg="#313244", fg="#cdd6f4",
             font=self.fonts["body"]).grid(row=1, column=0, sticky="w", pady=4)
    tk.Label(box, text=f"{PIPELLM_BASE_URL}  |  模型: {PIPELLM_MODEL}",
             bg="#313244", fg="#6c7086", font=self.fonts["small"], justify="left", wraplength=720).grid(row=1, column=1, sticky="w", padx=(12, 0))

    api_status = tk.StringVar(value="")
    tk.Label(box, textvariable=api_status, bg="#313244",
             font=self.fonts["small"], justify="left", wraplength=820).grid(row=2, columnspan=3, sticky="w", pady=(2, 0))

    def save_key():
        key = key_var.get().strip()
        if not key:
            api_status.set("❌ PipeLLM API Key 不能为空")
            return
        self.pipellm_api_key = key
        if self._save_api_key(key):
            api_status.set("✅ 已保存 PipeLLM API Key")
        else:
            api_status.set("⚠️ 保存失败，但当前会话仍会使用该 Key")

    def test_key():
        key = key_var.get().strip()
        if not key:
            api_status.set("❌ 请先输入 PipeLLM API Key")
            return
        api_status.set("⏳ 测试中...")

        def task():
            try:
                import anthropic

                client = anthropic.Anthropic(api_key=key, base_url=PIPELLM_BASE_URL)
                client.messages.create(
                    model=PIPELLM_MODEL,
                    max_tokens=16,
                    messages=[{"role": "user", "content": "reply: ok"}],
                )
                self.after(0, lambda: api_status.set("✅ PipeLLM API Key 可用"))
            except Exception as exc:
                self.after(0, lambda: api_status.set(f"❌ 测试失败：{str(exc)[:80]}"))

        threading.Thread(target=task, daemon=True).start()

    btn_row1 = tk.Frame(sec1, bg="#313244")
    btn_row1.pack(anchor="w", pady=(10, 0))
    RoundedButton(btn_row1, text="保存", font=self.fonts["button"], variant="primary", min_width=88, command=save_key).pack(side="left", padx=(0, 10))
    RoundedButton(btn_row1, text="测试连接", font=self.fonts["button"], variant="accent", min_width=110, command=test_key).pack(side="left")

    sec2 = make_section(inner, "证件照换白底模型（rembg）")

    def check_rembg_status():
        state = get_rembg_state()
        if state == "no_rembg":
            return "❌ rembg 未安装", False
        if state == "ready":
            import os

            size_mb = os.path.getsize(U2NET_MODEL_PATH) / 1024 / 1024
            return f"✅ 已就绪（模型文件 {size_mb:.0f}MB）", True
        return "⚠️ rembg 已安装，但模型尚未下载", True

    status_text, is_ready = check_rembg_status()
    rembg_status = tk.StringVar(value=status_text)
    rembg_status_label = tk.Label(sec2, textvariable=rembg_status,
                                  bg="#313244", fg="#a6e3a1" if is_ready else "#f38ba8",
                                  font=self.fonts["section"])
    rembg_status_label.pack(anchor="w", pady=(0, 4))

    def refresh_status():
        text, ready = check_rembg_status()
        rembg_status.set(text)
        rembg_status_label.config(fg="#a6e3a1" if ready else "#f38ba8")

    RoundedButton(sec2, text="刷新状态", font=self.fonts["small"], variant="secondary", min_width=96, command=refresh_status).pack(anchor="w", pady=(0, 8))

    tk.Label(sec2,
             text="rembg 使用 U2Net 模型自动识别人像轮廓，适合复杂背景、阴影和发丝边缘。",
             bg="#313244", fg="#6c7086", font=self.fonts["small"], justify="left", wraplength=820).pack(anchor="w", pady=(0, 10))

    install_log = _st.ScrolledText(sec2, height=6, bg="#181825", fg="#a6e3a1",
                                   font=self.fonts["mono"], wrap="word")
    install_log.pack(fill="x")

    def install_rembg():
        install_log.delete("1.0", "end")
        mirrors = [
            ("官方", "https://pypi.org/simple", "pypi.org"),
            ("清华", "https://pypi.tuna.tsinghua.edu.cn/simple", "pypi.tuna.tsinghua.edu.cn"),
            ("阿里云", "https://mirrors.aliyun.com/pypi/simple/", "mirrors.aliyun.com"),
        ]

        def task():
            import subprocess
            import sys

            for name, mirror, host in mirrors:
                self.after(0, lambda n=name: install_log.insert("end", f"\n尝试 {n} 镜像...\n"))
                proc = subprocess.Popen(
                    [
                        sys.executable, "-m", "pip", "install", "rembg[cpu]",
                        "-i", mirror, "--trusted-host", host, "--timeout", "60",
                        "--retries", "2", "--break-system-packages",
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                for line in proc.stdout:
                    self.after(0, lambda current=line: install_log.insert("end", current))
                proc.wait()
                if proc.returncode == 0:
                    self.after(0, lambda n=name: (
                        install_log.insert("end", f"\n✅ 通过 {n} 安装成功\n"),
                        rembg_status.set("✅ rembg 已安装，请继续下载模型"),
                    ))
                    return
            self.after(0, lambda: install_log.insert("end", "\n❌ 所有镜像均安装失败\n"))

        threading.Thread(target=task, daemon=True).start()

    def download_model():
        install_log.delete("1.0", "end")
        install_log.insert("end", "开始下载 U2Net 模型（约 170MB）...\n")

        def task():
            import os
            import requests

            os.makedirs(U2NET_MODEL_DIR, exist_ok=True)
            urls = [
                ("GitHub", "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx"),
                ("HuggingFace", "https://huggingface.co/danielgatis/rembg/resolve/main/u2net.onnx"),
            ]

            for source_name, url in urls:
                try:
                    self.after(0, lambda name=source_name: install_log.insert("end", f"尝试从 {name} 下载...\n"))
                    response = requests.get(url, stream=True, timeout=30)
                    response.raise_for_status()
                    with open(U2NET_MODEL_PATH, "wb") as handle:
                        for chunk in response.iter_content(chunk_size=1024 * 256):
                            if chunk:
                                handle.write(chunk)
                    self.after(0, lambda: (
                        install_log.insert("end", "✅ 模型下载完成\n"),
                        refresh_status(),
                    ))
                    return
                except Exception as exc:
                    self.after(0, lambda name=source_name, err=str(exc): install_log.insert("end", f"❌ {name} 失败：{err}\n"))
                    if os.path.exists(U2NET_MODEL_PATH):
                        os.remove(U2NET_MODEL_PATH)

            self.after(0, lambda: install_log.insert("end", "❌ 所有下载源均失败\n"))

        threading.Thread(target=task, daemon=True).start()

    btn_row2 = tk.Frame(sec2, bg="#313244")
    btn_row2.pack(anchor="w", pady=(10, 0))
    RoundedButton(btn_row2, text="安装 rembg", font=self.fonts["button"], variant="purple", min_width=120, command=install_rembg).pack(side="left", padx=(0, 10))
    RoundedButton(btn_row2, text="下载模型", font=self.fonts["button"], variant="warning", min_width=120, command=download_model).pack(side="left")

    sec3 = make_section(inner, "使用说明")
    for line in [
        "• PipeLLM API Key 用于本地 OCR 和通用 AI 辅助能力。",
        "• rembg 用于人物抠图和证件照白底处理。",
        "• rembg 模型首次使用时会缓存到 ~/.u2net/u2net.onnx。",
        "• 图片工具适合批量处理，证件照换白底适合单张精修。",
    ]:
        tk.Label(sec3, text=line, bg="#313244", fg="#6c7086",
                 font=self.fonts["small"], justify="left", wraplength=820).pack(anchor="w", pady=2)
