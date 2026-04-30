import json
import io
import os
import threading
import tkinter as tk
from difflib import SequenceMatcher
from tkinter import filedialog, scrolledtext, ttk

from ..koko_service import (
    KokoVisaClient,
    build_passport_filename,
    build_portrait_filename,
    choose_passport_and_photo,
    find_person_folder,
    parse_excel_rows,
    parse_visa_type_text,
    sanitize_person_name,
)
from ..widgets import RoundedButton
from .image_pages import _build_scrollable_page, _make_section


def _iter_person_folders(root_dir):
    for entry in sorted(os.listdir(root_dir)):
        path = os.path.join(root_dir, entry)
        if os.path.isdir(path):
            yield path


def _rename_path(src_path, dst_path):
    if os.path.abspath(src_path) == os.path.abspath(dst_path):
        return dst_path
    if os.path.exists(dst_path):
        if os.path.isdir(dst_path):
            raise RuntimeError(f"目标文件夹已存在：{os.path.basename(dst_path)}")
        os.remove(dst_path)
    os.replace(src_path, dst_path)
    return dst_path


def _find_portrait_candidate(folder_path, passport_image_path, looks_like_passport_image):
    from PIL import Image

    portrait_hints = ("证件", "photo", "人像", "头像", "微信", "qq")
    candidates = []
    for entry in sorted(os.listdir(folder_path)):
        path = os.path.join(folder_path, entry)
        if not os.path.isfile(path):
            continue
        lower = entry.lower()
        if not lower.endswith((".jpg", ".jpeg", ".png")):
            continue
        if passport_image_path and os.path.abspath(path) == os.path.abspath(passport_image_path):
            continue
        candidates.append(path)

    for path in candidates:
        lower = os.path.basename(path).lower()
        if "_证件照" in lower or any(hint in lower for hint in portrait_hints):
            return path

    non_passport_candidates = []
    for path in candidates:
        try:
            with Image.open(path) as img:
                if not looks_like_passport_image(img.convert("RGB")):
                    non_passport_candidates.append(path)
        except Exception:
            non_passport_candidates.append(path)

    if non_passport_candidates:
        return non_passport_candidates[0]
    return candidates[0] if candidates else None


def _build_excel_name_map(excel_path):
    rows = parse_excel_rows(excel_path)
    name_map = {}
    for row in rows:
        raw_name = str(row.get("person_name") or "").strip()
        norm_name = sanitize_person_name(raw_name)
        if norm_name and norm_name not in name_map:
            name_map[norm_name] = raw_name
    return name_map


def _find_best_excel_name_match(candidate_name, excel_name_map):
    candidate = sanitize_person_name(candidate_name)
    if not candidate:
        return "", 0.0

    if candidate in excel_name_map:
        return excel_name_map[candidate], 1.0

    scored = []
    for norm_name, raw_name in excel_name_map.items():
        if not norm_name:
            continue
        same_surname = candidate[:1] == norm_name[:1]
        same_length = len(candidate) == len(norm_name)
        same_positions = sum(1 for a, b in zip(candidate, norm_name) if a == b)
        diff_count = abs(len(candidate) - len(norm_name)) + sum(1 for a, b in zip(candidate, norm_name) if a != b)
        ratio = SequenceMatcher(None, candidate, norm_name).ratio()
        bonus = 0.08 if same_surname else 0.0
        bonus += 0.04 if same_length else 0.0
        if same_surname and same_length and diff_count <= 1:
            bonus += 0.22
        elif same_surname and same_positions >= max(1, len(candidate) - 1):
            bonus += 0.12
        score = ratio + bonus
        scored.append((score, raw_name, norm_name))

    if not scored:
        return "", 0.0

    scored.sort(key=lambda item: item[0], reverse=True)
    best_score, best_raw_name, _ = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else 0.0

    if best_score >= 0.88 and (best_score - second_score) >= 0.05:
        return best_raw_name, best_score
    return "", best_score


