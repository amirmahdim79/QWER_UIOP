import keyboard
import threading
import time
import tkinter as tk
import queue

# 🔤 English letter frequency (sorted, lowercase)
FREQUENCY_ORDER = list("etaoinshrdlcumwfgypbvkjxqz")

# Interleaved blocks of 5 from frequency order:
# block1 -> QWERC, block2 -> MUIOP, block3 -> QWERC, block4 -> MUIOP, ...
_BLOCKS = [FREQUENCY_ORDER[i:i+5] for i in range(0, len(FREQUENCY_ORDER), 5)]
QWERC_PAGES = [_BLOCKS[i] for i in range(0, len(_BLOCKS), 2)]
MUIOP_PAGES = [_BLOCKS[i] for i in range(1, len(_BLOCKS), 2)]

QWERC_CHARS = [ch for page in QWERC_PAGES for ch in page]
MUIOP_CHARS = [ch for page in MUIOP_PAGES for ch in page]

# 🔢 Numbers (0-9)
NUMBER_PAGES = [["0", "1", "2", "3", "4"], ["5", "6", "7", "8", "9"], [".", ",", "+", "-", "*"]]

# 📍 Common symbols (sorted by usage frequency, most → least)
SYMBOL_PAGES = [
	["'", "\"", "-", "?", "!"],
	[":", ";", "(", ")", "/"],
	["@", "#", "$", "&", "%"],
	["*", "_", "=", "+", "["],
	["]", "{", "}", "\\", "<"],
	[">", "|", "^", "~", "`"],
]

QWERC_KEYS = ["q", "w", "e", "r", "c"]
MUIOP_KEYS = ["m", "u", "i", "o", "p"]
MODE_KEYS = ["t", "y"]

MANAGED_KEYS = set(QWERC_KEYS + MUIOP_KEYS + MODE_KEYS)

# Character set modes
MODES = ["letters", "numbers", "symbols"]
current_mode = "letters"

qwerc_gear = 0
muiop_gear = 0
active = True
is_emitting = False
quit_event = threading.Event()

# Mode tracking
mode_index = 0

# Timer-based chord detection state
CHORD_WINDOW = 0.04  # 40ms window — fast enough to feel instant, wide enough to catch chords
_lock = threading.Lock()
pending_key = None       # first key pressed, awaiting possible chord partner
pending_timer = None     # timer that fires single-key action if no chord partner arrives
held_keys = set()        # currently physically held managed keys
chord_mode = False       # are we in chord mode (2+ keys detected)?
chord_fired = False      # did we already fire for this chord?
peak_keys = set()        # largest simultaneous set of keys seen during chord

# Multi-tap gear cycling
MULTI_TAP_WINDOW = 0.3  # 300ms window to detect repeated taps on same key
last_fired_key = None       # which key was last fired as single
last_fired_time = 0.0       # time.time() of last fire
tap_gear_offset = 0         # how many gears ahead from current gear

# Space double-tap detection
SPACE_DOUBLE_TAP_WINDOW = 0.3  # 300ms window to detect double-tap
space_tap_timer = None
space_tap_count = 0

# Floating UI
_ui_queue = queue.Queue()
_floating_ui = None


class FloatingUI:
	BG = "#1e1e2e"
	FG = "#cdd6f4"
	ACTIVE_FG = "#89dceb"
	ACTIVE_ALT_FG = "#a6e3a1"
	THUMB_FG = "#cba6f7"
	DIM_FG = "#585b70"
	YELLOW_FG = "#f9e2af"
	MARKER_FG = "#89dceb"

	def __init__(self):
		self.root = tk.Tk()
		self.root.title("QWERC")
		self.root.overrideredirect(True)
		self.root.attributes("-topmost", True)
		self.root.attributes("-alpha", 0.92)
		self.root.configure(bg=self.BG)

		# Draggable
		self._drag_x = 0
		self._drag_y = 0

		self.text = tk.Text(
			self.root, bg=self.BG, fg=self.FG,
			font=("Consolas", 10), wrap="none",
			borderwidth=0, highlightthickness=1,
			highlightbackground="#585b70",
			cursor="arrow", padx=8, pady=6,
			width=44, height=1,  # height auto-adjusted
		)
		self.text.pack(fill="both", expand=True)
		self.text.config(state="disabled")

		# Bind drag on the text widget too
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

		# Position near bottom-right of screen
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
				_ui_queue.get_nowait()
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
		"""Insert boxed characters with appropriate colors."""
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

		state_str = "ACTIVE" if active else "PAUSED"
		state_icon = "\u25b6" if active else "\u23f8"
		self._insert(f" {state_icon} {state_str} [{current_mode.upper()}]\n", "header")

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

			left_active = (g == qwerc_gear)
			right_active = (g == muiop_gear)

			# Main line: marker + 4 fingers + separator + 4 fingers + marker
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

			# Thumb line
			lt_tag = "thumb" if left_active else "dim"
			rt_tag = "thumb" if right_active else "dim"
			self._insert(f"                  ")
			self._insert(f"[{left_chars[4]}]", lt_tag)
			self._insert(" \u2502 ")
			self._insert(f"[{right_chars[0]}]", rt_tag)
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


