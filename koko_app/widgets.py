import tkinter as tk
import tkinter.font as tkfont


class RoundedButton(tk.Canvas):
    def __init__(
        self,
        parent,
        text,
        command=None,
        *,
        font,
        variant="secondary",
        width=None,
        min_width=0,
        padding_x=18,
        padding_y=10,
        radius=14,
    ):
        self.command = command
        self.text = text
        self.font = tkfont.Font(font=font)
        self.padding_x = padding_x
        self.padding_y = padding_y
        self.radius = radius
        self.state = "normal"
        self.variant = variant
        self.palette = self._palette_for(variant)

        text_width = self.font.measure(text)
        text_height = self.font.metrics("linespace")
        self.button_width = max(width or 0, min_width, text_width + padding_x * 2)
        self.button_height = text_height + padding_y * 2

        super().__init__(
            parent,
            width=self.button_width,
            height=self.button_height,
            bg=parent.cget("bg"),
            bd=0,
            highlightthickness=0,
            relief="flat",
            cursor="hand2",
        )
        self._is_pressed = False
        self._redraw()
        self.bind("<Enter>", self._handle_enter)
        self.bind("<Leave>", self._handle_leave)
        self.bind("<ButtonPress-1>", self._handle_press)
        self.bind("<ButtonRelease-1>", self._handle_release)

    def _palette_for(self, variant):
        palettes = {
            "sidebar": {
                "fill": "#25273a",
                "hover": "#2f3348",
                "active": "#3a4058",
                "disabled": "#232530",
                "text": "#f2e9cf",
            },
            "primary": {
                "fill": "#a8d8b0",
                "hover": "#b7e4bf",
                "active": "#91c69a",
                "disabled": "#627367",
                "text": "#122016",
            },
            "secondary": {
                "fill": "#3a3f59",
                "hover": "#484e69",
                "active": "#535a78",
                "disabled": "#2d3142",
                "text": "#e8eaf6",
            },
            "accent": {
                "fill": "#7ba7d9",
                "hover": "#8bb5e5",
                "active": "#6898cf",
                "disabled": "#556a83",
                "text": "#122033",
            },
            "warning": {
                "fill": "#dcc58d",
                "hover": "#e8d39d",
                "active": "#cbb171",
                "disabled": "#7b735c",
                "text": "#2b2412",
            },
            "purple": {
                "fill": "#bda6d8",
                "hover": "#cbb7e3",
                "active": "#aa90c8",
                "disabled": "#6f647d",
                "text": "#231a2f",
            },
        }
        return palettes[variant]

    def _draw_rounded_rect(self, x1, y1, x2, y2, radius, fill):
        self.create_arc(x1, y1, x1 + radius * 2, y1 + radius * 2, start=90, extent=90, fill=fill, outline=fill)
        self.create_arc(x2 - radius * 2, y1, x2, y1 + radius * 2, start=0, extent=90, fill=fill, outline=fill)
        self.create_arc(x1, y2 - radius * 2, x1 + radius * 2, y2, start=180, extent=90, fill=fill, outline=fill)
        self.create_arc(x2 - radius * 2, y2 - radius * 2, x2, y2, start=270, extent=90, fill=fill, outline=fill)
        self.create_rectangle(x1 + radius, y1, x2 - radius, y2, fill=fill, outline=fill)
        self.create_rectangle(x1, y1 + radius, x2, y2 - radius, fill=fill, outline=fill)

    def _current_fill(self):
        if self.state == "disabled":
            return self.palette["disabled"]
        if self._is_pressed:
            return self.palette["active"]
        return self.palette["fill"]

    def _redraw(self):
        self.delete("all")
        fill = self._current_fill()
        self._draw_rounded_rect(1, 1, self.button_width - 1, self.button_height - 1, self.radius, fill)
        self.create_text(
            self.button_width / 2,
            self.button_height / 2,
            text=self.text,
            fill=self.palette["text"],
            font=self.font,
        )

    def configure_button(self, *, text=None, command=None, state=None):
        if text is not None:
            self.text = text
        if command is not None:
            self.command = command
        if state is not None:
            self.state = state
            self.configure(cursor="arrow" if state == "disabled" else "hand2")
        self._redraw()

    def _handle_enter(self, _event):
        if self.state != "normal" or self._is_pressed:
            return
        self.palette["fill"], self.palette["hover"] = self.palette["hover"], self.palette["fill"]
        self._redraw()
        self.palette["fill"], self.palette["hover"] = self.palette["hover"], self.palette["fill"]

    def _handle_leave(self, _event):
        if self.state != "normal":
            return
        self._is_pressed = False
        self._redraw()

    def _handle_press(self, _event):
        if self.state != "normal":
            return
        self._is_pressed = True
        self._redraw()

    def _handle_release(self, event):
        if self.state != "normal":
            return
        should_run = 0 <= event.x <= self.button_width and 0 <= event.y <= self.button_height
        self._is_pressed = False
        self._redraw()
        if should_run and self.command:
            self.command()