def _preprocess_person_folder(app, folder_path, excel_name_map):
    from PIL import Image

    folder_name = os.path.basename(folder_path)
    matched_excel_name = excel_name_map.get(sanitize_person_name(folder_name), "")

    pdf_files = []
    image_files = []
    for entry in sorted(os.listdir(folder_path)):
        path = os.path.join(folder_path, entry)
        if not os.path.isfile(path):
            continue
        lower = entry.lower()
        if lower.endswith(".pdf"):
            pdf_files.append(path)
        elif lower.endswith((".jpg", ".jpeg", ".png")):
            image_files.append(path)

    passport_source = pdf_files[0] if pdf_files else None
    generated_passport_path = None
    ocr_bytes = None

    if passport_source:
        out_buf, _ = app._pdf_to_image_bytes(passport_source, max_kb=900)
        if out_buf is None:
            raise RuntimeError("PDF 转图片失败")
        ocr_bytes = out_buf.getvalue()
        generated_passport_path = os.path.join(folder_path, "__passport_from_pdf.jpg")
        with open(generated_passport_path, "wb") as handle:
            handle.write(ocr_bytes)
        passport_image_path = generated_passport_path
    else:
        passport_image_path, _ = choose_passport_and_photo(folder_path, app._looks_like_passport_image)
        if not passport_image_path:
            raise RuntimeError("未找到护照图片")

        with Image.open(passport_image_path) as img:
            cropped = app._auto_crop_passport(img.convert("RGB"))
            out = io.BytesIO()
            cropped.save(out, format="JPEG", quality=92)
            ocr_bytes = out.getvalue()

        generated_passport_path = os.path.join(folder_path, "__passport_processed.jpg")
        with open(generated_passport_path, "wb") as handle:
            handle.write(ocr_bytes)
        passport_image_path = generated_passport_path

    ocr_result = {}
    if matched_excel_name:
        person_name = sanitize_person_name(matched_excel_name)
        name_source = "Excel"
    else:
        ocr_result = app._pipellm_ocr_passport(ocr_bytes)
        ocr_name = sanitize_person_name((ocr_result or {}).get("name", ""))
        if not ocr_name:
            detail = (ocr_result or {}).get("error", "")
            if detail:
                raise RuntimeError(f"姓名提取失败：{detail}")
            raise RuntimeError("姓名提取失败，且文件夹名无法匹配 Excel")
        matched_from_ocr, match_score = _find_best_excel_name_match(ocr_name, excel_name_map)
        if matched_from_ocr:
            person_name = sanitize_person_name(matched_from_ocr)
            matched_excel_name = matched_from_ocr
            name_source = f"Excel近似匹配(OCR={ocr_name})"
        else:
            raise RuntimeError(f"OCR 姓名“{ocr_name}”无法可靠匹配 Excel，请人工检查")

    portrait_source = _find_portrait_candidate(folder_path, generated_passport_path, app._looks_like_passport_image)
    if not portrait_source:
        raise RuntimeError("未找到证件照图片")

    target_passport_path = os.path.join(folder_path, build_passport_filename(person_name))
    target_portrait_path = os.path.join(folder_path, build_portrait_filename(person_name, portrait_source))

    _rename_path(generated_passport_path, target_passport_path)
    _rename_path(portrait_source, target_portrait_path)

    for path in image_files:
        if os.path.abspath(path) in {os.path.abspath(target_passport_path), os.path.abspath(target_portrait_path)}:
            continue
        if os.path.exists(path) and os.path.basename(path).startswith("__passport_"):
            continue
        if path != portrait_source and path != passport_source and os.path.abspath(path) != os.path.abspath(target_passport_path):
            try:
                if "护照" in os.path.basename(path) or "passport" in os.path.basename(path).lower():
                    os.remove(path)
            except Exception:
                pass

    for pdf_path in pdf_files:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)

    renamed_folder_path = folder_path
    target_folder_name = person_name
    if os.path.basename(folder_path) != target_folder_name:
        parent_dir = os.path.dirname(folder_path)
        target_folder_path = os.path.join(parent_dir, target_folder_name)
        renamed_folder_path = _rename_path(folder_path, target_folder_path)

    return {
        "person_name": person_name,
        "matched_excel_name": matched_excel_name,
        "name_source": name_source,
        "folder_path": renamed_folder_path,
        "passport_path": os.path.join(renamed_folder_path, os.path.basename(target_passport_path)),
        "portrait_path": os.path.join(renamed_folder_path, os.path.basename(target_portrait_path)),
        "ocr_result": ocr_result,
    }