def refresh_ui():
	"""Signal the floating UI to refresh."""
	if _floating_ui is not None:
		_ui_queue.put(True)


def emit_char(char, shift_held):
	global is_emitting
	if char == "·":
		return
	out = char.upper() if shift_held else char
	is_emitting = True
	try:
		keyboard.write(out)
	finally:
		is_emitting = False


def send_key(name):
	global is_emitting
	is_emitting = True
	try:
		keyboard.send(name)
	finally:
		is_emitting = False


def reset_space_tap():
	global space_tap_count, space_tap_timer
	if space_tap_count == 1:
		# Single tap - emit one space
		emit_char(" ", False)
	space_tap_count = 0
	space_tap_timer = None


def handle_space():
	global space_tap_count, space_tap_timer
	
	if space_tap_timer is not None:
		space_tap_timer.cancel()
	
	space_tap_count += 1
	
	if space_tap_count == 2:
		# Double tap - send newline
		send_key("enter")
		space_tap_count = 0
		space_tap_timer = None
	else:
		# First tap - wait for potential second tap
		space_tap_timer = threading.Timer(SPACE_DOUBLE_TAP_WINDOW, reset_space_tap)
		space_tap_timer.start()


def get_current_pages():
	"""Return (left_pages, right_pages) based on current mode."""
	if current_mode == "letters":
		return QWERC_PAGES, MUIOP_PAGES
	elif current_mode == "numbers":
		return NUMBER_PAGES, NUMBER_PAGES
	else:  # symbols
		return SYMBOL_PAGES, SYMBOL_PAGES


def get_page(pages, gear):
	"""Get current page of 5 chars for the gear (clamped)."""
	g = max(0, min(gear, len(pages) - 1))
	page = pages[g]
	# Pad to 5 if last page is short
	return (page + ["·"] * 5)[:5]


def boxed(chars):
	"""Format chars in boxes: [e] [t] [a] [o] [i]"""
	return " ".join(f"[{c}]" for c in chars)


def print_header():
	print("🔤 English letter frequency: " + " ".join(FREQUENCY_ORDER))
	print("   Interleaved blocks of 5 (QWERC/MUIOP alternating)")
	print("   QWERC pages: " + " | ".join("".join(page) for page in QWERC_PAGES))
	print("   MUIOP pages: " + " | ".join("".join(page) for page in MUIOP_PAGES))


