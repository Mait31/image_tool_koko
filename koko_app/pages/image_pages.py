import tkinter as tk
from tkinter import ttk

from ..image_service import get_rembg_state


def build_image_tools_page(app):
    self = app
    self._clear_content()
    import io
    import os
    import threading
    import tkinter.ttk as ttk2
    from tkinter import filedialog, messagebox, scrolledtext

    canvas = tk.Canvas(self.content, bg="#1e1e2e", highlightthickness=0)
    vsb = ttk2.Scrollbar(self.content, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    vsb.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    inner = tk.Frame(canvas, bg="#1e1e2e")
    win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

    inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width))
    canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
    canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
    canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

    tk.Label(inner, text="🛠 图片工具", font=("Arial", 15, "bold"), bg="#1e1e2e", fg="#f9e2af").pack(
        anchor="w", padx=16, pady=(12, 2)
    )
    tk.Label(
        inner,
        text="批量处理文件夹内的护照 PDF / 图片：自动裁剪、可选换白底、可选压缩大小。",
        bg="#1e1e2e",
        fg="#6c7086",
        font=("Arial", 10),
    ).pack(anchor="w", padx=16, pady=(0, 10))

    pad = dict(padx=16, pady=4)
    sec1 = tk.LabelFrame(inner, text=" 选择文件夹 ", bg="#313244", fg="#f9e2af", font=("Arial", 11, "bold"), padx=12, pady=8)
    sec1.pack(fill="x", **pad)

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
    tk.Label(row, textvariable=folder_label, bg="#313244", fg="#cdd6f4", font=("Arial", 10), width=52, anchor="w").pack(side="left")
    tk.Button(
        row,
        text="选择文件夹",
        bg="#89b4fa",
        fg="#1e1e2e",
        relief="flat",
        cursor="hand2",
        font=("Arial", 10, "bold"),
        command=choose_folder,
    ).pack(side="left", padx=(8, 0))
    tk.Label(sec1, textvariable=count_var, bg="#313244", fg="#a6e3a1", font=("Arial", 10)).pack(anchor="w", pady=(4, 0))

    sec2 = tk.LabelFrame(inner, text=" 处理选项 ", bg="#313244", fg="#f9e2af", font=("Arial", 11, "bold"), padx=12, pady=8)
    sec2.pack(fill="x", **pad)

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
        font=("Arial", 10),
    ).pack(anchor="w")
    tk.Checkbutton(
        sec2,
        text="自动换白底（适用于人像证件照）",
        variable=opt_whitebg,
        bg="#313244",
        fg="#cdd6f4",
        selectcolor="#45475a",
        activebackground="#313244",
        font=("Arial", 10),
    ).pack(anchor="w")
    tk.Checkbutton(
        sec2,
        text="压缩到指定大小以内",
        variable=opt_limit,
        bg="#313244",
        fg="#cdd6f4",
        selectcolor="#45475a",
        activebackground="#313244",
        font=("Arial", 10),
    ).pack(anchor="w")

    size_row = tk.Frame(sec2, bg="#313244")
    size_row.pack(anchor="w", padx=(22, 0))
    tk.Label(size_row, text="最大 KB:", bg="#313244", fg="#6c7086", font=("Arial", 10)).pack(side="left")
    tk.Entry(size_row, textvariable=max_kb_var, width=6, bg="#45475a", fg="#cdd6f4", relief="flat", font=("Arial", 10)).pack(
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
        font=("Arial", 10),
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
        font=("Arial", 10),
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
        font=("Arial", 10),
    ).pack(anchor="w")

    sec3 = tk.LabelFrame(inner, text=" 处理进度 ", bg="#313244", fg="#f9e2af", font=("Arial", 11, "bold"), padx=12, pady=8)
    sec3.pack(fill="x", **pad)
    prog_var = tk.StringVar(value="等待开始...")
    summary_var = tk.StringVar(value="")
    tk.Label(sec3, textvariable=prog_var, bg="#313244", fg="#cdd6f4", font=("Arial", 10)).pack(anchor="w")
    bar = ttk2.Progressbar(sec3, mode="determinate", length=600)
    bar.pack(fill="x", pady=4)
    tk.Label(sec3, textvariable=summary_var, bg="#313244", fg="#a6e3a1", font=("Arial", 10, "bold")).pack(anchor="w")

    log_box = scrolledtext.ScrolledText(sec3, height=8, bg="#181825", fg="#cdd6f4", font=("Courier", 9), wrap="word", state="disabled")
    log_box.pack(fill="x", pady=(4, 0))

    def log(msg):
        log_box.config(state="normal")
        log_box.insert("end", msg + "\n")
        log_box.see("end")
        log_box.config(state="disabled")

    btn_row = tk.Frame(inner, bg="#1e1e2e")
    btn_row.pack(anchor="w", padx=16, pady=8)

    start_btn = tk.Button(
        btn_row,
        text="▶ 开始处理",
        bg="#a6e3a1",
        fg="#1e1e2e",
        relief="flat",
        cursor="hand2",
        font=("Arial", 12, "bold"),
        padx=20,
        pady=8,
    )
    start_btn.pack(side="left", padx=(0, 12))
    tk.Button(
        btn_row,
        text="清空日志",
        bg="#45475a",
        fg="#cdd6f4",
        relief="flat",
        cursor="hand2",
        font=("Arial", 10),
        padx=10,
        pady=8,
        command=lambda: (log_box.config(state="normal"), log_box.delete("1.0", "end"), log_box.config(state="disabled")),
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

        start_btn.config(state="disabled", text="处理中...")
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
                self.after(0, lambda: start_btn.config(state="normal", text="▶ 开始处理"))
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
            self.after(0, lambda: start_btn.config(state="normal", text="▶ 开始处理"))

        threading.Thread(target=worker, daemon=True).start()

    start_btn.config(command=start_processing)


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

    canvas = tk.Canvas(self.content, bg="#1e1e2e", highlightthickness=0)
    vsb = ttk.Scrollbar(self.content, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    vsb.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    inner = tk.Frame(canvas, bg="#1e1e2e")
    win_id = canvas.create_window((0, 0), window=inner, anchor="nw")
    inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width))
    canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

    tk.Label(inner, text="🎭 证件照换白底", font=("Arial", 15, "bold"), bg="#1e1e2e", fg="#cba6f7").pack(
        anchor="w", padx=16, pady=(12, 2)
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
    tk.Label(inner, textvariable=status_var, bg="#1e1e2e", fg=state_color, font=("Arial", 10)).pack(
        anchor="w", padx=16, pady=(0, 4)
    )

    if state != "ready":
        tk.Button(
            inner,
            text="⚙️ 前往设置安装 / 下载模型",
            bg="#cba6f7",
            fg="#1e1e2e",
            relief="flat",
            cursor="hand2",
            font=("Arial", 11, "bold"),
            padx=14,
            pady=6,
            command=self._page_settings,
        ).pack(anchor="w", padx=16, pady=(0, 8))

    mode_sec = tk.LabelFrame(inner, text=" 处理模式 ", bg="#313244", fg="#cba6f7", font=("Arial", 11, "bold"), padx=12, pady=8)
    mode_sec.pack(fill="x", padx=16, pady=4)
    mode_var = tk.StringVar(value="single")
    tk.Radiobutton(mode_sec, text="单张图片", variable=mode_var, value="single", bg="#313244", fg="#cdd6f4", selectcolor="#45475a", activebackground="#313244", font=("Arial", 10)).pack(side="left", padx=(0, 20))
    tk.Radiobutton(mode_sec, text="批量处理文件夹", variable=mode_var, value="batch", bg="#313244", fg="#cdd6f4", selectcolor="#45475a", activebackground="#313244", font=("Arial", 10)).pack(side="left")

    path_sec = tk.LabelFrame(inner, text=" 选择文件 ", bg="#313244", fg="#cba6f7", font=("Arial", 11, "bold"), padx=12, pady=8)
    path_sec.pack(fill="x", padx=16, pady=4)
    path_var = tk.StringVar(value="（未选择）")
    tk.Label(path_sec, textvariable=path_var, bg="#313244", fg="#cdd6f4", font=("Arial", 10), anchor="w", width=55).pack(side="left")
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

    tk.Button(
        path_sec,
        text="选择",
        bg="#89b4fa",
        fg="#1e1e2e",
        relief="flat",
        cursor="hand2",
        font=("Arial", 10, "bold"),
        padx=12,
        command=choose,
    ).pack(side="left", padx=(8, 0))

    opt_sec = tk.LabelFrame(inner, text=" 输出选项 ", bg="#313244", fg="#cba6f7", font=("Arial", 11, "bold"), padx=12, pady=8)
    opt_sec.pack(fill="x", padx=16, pady=4)
    overwrite_var = tk.BooleanVar(value=False)
    tk.Checkbutton(
        opt_sec,
        text="直接覆盖原文件（不勾选则输出到 whitebg 子文件夹）",
        variable=overwrite_var,
        bg="#313244",
        fg="#cdd6f4",
        selectcolor="#45475a",
        activebackground="#313244",
        font=("Arial", 10),
    ).pack(anchor="w")

    prog_sec = tk.LabelFrame(inner, text=" 进度 ", bg="#313244", fg="#cba6f7", font=("Arial", 11, "bold"), padx=12, pady=8)
    prog_sec.pack(fill="x", padx=16, pady=4)
    prog_var = tk.StringVar(value="")
    tk.Label(prog_sec, textvariable=prog_var, bg="#313244", fg="#cdd6f4", font=("Arial", 10)).pack(anchor="w")
    bar = ttk.Progressbar(prog_sec, mode="determinate")
    bar.pack(fill="x", pady=(4, 0))

    log_box = ScrolledText(inner, height=10, bg="#181825", fg="#a6e3a1", font=("Courier", 9), wrap="word")
    log_box.pack(fill="x", padx=16, pady=(4, 4))

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
        start_btn.config(state="disabled", text="处理中...")

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
            self.after(0, lambda: start_btn.config(state="normal", text="▶ 开始处理"))

        threading.Thread(target=worker, daemon=True).start()

    start_btn = tk.Button(
        inner,
        text="▶ 开始处理",
        bg="#a6e3a1" if state == "ready" else "#45475a",
        fg="#1e1e2e",
        relief="flat",
        cursor="hand2",
        font=("Arial", 12, "bold"),
        padx=20,
        pady=8,
        command=start,
    )
    start_btn.pack(anchor="w", padx=16, pady=(4, 16))