def build_koko_preprocess_page(app):
    self = app
    self._clear_content()

    inner = _build_scrollable_page(self.content, "#1e1e2e")

    tk.Label(inner, text="🗂️ 预处理归档", font=self.fonts["title"], bg="#1e1e2e", fg="#89b4fa").pack(anchor="w", pady=(12, 2))
    tk.Label(
        inner,
        text="先按 Excel 姓名标准化每个子文件夹：已命名文件夹直接按 Excel 姓名落盘，匹配不上的临时文件夹再走 OCR 辅助命名。",
        bg="#1e1e2e",
        fg="#6c7086",
        font=self.fonts["small"],
        justify="left",
        wraplength=920,
    ).pack(anchor="w", pady=(0, 10))

    sec1 = _make_section(inner, "基础信息", self.fonts, "#89b4fa")
    excel_var = tk.StringVar(value=self.koko_paths.get("excel_path", ""))
    folder_var = tk.StringVar(value=self.koko_paths.get("folder_path", ""))

    def choose_excel():
        path = filedialog.askopenfilename(title="选择 Excel 模板", filetypes=[("Excel", "*.xlsx")])
        if path:
            excel_var.set(path)
            self._save_koko_paths(excel_path=path)

    def choose_folder():
        path = filedialog.askdirectory(title="选择人员总文件夹")
        if path:
            folder_var.set(path)
            self._save_koko_paths(folder_path=path)

    def build_picker_row(parent, label, var, command):
        row = tk.Frame(parent, bg="#313244")
        row.pack(fill="x", pady=4)
        row.grid_columnconfigure(1, weight=1)
        tk.Label(row, text=label, bg="#313244", fg="#cdd6f4", font=self.fonts["body"]).grid(row=0, column=0, sticky="w")
        tk.Label(row, textvariable=var, bg="#313244", fg="#cdd6f4", font=self.fonts["small"], anchor="w", justify="left", wraplength=620).grid(row=0, column=1, sticky="ew", padx=(12, 12))
        RoundedButton(row, text="选择", font=self.fonts["button"], variant="accent", min_width=88, command=command).grid(row=0, column=2, sticky="e")

    build_picker_row(sec1, "Excel 模板", excel_var, choose_excel)
    build_picker_row(sec1, "人员总文件夹", folder_var, choose_folder)

    sec2 = _make_section(inner, "规则", self.fonts)
    for line in [
        "• 需要同时选择 Excel 和人员总文件夹。",
        "• 子文件夹名能匹配 Excel 姓名时，直接按 Excel 姓名重命名，不走 OCR。",
        "• 只有像 1 / 2 / 3 这种临时文件夹，才会走 OCR 辅助提取姓名。",
        "• 预处理后会生成：姓名_护照.jpg、姓名_证件照.xxx。",
        "• 成功提取到姓名后，子文件夹会改名成中文姓名。",
        "• 如果原始材料是 PDF，转换成功后会删除 PDF。",
        "• 如果 OCR 仍然提不出姓名，会提示具体子文件夹。",
    ]:
        tk.Label(sec2, text=line, bg="#313244", fg="#6c7086", font=self.fonts["small"], justify="left", wraplength=900).pack(anchor="w", pady=2)

    sec3 = _make_section(inner, "处理日志", self.fonts)
    status_var = tk.StringVar(value="等待开始...")
    summary_var = tk.StringVar(value="")
    tk.Label(sec3, textvariable=status_var, bg="#313244", fg="#cdd6f4", font=self.fonts["small"]).pack(anchor="w")
    tk.Label(sec3, textvariable=summary_var, bg="#313244", fg="#a6e3a1", font=self.fonts["section"], justify="left", wraplength=900).pack(anchor="w", pady=(4, 6))
    log_box = scrolledtext.ScrolledText(sec3, height=16, bg="#181825", fg="#cdd6f4", font=self.fonts["mono"], wrap="word", state="disabled")
    log_box.pack(fill="x")

    def log(message):
        log_box.config(state="normal")
        log_box.insert("end", message + "\n")
        log_box.see("end")
        log_box.config(state="disabled")

    btn_row = tk.Frame(inner, bg="#1e1e2e")
    btn_row.pack(anchor="w", pady=10)
    start_btn = RoundedButton(btn_row, text="▶ 开始预处理", font=self.fonts["button"], variant="primary", min_width=148)
    start_btn.pack(side="left", padx=(0, 12))

    def start():
        excel_path = excel_var.get().strip()
        root_dir = folder_var.get().strip()
        if not excel_path:
            status_var.set("❌ 请先选择 Excel 模板")
            return
        if not root_dir:
            status_var.set("❌ 请先选择人员总文件夹")
            return

        folders = list(_iter_person_folders(root_dir))
        if not folders:
            status_var.set("❌ 所选目录下没有子文件夹")
            return

        try:
            excel_name_map = _build_excel_name_map(excel_path)
        except Exception as exc:
            status_var.set(f"❌ Excel 读取失败：{exc}")
            return

        if not excel_name_map:
            status_var.set("❌ Excel 中没有可用姓名")
            return

        self._save_koko_paths(excel_path=excel_path, folder_path=root_dir)

        needs_ocr = any(not excel_name_map.get(sanitize_person_name(os.path.basename(path)), "") for path in folders)
        if needs_ocr and not (self.pipellm_api_key or "").strip():
            status_var.set("❌ 存在未命名文件夹，需要先在设置里填写 PipeLLM API Key")
            return

        start_btn.configure_button(state="disabled", text="处理中...")
        status_var.set("开始预处理...")
        summary_var.set("")

        def worker():
            ok = 0
            fail = 0
            failed = []
            total = len(folders)
            for idx, folder_path in enumerate(folders, start=1):
                folder_name = os.path.basename(folder_path)
                self.after(0, lambda i=idx, n=folder_name: status_var.set(f"处理中 ({i}/{total})：{n}"))
                try:
                    result = _preprocess_person_folder(self, folder_path, excel_name_map)
                    ok += 1
                    self.after(
                        0,
                        lambda r=result, old=folder_name: log(
                            f"✅ {old} -> {r['person_name']} | 来源: {r['name_source']} | 护照: {os.path.basename(r['passport_path'])} | 证件照: {os.path.basename(r['portrait_path'])}"
                        ),
                    )
                except Exception as exc:
                    fail += 1
                    failed.append(folder_name)
                    self.after(0, lambda n=folder_name, err=str(exc): log(f"❌ {n} 处理失败：{err}"))

            self.after(0, lambda: status_var.set("✅ 预处理完成"))
            self.after(0, lambda: summary_var.set(f"成功 {ok} 个，失败 {fail} 个。失败文件夹：{'、'.join(failed) if failed else '无'}"))
            self.after(0, lambda: start_btn.configure_button(state="normal", text="▶ 开始预处理"))

        threading.Thread(target=worker, daemon=True).start()

    start_btn.configure_button(command=start)