def print_status():
	state = "▶ ACTIVE" if active else "⏸ PAUSED"
	mode_display = f"[{current_mode.upper()}]"
	# ANSI styles (works in modern Windows terminals)
	RESET = "\033[0m"
	DIM = "\033[2m"
	ACTIVE_COLOR = "\033[1;96m"  # bright cyan
	ACTIVE_COLOR_ALT = "\033[1;92m"  # bright green
	HELP_COLOR = "\033[1;93m"    # bright yellow
	THUMB_COLOR = "\033[1;95m"   # bright magenta for finger 5 (thumb)

	def colored_boxed(chars, color1, color2, thumb_idx=None):
		"""Box chars with alternating colors, thumb in THUMB_COLOR."""
		result = []
		for i, c in enumerate(chars):
			if i == thumb_idx:
				color = THUMB_COLOR
			else:
				color = color1 if i % 2 == 0 else color2
			result.append(f"{color}[{c}]{RESET}")
		return " ".join(result)

	# Get the appropriate page sets based on mode
	left_pages, right_pages = get_current_pages()
	max_pages = max(len(left_pages), len(right_pages))

	active_numbers = f"    {HELP_COLOR}4   3   2   1{RESET}           {HELP_COLOR}1   2   3   4{RESET}"

	print(f"\n {state} {mode_display}")
	print(active_numbers)

	for g in range(max_pages):
		# Left side
		if g < len(left_pages):
			left_chars = get_page(left_pages, g)
		else:
			left_chars = ["·", "·", "·", "·", "·"]

		# Right side
		if g < len(right_pages):
			right_chars = get_page(right_pages, g)
		else:
			right_chars = ["·", "·", "·", "·", "·"]

		left_active = (g == qwerc_gear)
		right_active = (g == muiop_gear)

		# Main line: 4 fingers (indices 0-3 for left, 1-4 for right)
		left_main = left_chars[:4]
		right_main = right_chars[1:]

		# Thumb line: index 4 for left, index 0 for right
		left_thumb = left_chars[4]
		right_thumb = right_chars[0]

		# Left marker and main text
		if left_active:
			left_marker = "▶"
			left_text = colored_boxed(left_main, ACTIVE_COLOR, ACTIVE_COLOR_ALT)
		else:
			left_marker = "✕"
			left_text = boxed(left_main)

		# Right marker and main text
		if right_active:
			right_text = colored_boxed(right_main, ACTIVE_COLOR, ACTIVE_COLOR_ALT)
			right_marker = "◀"
		else:
			right_text = boxed(right_main)
			right_marker = "✕"

		# Thumb characters
		if left_active:
			lt = f"{THUMB_COLOR}[{left_thumb}]{RESET}"
		else:
			lt = f"[{left_thumb}]"
		if right_active:
			rt = f"{THUMB_COLOR}[{right_thumb}]{RESET}"
		else:
			rt = f"[{right_thumb}]"

		print(f" {left_marker} {left_text}    │    {right_text} {right_marker}")
		print(f"                  {lt} │ {rt}")

	refresh_ui()


def execute_combo(keys):
	"""Execute action for two-key combos."""
	global qwerc_gear, muiop_gear, current_mode, mode_index
	combo = frozenset(keys)
	left_pages, right_pages = get_current_pages()

	# Mode switching combo
	if combo == frozenset({"t", "y"}):
		mode_index = (mode_index + 1) % len(MODES)
		current_mode = MODES[mode_index]
		qwerc_gear = 0
		muiop_gear = 0
		print_status()
		return

	# Gear combos
	if combo == frozenset({"q", "w"}):
		qwerc_gear = max(qwerc_gear - 1, 0)
		print_status()
		return
	if combo == frozenset({"e", "r"}):
		qwerc_gear = min(qwerc_gear + 1, len(left_pages) - 1)
		print_status()
		return
	if combo == frozenset({"u", "i"}):
		muiop_gear = min(muiop_gear + 1, len(right_pages) - 1)
		print_status()
		return
	if combo == frozenset({"o", "p"}):
		muiop_gear = max(muiop_gear - 1, 0)
		print_status()
		return

	# Navigation / edit combos
	if combo == frozenset({"q", "m"}):
		send_key("left")
		return
	if combo == frozenset({"c", "p"}):
		send_key("right")
		return
	if combo == frozenset({"w", "o"}):
		send_key("backspace")
		return


def fire_single(key):
	"""Execute a single-key action with multi-tap gear cycling."""
	global qwerc_gear, muiop_gear, last_fired_key, last_fired_time, tap_gear_offset

	shift_held = keyboard.is_pressed("shift")
	now = time.time()

	# Handle mode keys
	if key == "t":
		qwerc_gear = 0
		last_fired_key = None
		print_status()
		return
	if key == "y":
		muiop_gear = 0
		last_fired_key = None
		print_status()
		return

	# Multi-tap detection: same key tapped again within window?
	if key == last_fired_key and (now - last_fired_time) < MULTI_TAP_WINDOW:
		tap_gear_offset += 1
		# Backspace the previously emitted character
		send_key("backspace")
	else:
		tap_gear_offset = 0

	last_fired_key = key
	last_fired_time = now

	# Get the correct pages based on mode
	left_pages, right_pages = get_current_pages()

	if key in QWERC_KEYS:
		idx = QWERC_KEYS.index(key)
		num_pages = len(left_pages)
		effective_gear = (qwerc_gear + tap_gear_offset) % num_pages
		char_page = get_page(left_pages, effective_gear)
		emit_char(char_page[idx], shift_held)
	elif key in MUIOP_KEYS:
		idx = MUIOP_KEYS.index(key)
		num_pages = len(right_pages)
		effective_gear = (muiop_gear + tap_gear_offset) % num_pages
		char_page = get_page(right_pages, effective_gear)
		emit_char(char_page[idx], shift_held)


