# Floating tkinter UI overlay — shows current gear state and predictions

import tkinter as tk
import queue

import state
from config import MAX_PREDICTIONS
from input_handler import get_current_pages, get_page


class FloatingUI:
	BG = "#1e1e2e"
	FG = "#cdd6f4"
	ACTIVE_FG = "#89dceb"
	ACTIVE_ALT_FG = "#a6e3a1"
	THUMB_FG = "#cba6f7"
	DIM_FG = "#585b70"
	YELLOW_FG = "#f9e2af"
	MARKER_FG = "#89dceb"
	PRED_FG = "#f9e2af"
	PRED_HIGHLIGHT_FG = "#a6e3a1"

	def __init__(self):
		self.root = tk.Tk()
		self.root.title("QWERC")
		self.root.overrideredirect(True)
		self.root.attributes("-topmost", True)
		self.root.attributes("-alpha", 0.92)
		self.root.configure(bg=self.BG)

		self._drag_x = 0
		self._drag_y = 0

		self.text = tk.Text(
			self.root, bg=self.BG, fg=self.FG,
			font=("Consolas", 10), wrap="none",
			borderwidth=0, highlightthickness=1,
			highlightbackground="#585b70",
			cursor="arrow", padx=8, pady=6,
			width=44, height=1,
		)
		self.text.pack(fill="both", expand=True)
		self.text.config(state="disabled")

		self.text.bind("<Button-1>", self._start_drag)
		self.text.bind("<B1-Motion>", self._do_drag)
		self.root.bind("<Button-1>", self._start_drag)
		self.root.bind("<B1-Motion>", self._do_drag)

		# Tags
		self.text.tag_configure("active", foreground=self.ACTIVE_FG, font=("Consolas", 10, "bold"))
		self.text.tag_configure("active_alt", foreground=self.ACTIVE_ALT_FG, font=("Consolas", 10, "bold"))
		self.text.tag_configure("thumb", foreground=self.THUMB_FG, font=("Consolas", 10, "bold"))
		self.text.tag_configure("dim", foreground=self.DIM_FG)
		self.text.tag_configure("yellow", foreground=self.YELLOW_FG)
		self.text.tag_configure("header", foreground=self.FG, font=("Consolas", 10, "bold"))
		self.text.tag_configure("marker_on", foreground=self.MARKER_FG, font=("Consolas", 10, "bold"))
		self.text.tag_configure("marker_off", foreground=self.DIM_FG)
		self.text.tag_configure("pred", foreground=self.PRED_FG)
		self.text.tag_configure("pred_top", foreground=self.PRED_HIGHLIGHT_FG, font=("Consolas", 10, "bold"))
		self.text.tag_configure("pred_label", foreground=self.DIM_FG)

		# Position near bottom-right
		self.root.update_idletasks()
		scr_w = self.root.winfo_screenwidth()
		scr_h = self.root.winfo_screenheight()
		self.root.geometry(f"+{scr_w - 500}+{scr_h - 350}")

		self.refresh()
		self._poll()

	def _start_drag(self, event):
		self._drag_x = event.x_root - self.root.winfo_x()
		self._drag_y = event.y_root - self.root.winfo_y()

	def _do_drag(self, event):
		self.root.geometry(f"+{event.x_root - self._drag_x}+{event.y_root - self._drag_y}")

	def _poll(self):
		try:
			while True:
				state.ui_queue.get_nowait()
				self.refresh()
		except queue.Empty:
			pass
		self.root.after(50, self._poll)

	def _insert(self, text, tag=None):
		if tag:
			self.text.insert("end", text, tag)
		else:
			self.text.insert("end", text)

	def _boxed_chars(self, chars, active, is_left):
		for i, ch in enumerate(chars):
			if i > 0:
				self._insert(" ")
			if active:
				tag = "active" if i % 2 == 0 else "active_alt"
			else:
				tag = "dim"
			self._insert(f"[{ch}]", tag)

	def refresh(self):
		self.text.config(state="normal")
		self.text.delete("1.0", "end")

		state_str = "ACTIVE" if state.active else "PAUSED"
		state_icon = "\u25b6" if state.active else "\u23f8"
		self._insert(f" {state_icon} {state_str} [{state.current_mode.upper()}]\n", "header")

		left_pages, right_pages = get_current_pages()
		max_pg = max(len(left_pages), len(right_pages))

		# Number header
		self._insert("    ")
		self._insert("4   3   2   1", "yellow")
		self._insert("           ")
		self._insert("1   2   3   4", "yellow")
		self._insert("\n")

		for g in range(max_pg):
			left_chars = get_page(left_pages, g) if g < len(left_pages) else ["\u00b7"] * 5
			right_chars = get_page(right_pages, g) if g < len(right_pages) else ["\u00b7"] * 5

			left_active = (g == state.qwerc_gear)
			right_active = (g == state.muiop_gear)

			if left_active:
				self._insert(" \u25b6 ", "marker_on")
			else:
				self._insert(" \u2715 ", "marker_off")

			self._boxed_chars(left_chars[:4], left_active, True)
			self._insert("    \u2502    ")
			self._boxed_chars(right_chars[1:], right_active, False)

			if right_active:
				self._insert(" \u25c0", "marker_on")
			else:
				self._insert(" \u2715", "marker_off")
			self._insert("\n")

			lt_tag = "thumb" if left_active else "dim"
			rt_tag = "thumb" if right_active else "dim"
			self._insert("                  ")
			self._insert(f"[{left_chars[4]}]", lt_tag)
			self._insert(" \u2502 ")
			self._insert(f"[{right_chars[0]}]", rt_tag)
			self._insert("\n")

		# Prediction bar
		if state.prediction_active and state.predictions:
			self._insert("\n")
			self._insert(" \U0001f4a1 ", "pred_label")
			self._insert(f'"{state.current_word}" \u2192  ', "dim")
			for i, word in enumerate(state.predictions[:MAX_PREDICTIONS]):
				tag = "pred_top" if i == 0 else "pred"
				label = "Q+P" if i == 0 else f" {i+1} "
				self._insert(f"[{label}]", "pred_label")
				self._insert(f" {word}  ", tag)
			self._insert("\n")

		# Auto-size height
		line_count = int(self.text.index("end-1c").split(".")[0])
		self.text.config(height=line_count)

		self.text.config(state="disabled")

	def run(self):
		self.root.mainloop()

	def close(self):
		try:
			self.root.quit()
		except Exception:
			pass