def build_koko_create_visa_page(app):
    self = app
    self._clear_content()

    inner = _build_scrollable_page(self.content, "#1e1e2e")

    tk.Label(inner, text="🧾 创建签证申请", font=self.fonts["title"], bg="#1e1e2e", fg="#89b4fa").pack(anchor="w", pady=(12, 2))
    tk.Label(
        inner,
        text="在完成“预处理归档”后，根据 Excel 模板和标准化图片文件夹批量创建 KOKO 签证申请。",
        bg="#1e1e2e",
        fg="#6c7086",
        font=self.fonts["small"],
        justify="left",
        wraplength=920,
    ).pack(anchor="w", pady=(0, 10))

    sec1 = _make_section(inner, "基础信息", self.fonts, "#89b4fa")
    excel_var = tk.StringVar(value=self.koko_paths.get("excel_path", ""))
    folder_var = tk.StringVar(value=self.koko_paths.get("folder_path", ""))
    visa_category_var = tk.StringVar(value="tourism")

    def build_picker_row(parent, label, var, command):
        row = tk.Frame(parent, bg="#313244")
        row.pack(fill="x", pady=4)
        row.grid_columnconfigure(1, weight=1)
        tk.Label(row, text=label, bg="#313244", fg="#cdd6f4", font=self.fonts["body"]).grid(row=0, column=0, sticky="w")
        tk.Label(row, textvariable=var, bg="#313244", fg="#cdd6f4", font=self.fonts["small"], anchor="w", justify="left", wraplength=620).grid(row=0, column=1, sticky="ew", padx=(12, 12))
        RoundedButton(row, text="选择", font=self.fonts["button"], variant="accent", min_width=88, command=command).grid(row=0, column=2, sticky="e")

    def choose_excel():
        path = filedialog.askopenfilename(title="选择 Excel 模板", filetypes=[("Excel", "*.xlsx")])
        if path:
            excel_var.set(path)
            self._save_koko_paths(excel_path=path)

    def choose_folder():
        path = filedialog.askdirectory(title="选择人员总文件夹")
        if path:
            folder_var.set(path)
            self._save_koko_paths(folder_path=path)

    build_picker_row(sec1, "Excel 模板", excel_var, choose_excel)
    build_picker_row(sec1, "人员总文件夹", folder_var, choose_folder)

    visa_row = tk.Frame(sec1, bg="#313244")
    visa_row.pack(anchor="w", pady=(10, 4))
    tk.Label(visa_row, text="签证类别", bg="#313244", fg="#cdd6f4", font=self.fonts["body"]).pack(side="left")
    tk.Radiobutton(visa_row, text="旅游签", variable=visa_category_var, value="tourism", bg="#313244", fg="#cdd6f4", selectcolor="#45475a", activebackground="#313244", font=self.fonts["small"]).pack(side="left", padx=(12, 8))
    tk.Radiobutton(visa_row, text="商务签", variable=visa_category_var, value="business", bg="#313244", fg="#cdd6f4", selectcolor="#45475a", activebackground="#313244", font=self.fonts["small"]).pack(side="left")

    sec_tags = _make_section(inner, "标签选择", self.fonts)
    tag_status_var = tk.StringVar(value="等待加载标签...")
    tk.Label(sec_tags, textvariable=tag_status_var, bg="#313244", fg="#cdd6f4", font=self.fonts["small"]).pack(anchor="w", pady=(0, 6))
    tag_box = tk.Frame(sec_tags, bg="#313244")
    tag_box.pack(fill="x")
    tag_vars = []
    tag_columns = 6
    for col in range(tag_columns):
        tag_box.grid_columnconfigure(col, weight=1)

    def render_tags(items):
        nonlocal tag_vars
        tag_vars = []
        for widget in tag_box.winfo_children():
            widget.destroy()
        if not items:
            tk.Label(tag_box, text="暂无可选标签", bg="#313244", fg="#6c7086", font=self.fonts["small"]).pack(anchor="w")
            return
        for idx, item in enumerate(items):
            row = idx // tag_columns
            col = idx % tag_columns
            var = tk.BooleanVar(value=False)
            tag_vars.append({"var": var, "id": item.get("id", ""), "name": item.get("name", "")})
            cb = tk.Checkbutton(
                tag_box,
                text=item.get("name", ""),
                variable=var,
                bg="#313244",
                fg="#cdd6f4",
                selectcolor="#45475a",
                activebackground="#313244",
                font=self.fonts["small"],
                anchor="w",
                justify="left",
            )
            cb.grid(row=row, column=col, sticky="ew", padx=(0, 12), pady=2)

    def load_tags():
        api_key = (self.koko_api_key or "").strip()
        if not api_key:
            tag_status_var.set("❌ 请先在设置里填写 KOKO API Key")
            render_tags([])
            return
        tag_status_var.set("加载标签中...")

        def worker():
            try:
                client = KokoVisaClient(api_key)
                payload = client.list_tags()
                items = payload.get("data") or []
                self.after(0, lambda: tag_status_var.set(f"✅ 已加载 {len(items)} 个标签"))
                self.after(0, lambda i=items: render_tags(i))
            except Exception as exc:
                self.after(0, lambda err=str(exc): tag_status_var.set(f"❌ 标签加载失败：{err}"))
                self.after(0, lambda: render_tags([]))

        threading.Thread(target=worker, daemon=True).start()

    tag_btn_row = tk.Frame(sec_tags, bg="#313244")
    tag_btn_row.pack(anchor="w", pady=(8, 0))
    RoundedButton(tag_btn_row, text="刷新标签", font=self.fonts["small"], variant="secondary", min_width=96, command=load_tags).pack(side="left")
    load_tags()

    sec2 = _make_section(inner, "说明", self.fonts)
    for line in [
        "• 公司按 Excel 里的公司名搜索，不回写 Excel。",
        "• 建议先完成“预处理归档”，再进行创建。",
        "• 每个人一个子文件夹，程序会优先使用标准命名：姓名_护照.jpg、姓名_证件照.xxx。",
        "• 创建签证申请只支持图片上传：护照图 + 人像图。",
        "• 勾选的标签会在申请创建成功后自动补打到该申请上。",
        "• 当前版本支持普通 / 加急 / 超级加急；超级加急会按 urgent + is_super_urgent=true 提交。",
    ]:
        tk.Label(sec2, text=line, bg="#313244", fg="#6c7086", font=self.fonts["small"], justify="left", wraplength=900).pack(anchor="w", pady=2)

    sec3 = _make_section(inner, "查询内容输出 / 创建日志", self.fonts)
    status_var = tk.StringVar(value="等待开始...")
    summary_var = tk.StringVar(value="")
    tk.Label(sec3, textvariable=status_var, bg="#313244", fg="#cdd6f4", font=self.fonts["small"]).pack(anchor="w")
    tk.Label(sec3, textvariable=summary_var, bg="#313244", fg="#a6e3a1", font=self.fonts["section"], justify="left", wraplength=900).pack(anchor="w", pady=(4, 6))
    log_box = scrolledtext.ScrolledText(sec3, height=12, bg="#181825", fg="#cdd6f4", font=self.fonts["mono"], wrap="word", state="disabled")
    log_box.pack(fill="x")

    sec4 = _make_section(inner, "接口原始输出", self.fonts)
    raw_box = scrolledtext.ScrolledText(sec4, height=12, bg="#11111b", fg="#f5f5f5", font=self.fonts["mono"], wrap="word", state="disabled")
    raw_box.pack(fill="x")

    def log(message):
        log_box.config(state="normal")
        log_box.insert("end", message + "\n")
        log_box.see("end")
        log_box.config(state="disabled")

    def set_raw_output(payload):
        raw_box.config(state="normal")
        raw_box.delete("1.0", "end")
        if isinstance(payload, (dict, list)):
            raw_box.insert("end", json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            raw_box.insert("end", str(payload))
        raw_box.see("end")
        raw_box.config(state="disabled")

    btn_row = tk.Frame(inner, bg="#1e1e2e")
    btn_row.pack(anchor="w", pady=10)
    start_btn = RoundedButton(btn_row, text="▶ 开始创建", font=self.fonts["button"], variant="primary", min_width=132)
    start_btn.pack(side="left", padx=(0, 12))
    RoundedButton(
        btn_row,
        text="清空日志",
        font=self.fonts["small"],
        variant="secondary",
        min_width=88,
        command=lambda: (log_box.config(state="normal"), log_box.delete("1.0", "end"), log_box.config(state="disabled")),
    ).pack(side="left")

    def start():
        excel_path = excel_var.get().strip()
        root_dir = folder_var.get().strip()
        api_key = (self.koko_api_key or "").strip()
        visa_category = visa_category_var.get()
        selected_tags = [item for item in tag_vars if item["var"].get() and item["id"]]

        if not excel_path:
            status_var.set("❌ 请先选择 Excel 模板")
            return
        if not root_dir:
            status_var.set("❌ 请先选择人员总文件夹")
            return
        if not api_key:
            status_var.set("❌ 请先在设置里填写 KOKO API Key")
            return

        self._save_koko_paths(excel_path=excel_path, folder_path=root_dir)

        start_btn.configure_button(state="disabled", text="处理中...")
        status_var.set("开始处理...")
        summary_var.set("")

        def worker():
            ok = 0
            fail = 0
            failed_names = []
            try:
                rows = parse_excel_rows(excel_path)
            except Exception as exc:
                self.after(0, lambda: status_var.set(f"❌ Excel 读取失败：{exc}"))
                self.after(0, lambda: start_btn.configure_button(state="normal", text="▶ 开始创建"))
                return

            if not rows:
                self.after(0, lambda: status_var.set("❌ Excel 中没有可处理的数据"))
                self.after(0, lambda: start_btn.configure_button(state="normal", text="▶ 开始创建"))
                return

            client = KokoVisaClient(api_key)
            total = len(rows)
            for idx, row in enumerate(rows, start=1):
                name = row["person_name"]
                self.after(0, lambda i=idx, n=name: status_var.set(f"处理中 ({i}/{total})：{n}"))
                try:
                    parsed_type = parse_visa_type_text(row["visa_type_text"])
                    person_folder = find_person_folder(root_dir, name)
                    if not person_folder:
                        raise RuntimeError("未找到对应的人员子文件夹")

                    passport_path, photo_path = choose_passport_and_photo(person_folder, self._looks_like_passport_image)
                    if not passport_path:
                        raise RuntimeError("未找到护照图片")
                    if not photo_path:
                        raise RuntimeError("未找到证件照图片")

                    company, _ = client.search_company(row["company_name"])
                    if not company:
                        raise RuntimeError(f"未搜索到公司：{row['company_name']}")

                    result, submit_payload = client.submit_visa(
                        passport_path=passport_path,
                        photo_path=photo_path,
                        visa_category=visa_category,
                        company_id=company["id"],
                        entry_type=parsed_type["entry_type"],
                        months=parsed_type["months"],
                        service_level=parsed_type["service_level"],
                        is_super_urgent=parsed_type["is_super_urgent"],
                    )

                    app_info = result.get("application") or {}
                    app_id = app_info.get("id", "")
                    app_status = app_info.get("status", "")
                    company_name = company.get("name", row["company_name"])
                    photo_note = os.path.basename(photo_path) if photo_path else "未带证件照"
                    urgency_note = "超级加急" if parsed_type["is_super_urgent"] else ("加急" if parsed_type["service_level"] == "urgent" else "普通")
                    applied_tag_names = []
                    if app_id and selected_tags:
                        for tag in selected_tags:
                            client.add_tag_to_visa(app_id, tag["id"])
                            applied_tag_names.append(tag["name"])
                    ok += 1
                    self.after(0, lambda p=submit_payload: set_raw_output(p))
                    self.after(
                        0,
                        lambda n=name, c=company_name, aid=app_id, st=app_status, pn=photo_note, un=urgency_note, tags="、".join(applied_tag_names) or "无": log(
                            f"✅ {n} 创建成功 | 公司: {c} | 服务等级: {un} | 状态: {st or '未知'} | 申请ID: {aid or '未返回'} | 标签: {tags} | 证件照: {pn}"
                        ),
                    )
                except Exception as exc:
                    fail += 1
                    failed_names.append(name)
                    self.after(0, lambda n=name, err=str(exc): log(f"❌ {n} 创建失败：{err}"))
                    self.after(0, lambda n=name, err=str(exc): set_raw_output({"person_name": n, "error": err}))

            failed_text = "、".join(failed_names) if failed_names else "无"
            self.after(0, lambda: status_var.set("✅ 全部处理完成"))
            self.after(0, lambda: summary_var.set(f"成功 {ok}  个，失败 {fail} 个。失败项：{failed_text}"))
            self.after(0, lambda: start_btn.configure_button(state="normal", text="▶ 开始创建"))

        threading.Thread(target=worker, daemon=True).start()

    start_btn.configure_button(command=start)


def build_koko_query_page(app):
    self = app
    self._clear_content()

    inner = _build_scrollable_page(self.content, "#1e1e2e")

    tk.Label(inner, text="🔎 查询接口", font=self.fonts["title"], bg="#1e1e2e", fg="#89b4fa").pack(anchor="w", pady=(12, 2))
    tk.Label(
        inner,
        text="用于直接查看 KOKO 后端接口返回。适合联调公司、护照、签证查询，以及确认后端实际枚举值。",
        bg="#1e1e2e",
        fg="#6c7086",
        font=self.fonts["small"],
        justify="left",
        wraplength=920,
    ).pack(anchor="w", pady=(0, 10))

    sec1 = _make_section(inner, "查询参数", self.fonts, "#89b4fa")
    query_type_var = tk.StringVar(value="company")
    query_text_var = tk.StringVar(value="")
    query_text_label_var = tk.StringVar(value="查询文本")
    status_var = tk.StringVar(value="等待查询...")

    query_type_row = tk.Frame(sec1, bg="#313244")
    query_type_row.pack(anchor="w", pady=(0, 8))
    tk.Label(query_type_row, text="查询类型", bg="#313244", fg="#cdd6f4", font=self.fonts["body"]).pack(side="left")
    tk.Radiobutton(query_type_row, text="公司搜索", variable=query_type_var, value="company", command=lambda: on_query_type_change(), bg="#313244", fg="#cdd6f4", selectcolor="#45475a", activebackground="#313244", font=self.fonts["small"]).pack(side="left", padx=(12, 6))
    tk.Radiobutton(query_type_row, text="护照搜索", variable=query_type_var, value="passport_search", command=lambda: on_query_type_change(), bg="#313244", fg="#cdd6f4", selectcolor="#45475a", activebackground="#313244", font=self.fonts["small"]).pack(side="left", padx=6)
    tk.Radiobutton(query_type_row, text="护照详情", variable=query_type_var, value="passport_detail", command=lambda: on_query_type_change(), bg="#313244", fg="#cdd6f4", selectcolor="#45475a", activebackground="#313244", font=self.fonts["small"]).pack(side="left", padx=6)
    tk.Radiobutton(query_type_row, text="签证搜索", variable=query_type_var, value="visa_search", command=lambda: on_query_type_change(), bg="#313244", fg="#cdd6f4", selectcolor="#45475a", activebackground="#313244", font=self.fonts["small"]).pack(side="left", padx=6)
    tk.Radiobutton(query_type_row, text="签证详情", variable=query_type_var, value="visa_detail", command=lambda: on_query_type_change(), bg="#313244", fg="#cdd6f4", selectcolor="#45475a", activebackground="#313244", font=self.fonts["small"]).pack(side="left", padx=6)

    fields_container = tk.Frame(sec1, bg="#313244")
    fields_container.pack(fill="x")

    query_input_row = tk.Frame(fields_container, bg="#313244")
    query_input_row.grid_columnconfigure(1, weight=1)
    tk.Label(query_input_row, textvariable=query_text_label_var, bg="#313244", fg="#cdd6f4", font=self.fonts["body"]).grid(row=0, column=0, sticky="w")
    query_text_entry = tk.Entry(query_input_row, textvariable=query_text_var, bg="#45475a", fg="#cdd6f4", insertbackground="white", relief="flat", font=self.fonts["body"])
    query_text_entry.grid(row=0, column=1, sticky="ew", padx=(12, 0))

    status_label = tk.Label(sec1, textvariable=status_var, bg="#313244", fg="#cdd6f4", font=self.fonts["small"])
    status_label.pack(anchor="w", pady=(6, 0))

    btn_row = tk.Frame(sec1, bg="#313244")
    btn_row.pack(anchor="w", pady=(8, 0))
    query_btn = RoundedButton(btn_row, text="查询接口", font=self.fonts["button"], variant="accent", min_width=112)
    query_btn.pack(side="left")

    def refresh_query_fields(*_args):
        query_type = query_type_var.get()

        show_text = query_type in {"company", "passport_search", "passport_detail", "visa_search", "visa_detail"}

        if query_type == "company":
            query_text_label_var.set("公司名（可空）")
        elif query_type == "passport_search":
            query_text_label_var.set("姓名 / 护照号")
        elif query_type == "passport_detail":
            query_text_label_var.set("passport_id")
        elif query_type == "visa_search":
            query_text_label_var.set("护照号")
        elif query_type == "visa_detail":
            query_text_label_var.set("application_id")
        else:
            query_text_label_var.set("查询文本")

        query_input_row.pack_forget()

        if show_text:
            query_input_row.pack(fill="x", pady=4)

        fields_container.update_idletasks()
        self.update_idletasks()

    def on_query_type_change():
        refresh_query_fields()

    refresh_query_fields()

    sec2 = _make_section(inner, "查询内容输出（双击单元格复制）", self.fonts)
    summary_label_var = tk.StringVar(value="等待查询结果...")
    tk.Label(sec2, textvariable=summary_label_var, bg="#313244", fg="#cdd6f4", font=self.fonts["small"]).pack(anchor="w", pady=(0, 6))

    tree_frame = tk.Frame(sec2, bg="#181825")
    tree_frame.pack(fill="x")

    tree_scroll_y = tk.Scrollbar(tree_frame, orient="vertical", bg="#313244", troughcolor="#181825", activebackground="#45475a", highlightthickness=0)
    tree_scroll_x = tk.Scrollbar(tree_frame, orient="horizontal", bg="#313244", troughcolor="#181825", activebackground="#45475a", highlightthickness=0)
    content_tree = ttk.Treeview(tree_frame, show="headings", yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set, height=12)
    tree_scroll_y.config(command=content_tree.yview)
    tree_scroll_x.config(command=content_tree.xview)
    tree_scroll_y.pack(side="right", fill="y")
    tree_scroll_x.pack(side="bottom", fill="x")
    content_tree.pack(fill="x")

    tree_style = ttk.Style()
    tree_style.configure("Koko.Treeview", rowheight=28, background="#181825", fieldbackground="#181825", foreground="#cdd6f4", borderwidth=0)
    tree_style.configure("Koko.Treeview.Heading", background="#2a2d3e", foreground="#7fb2ff", borderwidth=0, relief="flat")
    tree_style.map("Koko.Treeview.Heading", background=[("active", "#34384d")], foreground=[("active", "#cdd6f4")])
    tree_style.map("Koko.Treeview", background=[("selected", "#45475a")], foreground=[("selected", "#f5f5f5")])
    content_tree.configure(style="Koko.Treeview")
    content_tree.bind("<Double-1>", lambda event: copy_tree_cell(event))
    content_tree.bind("<Button-3>", lambda event: show_tree_menu(event))
    content_tree.bind("<Control-Button-1>", lambda event: show_tree_menu(event))

    tree_menu = tk.Menu(content_tree, tearoff=0, bg="#313244", fg="#cdd6f4", activebackground="#45475a", activeforeground="#f5f5f5")

    sec3 = _make_section(inner, "接口原始输出", self.fonts)
    raw_box = scrolledtext.ScrolledText(sec3, height=16, bg="#11111b", fg="#f5f5f5", font=self.fonts["mono"], wrap="word", state="disabled")
    raw_box.pack(fill="x")

    def write_box(widget, text):
        widget.config(state="normal")
        widget.delete("1.0", "end")
        widget.insert("end", text)
        widget.see("end")
        widget.config(state="disabled")

    def set_raw_output(payload):
        if isinstance(payload, (dict, list)):
            write_box(raw_box, json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            write_box(raw_box, str(payload))

    def set_table_output(summary_text, columns, rows):
        summary_label_var.set(summary_text)
        content_tree.delete(*content_tree.get_children())
        content_tree["columns"] = columns

        for col in columns:
            content_tree.heading(col, text=col)
            width = 160
            if col in {"值", "result_link", "name", "公司名"}:
                width = 280
            elif col in {"id", "application_id", "passport_id"}:
                width = 240
            content_tree.column(col, width=width, minwidth=100, anchor="center", stretch=True)

        for row in rows:
            values = [row.get(col, "") for col in columns]
            content_tree.insert("", "end", values=values)

    def set_detail_output(summary_text, data):
        rows = [{"字段": key, "值": data.get(key, "")} for key in data.keys()]
        set_table_output(summary_text, ["字段", "值"], rows)

    def get_tree_cell_value(event=None):
        row_id = content_tree.identify_row(event.y) if event else content_tree.focus()
        col_id = content_tree.identify_column(event.x) if event else ""
        if not row_id:
            return "", "", ""

        if event:
            content_tree.selection_set(row_id)
            content_tree.focus(row_id)

        values = content_tree.item(row_id, "values")
        if not values:
            return row_id, "", ""

        if not col_id:
            return row_id, "", "\t".join(str(v) for v in values)

        col_index = int(col_id.replace("#", "")) - 1
        if col_index < 0 or col_index >= len(values):
            return row_id, "", ""

        return row_id, col_id, str(values[col_index])

    def copy_text_to_clipboard(text):
        if not text:
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update_idletasks()

    def copy_tree_cell(event=None):
        _, _, value = get_tree_cell_value(event)
        if value:
            copy_text_to_clipboard(value)

    def copy_tree_row():
        _, _, value = get_tree_cell_value()
        if value:
            copy_text_to_clipboard(value)

    def show_tree_menu(event):
        row_id, _, cell_value = get_tree_cell_value(event)
        if not row_id:
            return

        row_values = content_tree.item(row_id, "values")
        row_text = "\t".join(str(v) for v in row_values)

        tree_menu.delete(0, "end")
        tree_menu.add_command(
            label="复制单元格",
            command=lambda text=cell_value: copy_text_to_clipboard(text),
        )
        tree_menu.add_command(
            label="复制整行",
            command=lambda text=row_text: copy_text_to_clipboard(text),
        )
        tree_menu.tk_popup(event.x_root, event.y_root)

    def run_query():
        api_key = (self.koko_api_key or "").strip()
        if not api_key:
            status_var.set("❌ 请先在设置里填写 KOKO API Key")
            return

        query_btn.configure_button(state="disabled", text="查询中...")
        status_var.set("查询接口中...")

        def worker():
            client = KokoVisaClient(api_key)
            query_type = query_type_var.get()
            query_text = query_text_var.get().strip()
            try:
                if query_type == "company":
                    payload = client.search_company_payload(query_text)
                    items = payload.get("data") or []
                    if query_text:
                        summary_text = f"公司搜索“{query_text}”返回 {len(items)} 条"
                    else:
                        summary_text = f"公司列表返回 {len(items)} 条"
                    rows = [{"公司名": item.get("name", ""), "id": item.get("id", ""), "inn": item.get("inn", "")} for item in items]
                elif query_type == "passport_search":
                    if not query_text:
                        raise RuntimeError("护照搜索需要填写姓名或护照号")
                    payload = client.search_passports(query_text)
                    items = payload.get("data") or []
                    summary_text = f"护照搜索“{query_text}”返回 {len(items)} 条"
                    rows = [
                        {
                            "中文名": item.get("name_zh", ""),
                            "护照号": item.get("passport_number", ""),
                            "英文名": f"{item.get('last_name', '')} {item.get('first_name', '')}".strip(),
                            "国籍": item.get("nationality", ""),
                            "id": item.get("id", ""),
                        }
                        for item in items
                    ]
                elif query_type == "passport_detail":
                    if not query_text:
                        raise RuntimeError("护照详情需要填写 passport_id")
                    payload = client.get_passport_detail(query_text)
                    data = payload.get("data") or {}
                    summary_text = "护照详情查询成功"
                elif query_type == "visa_search":
                    if not query_text:
                        raise RuntimeError("签证搜索需要填写护照号")
                    payload = client.find_visas_by_passport_number(query_text)
                    items = payload.get("data") or []
                    summary_text = f"护照号“{query_text}”匹配到 {len(items)} 条签证申请"
                    rows = [
                        {
                            "护照号": item.get("passport_number", ""),
                            "签证类别": item.get("visa_category", ""),
                            "状态": item.get("status", ""),
                            "服务等级": item.get("service_level", ""),
                            "超级加急": item.get("is_super_urgent", ""),
                            "application_id": item.get("id", ""),
                        }
                        for item in items
                    ]
                elif query_type == "visa_detail":
                    if not query_text:
                        raise RuntimeError("签证详情需要填写 application_id")
                    payload = client.get_visa_detail(query_text)
                    data = payload.get("data") or {}
                    summary_text = "签证详情查询成功"

                self.after(0, lambda p=payload: set_raw_output(p))
                if query_type == "company":
                    self.after(0, lambda s=summary_text, r=rows: set_table_output(s, ["公司名", "id", "inn"], r))
                elif query_type == "passport_search":
                    self.after(0, lambda s=summary_text, r=rows: set_table_output(s, ["中文名", "护照号", "英文名", "国籍", "id"], r))
                elif query_type == "passport_detail":
                    self.after(0, lambda s=summary_text, d=data: set_detail_output(s, d))
                elif query_type == "visa_search":
                    self.after(0, lambda s=summary_text, r=rows: set_table_output(s, ["护照号", "签证类别", "状态", "服务等级", "超级加急", "application_id"], r))
                elif query_type == "visa_detail":
                    self.after(0, lambda s=summary_text, d=data: set_detail_output(s, d))
                self.after(0, lambda: status_var.set("✅ 查询完成"))
            except Exception as exc:
                self.after(0, lambda err=str(exc): set_table_output(f"查询失败：{err}", ["状态"], [{"状态": err}]))
                self.after(0, lambda err=str(exc): set_raw_output({"error": err}))
                self.after(0, lambda: status_var.set("❌ 查询失败"))
            finally:
                self.after(0, lambda: query_btn.configure_button(state="normal", text="查询接口"))

        threading.Thread(target=worker, daemon=True).start()

    query_btn.configure_button(command=run_query)