def _fire_pending():
	"""Timer callback: no second key arrived within CHORD_WINDOW, fire as single key."""
	global pending_key, pending_timer
	with _lock:
		key = pending_key
		pending_key = None
		pending_timer = None
	if key and active:
		fire_single(key)


def on_key(event):
	global chord_mode, chord_fired, peak_keys, pending_key, pending_timer

	if is_emitting:
		return

	key = event.name

	# Handle space separately for double-tap
	if key == "space":
		if event.event_type == "down":
			if not active:
				return
			handle_space()
		return

	if key not in MANAGED_KEYS:
		return

	if event.event_type == "down":
		if key in held_keys:
			return  # key repeat — ignore

		held_keys.add(key)

		if not active:
			return

		with _lock:
			if chord_mode:
				# Already in chord mode — just accumulate
				if len(held_keys) > len(peak_keys):
					peak_keys = set(held_keys)
			elif pending_key is not None:
				# Second key arrived within chord window → enter chord mode
				if pending_timer is not None:
					pending_timer.cancel()
					pending_timer = None
				chord_mode = True
				chord_fired = False
				peak_keys = set(held_keys)
				pending_key = None
			else:
				# First key down — start short timer
				pending_key = key
				pending_timer = threading.Timer(CHORD_WINDOW, _fire_pending)
				pending_timer.start()

	else:  # up
		held_keys.discard(key)

		if not active:
			return

		with _lock:
			if chord_mode:
				# Fire combo when all chord keys are released
				if len(held_keys) == 0:
					if not chord_fired:
						chord_fired = True
						execute_combo(peak_keys)
					chord_mode = False
					chord_fired = False
					peak_keys = set()


def toggle_pause():
	global active
	active = not active
	print_status()


def quit_app():
	global _floating_ui
	print("\n👋 Quitting...")
	keyboard.unhook_all()
	if _floating_ui is not None:
		_floating_ui.close()
		_floating_ui = None
	quit_event.set()


def _run_floating_ui():
	"""Launch the floating UI in a background thread."""
	global _floating_ui
	try:
		_floating_ui = FloatingUI()
		_floating_ui.run()
	except Exception as e:
		print(f"[FloatingUI] Could not start: {e}")
		_floating_ui = None


def main():
	print_header()
	print("\nControls:")
	print("  Q W E R C     → type QWERC page letters (left hand)")
	print("  M U I O P     → type MUIOP page letters (right hand)")
	print("  Shift+key     → uppercase")
	print("  T             → reset left gear to 0")
	print("  Y             → reset right gear to 0")
	print("  Q+W hold      → left gear down")
	print("  E+R hold      → left gear up")
	print("  U+I hold      → right gear up")
	print("  O+P hold      → right gear down")
	print("  Q+M hold      → ← arrow")
	print("  C+P hold      → → arrow")
	print("  W+O hold      → backspace")
	print("  T+Y hold      → cycle modes (letters/numbers/symbols)")
	print("  Space         → space (double-tap → enter)")
	print("  Ctrl+Shift+A  → pause / resume")
	print("  Ctrl+Shift+Z  → quit")
	print("  All other keys work normally.")

	# Launch floating UI in background thread
	ui_thread = threading.Thread(target=_run_floating_ui, daemon=True)
	ui_thread.start()

	print_status()

	for key in MANAGED_KEYS:
		keyboard.hook_key(key, on_key, suppress=True)

	keyboard.hook_key("space", on_key, suppress=True)  # Hook space for double-tap detection

	keyboard.add_hotkey("ctrl+shift+a", toggle_pause)
	keyboard.add_hotkey("ctrl+shift+z", quit_app)

	quit_event.wait()


if __name__ == "__main__":
	main()
