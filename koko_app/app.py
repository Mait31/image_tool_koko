#!/usr/bin/env python3
"""
Local image and OCR toolbox built with Tkinter.
"""

import tkinter as tk

from .config import ensure_runtime_dependencies
from .config_store import load_api_key, save_api_key
from .image_service import auto_crop_passport, enhance_passport_image, make_white_background, pdf_to_image_bytes
from .ocr_service import ocr_passport
from .pages.image_pages import build_image_tools_page
from .pages.settings_page import build_settings_page

ensure_runtime_dependencies()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("本地图片与 OCR 工具箱")
        self.geometry("1100x720")
        self.resizable(True, True)
        self.configure(bg="#1e1e2e")
        self.pipellm_api_key = self._load_api_key()
        self._build_main()

    def _build_main(self):
        self._clear()

        top = tk.Frame(self, bg="#181825", height=48)
        top.pack(fill="x")
        top.pack_propagate(False)
        tk.Label(
            top,
            text="本地图片与 OCR 工具箱",
            font=("Arial", 14, "bold"),
            bg="#181825",
            fg="#cba6f7",
        ).pack(side="left", padx=16, pady=10)

        body = tk.Frame(self, bg="#1e1e2e")
        body.pack(fill="both", expand=True)

        sidebar = tk.Frame(body, bg="#181825", width=190)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        self.content = tk.Frame(body, bg="#1e1e2e")
        self.content.pack(side="left", fill="both", expand=True)

        tool_menus = [
            ("图片工具", self._page_image_tools),
            ("设置", self._page_settings),
        ]

        tk.Label(
            sidebar,
            text="本地工具",
            bg="#181825",
            fg="#6c7086",
            font=("Arial", 9),
        ).pack(pady=(16, 4), padx=12, anchor="w")

        self._menu_btns = []
        for label, cmd in tool_menus:
            btn = tk.Button(
                sidebar,
                text=label,
                anchor="w",
                padx=12,
                font=("Arial", 11),
                bg="#181825",
                fg="#f9e2af",
                relief="flat",
                cursor="hand2",
                activebackground="#313244",
                command=lambda c=cmd: self._menu_click(c),
            )
            btn.pack(fill="x", pady=1)
            self._menu_btns.append(btn)

        self._page_image_tools()

    def _menu_click(self, cmd):
        cmd()

    def _clear(self):
        for widget in self.winfo_children():
            widget.destroy()

    def _clear_content(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    def _load_api_key(self):
        return load_api_key()

    def _save_api_key(self, key):
        return save_api_key(key)

    def _enhance_passport_image(self, img_bytes):
        return enhance_passport_image(img_bytes)

    def _pipellm_ocr_passport(self, img_bytes):
        return ocr_passport(self.pipellm_api_key, img_bytes)

    def _make_white_background(self, img_bytes):
        return make_white_background(img_bytes)

    def _auto_crop_passport(self, img):
        return auto_crop_passport(img)

    def _pdf_to_image_bytes(self, pdf_path, max_kb=900):
        return pdf_to_image_bytes(pdf_path, max_kb=max_kb)

    def _page_settings(self):
        build_settings_page(self)

    def _page_image_tools(self):
        build_image_tools_page(self)

def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
