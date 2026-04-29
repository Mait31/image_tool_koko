import tkinter as tk
from tkinter import ttk

from ..image_service import get_rembg_state
from ..widgets import RoundedButton


def _build_scrollable_page(parent, bg):
    canvas = tk.Canvas(parent, bg=bg, highlightthickness=0)
    vsb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    vsb.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    outer = tk.Frame(canvas, bg=bg)
    inner = tk.Frame(outer, bg=bg)
    inner.pack(fill="x", expand=True, padx=16, pady=0)
    win_id = canvas.create_window((0, 0), window=outer, anchor="nw")

    def sync_scrollregion(_event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def resize_inner(event):
        width = min(max(event.width - 16, 760), 980)
        canvas.itemconfig(win_id, width=event.width)
        inner.configure(width=width)

    def on_mousewheel(event):
        if not canvas.winfo_exists():
            return
        delta = getattr(event, "delta", 0)
        if delta:
            canvas.yview_scroll(int(-1 * (delta / 120)), "units")
            return
        if getattr(event, "num", None) == 4:
            canvas.yview_scroll(-1, "units")
        elif getattr(event, "num", None) == 5:
            canvas.yview_scroll(1, "units")

    def bind_mousewheel(_event=None):
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        canvas.bind_all("<Button-4>", on_mousewheel)
        canvas.bind_all("<Button-5>", on_mousewheel)

    def unbind_mousewheel(_event=None):
        canvas.unbind_all("<MouseWheel>")
        canvas.unbind_all("<Button-4>")
        canvas.unbind_all("<Button-5>")

    outer.bind("<Configure>", sync_scrollregion)
    canvas.bind("<Configure>", resize_inner)
    canvas.bind("<Enter>", bind_mousewheel)
    canvas.bind("<Leave>", unbind_mousewheel)
    return inner


def _make_section(parent, title, fonts, title_fg="#f9e2af"):
    section = tk.Frame(parent, bg="#313244", padx=12, pady=10)
    section.pack(fill="x", pady=6)
    tk.Label(section, text=title, bg="#313244", fg=title_fg, font=fonts["section"]).pack(
        anchor="w", pady=(0, 8)
    )
    return section


def build_image_tools_page(app):
    self = app
    self._clear_content()
    import io
    import os
    import threading
    import tkinter.ttk as ttk2
    from tkinter import filedialog, messagebox, scrolledtext

    inner = _build_scrollable_page(self.content, "#1e1e2e")

    tk.Label(inner, text="🛠 图片工具", font=self.fonts["title"], bg="#1e1e2e", fg="#f9e2af").pack(
        anchor="w", pady=(12, 2)
    )
    tk.Label(
        inner,
        text="批量处理文件夹内的护照 PDF / 图片：自动裁剪、可选换白底、可选压缩大小。",
        bg="#1e1e2e",
        fg="#6c7086",
        font=self.fonts["small"],
        justify="left",
        wraplength=920,
    ).pack(anchor="w", pady=(0, 10))

    sec1 = _make_section(inner, "选择文件夹", self.fonts)

    folder_var = tk.StringVar(value="")
    folder_label = tk.StringVar(value="（未选择）")
    count_var = tk.StringVar(value="")

    def scan_files(folder):
        result = []
        for root, _, files in os.walk(folder):
            for file_name in files:
                if file_name.lower().endswith((".pdf", ".jpg", ".jpeg", ".png")):
                    result.append(os.path.join(root, file_name))
        return result

    def choose_folder():
        folder = filedialog.askdirectory(title="选择包含护照 PDF / 图片的文件夹")
        if not folder:
            return
        folder_var.set(folder)
        folder_label.set(folder)
        files = scan_files(folder)
        pdfs = [f for f in files if f.lower().endswith(".pdf")]
        imgs = [f for f in files if f.lower().endswith((".jpg", ".jpeg", ".png"))]
        count_var.set(f"找到 PDF: {len(pdfs)} 个，图片: {len(imgs)} 个，共 {len(files)} 个文件")

    row = tk.Frame(sec1, bg="#313244")
    row.pack(fill="x")
    row.grid_columnconfigure(0, weight=1)
    tk.Label(
        row,
        textvariable=folder_label,
        bg="#313244",
        fg="#cdd6f4",
        font=self.fonts["small"],
        anchor="w",
        justify="left",
        wraplength=720,
    ).grid(row=0, column=0, sticky="ew")
    RoundedButton(
        row,
        text="选择文件夹",
        font=self.fonts["button"],
        variant="accent",
        command=choose_folder,
        min_width=110,
    ).grid(row=0, column=1, sticky="e", padx=(12, 0))
    tk.Label(sec1, textvariable=count_var, bg="#313244", fg="#a6e3a1", font=self.fonts["small"]).pack(anchor="w", pady=(4, 0))

    sec2 = _make_section(inner, "处理选项", self.fonts)

    opt_crop = tk.BooleanVar(value=True)
    opt_whitebg = tk.BooleanVar(value=True)
    opt_limit = tk.BooleanVar(value=True)
    opt_subdir = tk.BooleanVar(value=True)
    max_kb_var = tk.IntVar(value=1024)

    tk.Checkbutton(
        sec2,
        text="自动裁剪护照 / 人像区域",
        variable=opt_crop,
        bg="#313244",
        fg="#cdd6f4",
        selectcolor="#45475a",
        activebackground="#313244",
        font=self.fonts["small"],
    ).pack(anchor="w")
    tk.Checkbutton(
        sec2,
        text="自动换白底（适用于人像证件照）",
        variable=opt_whitebg,
        bg="#313244",
        fg="#cdd6f4",
        selectcolor="#45475a",
        activebackground="#313244",
        font=self.fonts["small"],
    ).pack(anchor="w")
    tk.Checkbutton(
        sec2,
        text="压缩到指定大小以内",
        variable=opt_limit,
        bg="#313244",
        fg="#cdd6f4",
        selectcolor="#45475a",
        activebackground="#313244",
        font=self.fonts["small"],
    ).pack(anchor="w")

    size_row = tk.Frame(sec2, bg="#313244")
    size_row.pack(anchor="w", padx=(22, 0))
    tk.Label(size_row, text="最大 KB:", bg="#313244", fg="#6c7086", font=self.fonts["small"]).pack(side="left")
    tk.Entry(size_row, textvariable=max_kb_var, width=8, bg="#45475a", fg="#cdd6f4", relief="flat", font=self.fonts["small"]).pack(
        side="left", padx=4
    )

    tk.Checkbutton(
        sec2,
        text="递归处理子文件夹",
        variable=opt_subdir,
        bg="#313244",
        fg="#cdd6f4",
        selectcolor="#45475a",
        activebackground="#313244",
        font=self.fonts["small"],
    ).pack(anchor="w")

    out_mode = tk.StringVar(value="subfolder")
    tk.Radiobutton(
        sec2,
        text="输出到 processed 子文件夹（推荐）",
        variable=out_mode,
        value="subfolder",
        bg="#313244",
        fg="#cdd6f4",
        selectcolor="#45475a",
        activebackground="#313244",
        font=self.fonts["small"],
    ).pack(anchor="w", pady=(6, 0))
    tk.Radiobutton(
        sec2,
        text="直接覆盖原文件",
        variable=out_mode,
        value="same",
        bg="#313244",
        fg="#f38ba8",
        selectcolor="#45475a",
        activebackground="#313244",
        font=self.fonts["small"],
    ).pack(anchor="w")

    sec3 = _make_section(inner, "处理进度", self.fonts)
    prog_var = tk.StringVar(value="等待开始...")
    summary_var = tk.StringVar(value="")
    tk.Label(sec3, textvariable=prog_var, bg="#313244", fg="#cdd6f4", font=self.fonts["small"]).pack(anchor="w")
    bar = ttk2.Progressbar(sec3, mode="determinate", length=600)
    bar.pack(fill="x", pady=4)
    tk.Label(sec3, textvariable=summary_var, bg="#313244", fg="#a6e3a1", font=self.fonts["section"], justify="left", wraplength=920).pack(anchor="w")

    log_box = scrolledtext.ScrolledText(sec3, height=8, bg="#181825", fg="#cdd6f4", font=self.fonts["mono"], wrap="word", state="disabled")
    log_box.pack(fill="x", pady=(4, 0))

    def log(msg):
        log_box.config(state="normal")
        log_box.insert("end", msg + "\n")
        log_box.see("end")
        log_box.config(state="disabled")

    btn_row = tk.Frame(inner, bg="#1e1e2e")
    btn_row.pack(anchor="w", pady=10)

    start_btn = RoundedButton(
        btn_row,
        text="▶ 开始处理",
        font=self.fonts["button"],
        variant="primary",
        min_width=120,
    )
    start_btn.pack(side="left", padx=(0, 12))
    RoundedButton(
        btn_row,
        text="清空日志",
        font=self.fonts["small"],
        variant="secondary",
        command=lambda: (log_box.config(state="normal"), log_box.delete("1.0", "end"), log_box.config(state="disabled")),
        min_width=88,
    ).pack(side="left")

    def start_processing():
        folder = folder_var.get()
        if not folder:
            messagebox.showwarning("提示", "请先选择文件夹")
            return

        do_crop = opt_crop.get()
        do_limit = opt_limit.get()
        max_kb = max_kb_var.get()
        recurse = opt_subdir.get()
        mode = out_mode.get()

        start_btn.configure_button(state="disabled", text="处理中...")
        summary_var.set("")

        def worker():
            from PIL import Image as PILImage

            all_files = []
            if recurse:
                all_files = scan_files(folder)
            else:
                for file_name in os.listdir(folder):
                    file_path = os.path.join(folder, file_name)
                    if os.path.isfile(file_path) and file_name.lower().endswith((".pdf", ".jpg", ".jpeg", ".png")):
                        all_files.append(file_path)

            total = len(all_files)
            self.after(0, lambda: bar.configure(maximum=max(total, 1), value=0))

            if total == 0:
                self.after(0, lambda: prog_var.set("未找到 PDF 或图片文件"))
                self.after(0, lambda: start_btn.configure_button(state="normal", text="▶ 开始处理"))
                return

            ok = fail = 0
            for idx, file_path in enumerate(all_files):
                name = os.path.basename(file_path)
                self.after(0, lambda n=name, i=idx: prog_var.set(f"处理中 ({i+1}/{total}): {n}"))
                try:
                    if mode == "subfolder":
                        rel = os.path.relpath(file_path, folder)
                        rel_dir = os.path.dirname(rel)
                        out_dir = os.path.join(folder, "processed", rel_dir)
                        os.makedirs(out_dir, exist_ok=True)
                        out_path = os.path.join(out_dir, os.path.splitext(name)[0] + ".jpg")
                    else:
                        out_path = os.path.splitext(file_path)[0] + ".jpg"

                    if file_path.lower().endswith(".pdf"):
                        img_buf, _ = self._pdf_to_image_bytes(file_path, max_kb=max_kb if do_limit else 99999)
                        if img_buf is None:
                            fail += 1
                            self.after(0, lambda n=name: log(f"❌ PDF 转换失败: {n}"))
                            self.after(0, lambda v=idx + 1: bar.configure(value=v))
                            continue
                        img = PILImage.open(img_buf).convert("RGB")
                    else:
                        img = PILImage.open(file_path).convert("RGB")
                        if do_crop:
                            img = self._auto_crop_passport(img)

                    if opt_whitebg.get():
                        temp = io.BytesIO()
                        img.save(temp, format="JPEG", quality=92)
                        result = self._make_white_background(temp.getvalue())
                        img = PILImage.open(io.BytesIO(result)).convert("RGB")

                    if do_limit:
                        quality = 85
                        while quality >= 30:
                            buf = io.BytesIO()
                            img.save(buf, format="JPEG", quality=quality)
                            if buf.tell() / 1024 <= max_kb:
                                break
                            quality -= 10
                        else:
                            width, height = img.size
                            while width > 400:
                                width, height = int(width * 0.75), int(height * 0.75)
                                resized = img.resize((width, height), PILImage.LANCZOS)
                                buf = io.BytesIO()
                                resized.save(buf, format="JPEG", quality=60)
                                if buf.tell() / 1024 <= max_kb:
                                    break
                    else:
                        buf = io.BytesIO()
                        img.save(buf, format="JPEG", quality=90)

                    buf.seek(0)
                    with open(out_path, "wb") as handle:
                        handle.write(buf.read())

                    size_kb = os.path.getsize(out_path) / 1024
                    ok += 1
                    self.after(0, lambda n=name, s=size_kb: log(f"✅ {n} -> {s:.0f} KB"))
                except Exception as exc:
                    fail += 1
                    self.after(0, lambda n=name, err=str(exc): log(f"❌ {n} 错误: {err}"))

                self.after(0, lambda v=idx + 1: bar.configure(value=v))

            out_desc = os.path.join(folder, "processed") if mode == "subfolder" else "原位置（已覆盖）"
            self.after(0, lambda: prog_var.set("✅ 全部处理完成"))
            self.after(0, lambda: summary_var.set(f"✅ 成功 {ok}  ❌ 失败 {fail}  共 {total} 个 -> 输出: {out_desc}"))
            self.after(0, lambda: start_btn.configure_button(state="normal", text="▶ 开始处理"))

        threading.Thread(target=worker, daemon=True).start()

    start_btn.configure_button(command=start_processing)


def build_photo_whitebg_page(app):
    self = app
    self._clear_content()
    try:
        self._page_photo_whitebg_build()
    except Exception:
        import traceback

        tk.Label(
            self.content,
            text=f"页面加载错误:\n{traceback.format_exc()}",
            bg="#1e1e2e",
            fg="#f38ba8",
            font=("Courier", 9),
            justify="left",
            wraplength=700,
        ).pack(padx=16, pady=16, anchor="w")


def build_photo_whitebg_page_body(app):
    self = app
    import os
    import threading
    from tkinter import filedialog
    from tkinter.scrolledtext import ScrolledText

    inner = _build_scrollable_page(self.content, "#1e1e2e")

    tk.Label(inner, text="🎭 证件照换白底", font=self.fonts["title"], bg="#1e1e2e", fg="#cba6f7").pack(
        anchor="w", pady=(12, 2)
    )

    def rembg_state_info():
        state = get_rembg_state()
        messages = {
            "no_rembg": "❌ rembg 未安装，请先到设置页安装",
            "no_model": "⚠️ rembg 已安装，但模型尚未下载，请先到设置页下载",
            "ready": "✅ rembg 已就绪，可以正常使用",
        }
        return state, messages[state]

    state, state_msg = rembg_state_info()
    state_color = {"ready": "#a6e3a1", "no_model": "#f9e2af", "no_rembg": "#f38ba8"}[state]
    status_var = tk.StringVar(value=state_msg)
    tk.Label(inner, textvariable=status_var, bg="#1e1e2e", fg=state_color, font=self.fonts["small"]).pack(
        anchor="w", pady=(0, 4)
    )

    if state != "ready":
        RoundedButton(
            inner,
            text="⚙️ 前往设置安装 / 下载模型",
            font=self.fonts["button"],
            variant="purple",
            min_width=220,
            command=self._page_settings,
        ).pack(anchor="w", pady=(0, 8))

    mode_sec = _make_section(inner, "处理模式", self.fonts, "#cba6f7")
    mode_var = tk.StringVar(value="single")
    tk.Radiobutton(mode_sec, text="单张图片", variable=mode_var, value="single", bg="#313244", fg="#cdd6f4", selectcolor="#45475a", activebackground="#313244", font=self.fonts["small"]).pack(side="left", padx=(0, 20))
    tk.Radiobutton(mode_sec, text="批量处理文件夹", variable=mode_var, value="batch", bg="#313244", fg="#cdd6f4", selectcolor="#45475a", activebackground="#313244", font=self.fonts["small"]).pack(side="left")

    path_sec = _make_section(inner, "选择文件", self.fonts, "#cba6f7")
    path_var = tk.StringVar(value="（未选择）")
    path_row = tk.Frame(path_sec, bg="#313244")
    path_row.pack(fill="x")
    path_row.grid_columnconfigure(0, weight=1)
    tk.Label(path_row, textvariable=path_var, bg="#313244", fg="#cdd6f4", font=self.fonts["small"], anchor="w", justify="left", wraplength=720).grid(row=0, column=0, sticky="ew")
    selected = {"files": []}

    def choose():
        if mode_var.get() == "single":
            file_path = filedialog.askopenfilename(title="选择证件照", filetypes=[("图片", "*.jpg *.jpeg *.png")])
            if file_path:
                selected["files"] = [file_path]
                path_var.set(os.path.basename(file_path))
        else:
            folder = filedialog.askdirectory(title="选择证件照文件夹")
            if folder:
                files = [os.path.join(folder, x) for x in os.listdir(folder) if x.lower().endswith((".jpg", ".jpeg", ".png"))]
                selected["files"] = files
                path_var.set(f"{folder}（{len(files)} 张）")

    RoundedButton(
        path_row,
        text="选择",
        font=self.fonts["button"],
        variant="accent",
        min_width=88,
        command=choose,
    ).grid(row=0, column=1, sticky="e", padx=(12, 0))

    opt_sec = _make_section(inner, "输出选项", self.fonts, "#cba6f7")
    overwrite_var = tk.BooleanVar(value=False)
    tk.Checkbutton(
        opt_sec,
        text="直接覆盖原文件（不勾选则输出到 whitebg 子文件夹）",
        variable=overwrite_var,
        bg="#313244",
        fg="#cdd6f4",
        selectcolor="#45475a",
        activebackground="#313244",
        font=self.fonts["small"],
    ).pack(anchor="w")

    prog_sec = _make_section(inner, "进度", self.fonts, "#cba6f7")
    prog_var = tk.StringVar(value="")
    tk.Label(prog_sec, textvariable=prog_var, bg="#313244", fg="#cdd6f4", font=self.fonts["small"]).pack(anchor="w")
    bar = ttk.Progressbar(prog_sec, mode="determinate")
    bar.pack(fill="x", pady=(4, 0))

    log_box = ScrolledText(inner, height=10, bg="#181825", fg="#a6e3a1", font=self.fonts["mono"], wrap="word")
    log_box.pack(fill="x", pady=(4, 4))

    def log(msg):
        self.after(0, lambda m=msg: (log_box.insert("end", m + "\n"), log_box.see("end")))

    def start():
        files = selected["files"]
        if not files:
            prog_var.set("❌ 请先选择文件")
            return
        if get_rembg_state() != "ready":
            prog_var.set("❌ rembg 未就绪，请先安装并下载模型")
            return

        log_box.delete("1.0", "end")
        bar["maximum"] = len(files)
        bar["value"] = 0
        start_btn.configure_button(state="disabled", text="处理中...")

        def worker():
            ok = fail = 0
            for idx, file_path in enumerate(files):
                file_name = os.path.basename(file_path)
                self.after(0, lambda n=file_name, i=idx: prog_var.set(f"({i+1}/{len(files)}) {n}"))
                try:
                    with open(file_path, "rb") as handle:
                        result = self._make_white_background(handle.read())
                    if overwrite_var.get():
                        out_path = file_path
                    else:
                        out_dir = os.path.join(os.path.dirname(file_path), "whitebg")
                        os.makedirs(out_dir, exist_ok=True)
                        out_path = os.path.join(out_dir, os.path.splitext(file_name)[0] + "_white.jpg")
                    with open(out_path, "wb") as handle:
                        handle.write(result)
                    size_kb = os.path.getsize(out_path) / 1024
                    log(f"✅ {file_name} -> {size_kb:.0f}KB -> {os.path.basename(out_path)}")
                    ok += 1
                except Exception as exc:
                    log(f"❌ {file_name} 错误: {exc}")
                    fail += 1
                self.after(0, lambda v=idx + 1: bar.configure(value=v))

            self.after(0, lambda: prog_var.set(f"✅ 完成  成功 {ok}  失败 {fail}"))
            self.after(0, lambda: start_btn.configure_button(state="normal", text="▶ 开始处理"))

        threading.Thread(target=worker, daemon=True).start()

    start_btn = RoundedButton(
        inner,
        text="▶ 开始处理",
        font=self.fonts["button"],
        variant="primary" if state == "ready" else "secondary",
        min_width=120,
        command=start,
    )
    if state != "ready":
        start_btn.configure_button(state="disabled")
    start_btn.pack(anchor="w", padx=16, pady=(4, 16))
