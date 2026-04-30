#!/usr/bin/env python3
"""
Local image and OCR toolbox built with Tkinter.
"""

import tkinter as tk
import tkinter.font as tkfont

from .config import ensure_runtime_dependencies
from .config_store import load_api_key, load_koko_api_key, load_koko_paths, save_api_key, save_koko_api_key, save_koko_paths
from .image_service import auto_crop_passport, enhance_passport_image, looks_like_passport_image, make_white_background, pdf_to_image_bytes
from .ocr_service import ocr_passport
from .pages.image_pages import build_image_tools_page
from .pages.koko_pages import build_koko_create_visa_page, build_koko_preprocess_page, build_koko_query_page
from .pages.settings_page import build_settings_page
from .widgets import RoundedButton

ensure_runtime_dependencies()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("本地图片与 OCR 工具箱")
        self.geometry("1180x820")
        self.minsize(980, 700)
        self.resizable(True, True)
        self.configure(bg="#1e1e2e")
        self.is_macos = self.tk.call("tk", "windowingsystem") == "aqua"
        self.fonts = self._build_fonts()
        self._configure_ui_defaults()
        self.pipellm_api_key = self._load_api_key()
        self.koko_api_key = self._load_koko_api_key()
        self.koko_paths = self._load_koko_paths()
        self._build_main()

    def _build_fonts(self):
        family = "PingFang SC" if self.is_macos else "Arial"
        mono_family = "Menlo" if self.is_macos else "Courier"
        return {
            "title": (family, 15, "bold"),
            "heading": (family, 13, "bold"),
            "section": (family, 11, "bold"),
            "body": (family, 11),
            "small": (family, 10),
            "mono": (mono_family, 10),
            "button": (family, 11, "bold"),
        }

    def _configure_ui_defaults(self):
        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(family=self.fonts["body"][0], size=self.fonts["body"][1])
        text_font = tkfont.nametofont("TkTextFont")
        text_font.configure(family=self.fonts["body"][0], size=self.fonts["body"][1])
        fixed_font = tkfont.nametofont("TkFixedFont")
        fixed_font.configure(family=self.fonts["mono"][0], size=self.fonts["mono"][1])
        heading_font = tkfont.nametofont("TkHeadingFont")
        heading_font.configure(family=self.fonts["section"][0], size=self.fonts["section"][1], weight="bold")
        self.option_add("*Label.Font", self.fonts["body"])
        self.option_add("*Button.Font", self.fonts["body"])
        self.option_add("*Entry.Font", self.fonts["body"])
        self.option_add("*Checkbutton.Font", self.fonts["body"])
        self.option_add("*Radiobutton.Font", self.fonts["body"])
        self.option_add("*LabelFrame.Font", self.fonts["section"])

    def _build_main(self):
        self._clear()

        top = tk.Frame(self, bg="#181825", height=48)
        top.pack(fill="x")
        top.pack_propagate(False)
        tk.Label(
            top,
            text="本地图片与 OCR 工具箱",
            font=self.fonts["heading"],
            bg="#181825",
            fg="#cba6f7",
        ).pack(side="left", padx=16, pady=10)

        self.body = tk.Frame(self, bg="#1e1e2e")
        self.body.pack(fill="both", expand=True)

        sidebar = tk.Frame(self.body, bg="#181825", width=190)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        self._recreate_content()

        menu_groups = [
            ("本地工具", [("图片工具", self._page_image_tools), ("设置", self._page_settings)]),
            ("KOKO", [("预处理归档", self._page_koko_preprocess), ("创建签证申请", self._page_koko_create_visa), ("查询接口", self._page_koko_query)]),
        ]

        self._menu_btns = []
        for group_title, tool_menus in menu_groups:
            tk.Label(
                sidebar,
                text=group_title,
                bg="#181825",
                fg="#6c7086",
                font=self.fonts["small"],
            ).pack(pady=(16, 4), padx=12, anchor="w")

            for label, cmd in tool_menus:
                btn = RoundedButton(
                    sidebar,
                    font=self.fonts["body"],
                    text=label,
                    variant="sidebar",
                    width=150,
                    radius=12,
                    command=lambda c=cmd: self._menu_click(c),
                )
                btn.pack(pady=4, padx=12, anchor="w")
                self._menu_btns.append(btn)

        self._page_image_tools()

    def _menu_click(self, cmd):
        cmd()

    def _clear(self):
        for widget in self.winfo_children():
            widget.destroy()

    def _clear_content(self):
        if hasattr(self, "content") and self.content.winfo_exists():
            self.content.destroy()
        self._recreate_content()

    def _recreate_content(self):
        self.content = tk.Frame(self.body, bg="#1e1e2e")
        self.content.pack(side="left", fill="both", expand=True)

    def _load_api_key(self):
        return load_api_key()

    def _save_api_key(self, key):
        return save_api_key(key)

    def _load_koko_api_key(self):
        return load_koko_api_key()

    def _save_koko_api_key(self, key):
        return save_koko_api_key(key)

    def _load_koko_paths(self):
        return load_koko_paths()

    def _save_koko_paths(self, *, excel_path=None, folder_path=None):
        if excel_path is not None:
            self.koko_paths["excel_path"] = excel_path
        if folder_path is not None:
            self.koko_paths["folder_path"] = folder_path
        return save_koko_paths(excel_path=excel_path, folder_path=folder_path)

    def _enhance_passport_image(self, img_bytes):
        return enhance_passport_image(img_bytes)

    def _pipellm_ocr_passport(self, img_bytes):
        return ocr_passport(self.pipellm_api_key, img_bytes)

    def _make_white_background(self, img_bytes):
        return make_white_background(img_bytes)

    def _auto_crop_passport(self, img):
        return auto_crop_passport(img)

    def _looks_like_passport_image(self, img):
        return looks_like_passport_image(img)

    def _pdf_to_image_bytes(self, pdf_path, max_kb=900):
        return pdf_to_image_bytes(pdf_path, max_kb=max_kb)

    def _page_settings(self):
        build_settings_page(self)

    def _page_image_tools(self):
        build_image_tools_page(self)

    def _page_koko_create_visa(self):
        build_koko_create_visa_page(self)

    def _page_koko_preprocess(self):
        build_koko_preprocess_page(self)

    def _page_koko_query(self):
        build_koko_query_page(self)

def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
