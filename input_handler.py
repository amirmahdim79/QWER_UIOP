# Character emission, combos, space handling, and prediction integration

import keyboard
import threading
import time

import state
from config import (
	QWERC_KEYS, MUIOP_KEYS, MODES, QWERC_PAGES, MUIOP_PAGES,
	NUMBER_PAGES, SYMBOL_PAGES, MULTI_TAP_WINDOW, SPACE_DOUBLE_TAP_WINDOW,
	PREDICTION_ACCEPT_COMBO, PREDICTION_PICK_COMBOS, AUTOCORRECT_TOGGLE_COMBO,
	THREE_KEY_COMBOS,
)
from predictor import predictor
from autocorrect import autocorrector


def refresh_ui():
	"""Signal the floating UI to refresh."""
	if state.floating_ui is not None:
		state.ui_queue.put(True)


def get_current_pages():
	"""Return (left_pages, right_pages) based on current mode."""
	if state.current_mode == "letters":
		return QWERC_PAGES, MUIOP_PAGES
	elif state.current_mode == "numbers":
		return NUMBER_PAGES, NUMBER_PAGES
	else:
		return SYMBOL_PAGES, SYMBOL_PAGES


def get_page(pages, gear):
	"""Get current page of 5 chars for the gear (clamped)."""
	g = max(0, min(gear, len(pages) - 1))
	page = pages[g]
	return (page + ["\u00b7"] * 5)[:5]


def emit_char(char, shift_held):
	"""Emit a single character and update prediction state."""
	if char == "\u00b7":
		return
	out = char.upper() if shift_held else char
	state.is_emitting = True
	try:
		keyboard.write(out)
	finally:
		state.is_emitting = False

	# Update word prediction
	if state.current_mode == "letters" and out.isalpha():
		state.current_word += out.lower()
		state.predictions = predictor.predict(state.current_word)
		state.prediction_active = len(state.predictions) > 0
	else:
		_finish_word()

	refresh_ui()


def send_key(name):
	state.is_emitting = True
	try:
		keyboard.send(name)
	finally:
		state.is_emitting = False


def _finish_word():
	"""End the current word — auto-correct if enabled, then learn it."""
	word = state.current_word

	# Auto-correct before learning
	if word and state.autocorrect_enabled and state.current_mode == "letters" and len(word) >= 2:
		corrected, was_corrected = autocorrector.correct(word, predictor._words)
		if was_corrected:
			# Replace the typed word with the corrected one
			state.is_emitting = True
			try:
				for _ in range(len(word)):
					keyboard.send("backspace")
				keyboard.write(corrected)
			finally:
				state.is_emitting = False
			word = corrected

	if len(word) >= 3:
		predictor.add_word(word)
	state.current_word = ""
	state.predictions = []
	state.prediction_active = False
	refresh_ui()


def accept_prediction(index=0):
	"""Accept prediction at given index: delete typed prefix, emit full word + space."""
	if not state.predictions or index >= len(state.predictions):
		return
	word = state.predictions[index]
	prefix_len = len(state.current_word)

	# Guard the entire operation so the hook ignores all synthetic events
	state.is_emitting = True
	try:
		for _ in range(prefix_len):
			keyboard.send("backspace")
		keyboard.write(word + " ")
	finally:
		state.is_emitting = False

	predictor.boost_word(word)
	state.current_word = ""
	state.predictions = []
	state.prediction_active = False

	# Reset multi-tap state so next keystroke starts clean
	state.last_fired_key = None
	state.last_fired_time = 0.0
	state.tap_gear_offset = 0

	refresh_ui()


def reset_space_tap():
	if state.space_tap_count == 1:
		emit_char(" ", False)
		_finish_word()
	state.space_tap_count = 0
	state.space_tap_timer = None


def handle_space():
	if state.space_tap_timer is not None:
		state.space_tap_timer.cancel()

	state.space_tap_count += 1

	if state.space_tap_count == 2:
		send_key("enter")
		_finish_word()
		state.space_tap_count = 0
		state.space_tap_timer = None
	else:
		state.space_tap_timer = threading.Timer(SPACE_DOUBLE_TAP_WINDOW, reset_space_tap)
		state.space_tap_timer.start()


def _execute_three_key(action):
	"""Handle 3-key chord actions."""
	_finish_word()
	state.is_emitting = True
	try:
		if action == "delete_word_left":
			keyboard.send("ctrl+backspace")
		elif action == "delete_word_right":
			keyboard.send("ctrl+delete")
		elif action == "delete_line":
			keyboard.send("home")
			keyboard.send("shift+end")
			keyboard.send("backspace")
		elif action == "select_word":
			keyboard.send("ctrl+shift+left")
		elif action == "select_line":
			keyboard.send("home")
			keyboard.send("shift+end")
		elif action == "word_left":
			keyboard.send("ctrl+left")
		elif action == "word_right":
			keyboard.send("ctrl+right")
		elif action == "copy":
			keyboard.send("ctrl+c")
		elif action == "paste":
			keyboard.send("ctrl+v")
		elif action == "cut":
			keyboard.send("ctrl+x")
		elif action == "undo":
			keyboard.send("ctrl+z")
		elif action == "redo":
			keyboard.send("ctrl+y")
		elif action == "tab":
			keyboard.send("tab")
		elif action == "home":
			keyboard.send("home")
		elif action == "end":
			keyboard.send("end")
	finally:
		state.is_emitting = False


def execute_combo(keys):
	"""Execute action for key combos (2-key and 3-key)."""
	combo = frozenset(keys)
	left_pages, right_pages = get_current_pages()

	# 3-key chords
	if combo in THREE_KEY_COMBOS:
		_execute_three_key(THREE_KEY_COMBOS[combo])
		return

	# Accept prediction by slot: C+M/U/I/O for #1-#4, Q+P for #1
	if state.prediction_active:
		if combo == PREDICTION_ACCEPT_COMBO:
			accept_prediction(0)
			return
		if combo in PREDICTION_PICK_COMBOS:
			accept_prediction(PREDICTION_PICK_COMBOS[combo])
			return

	# Autocorrect toggle
	if combo == AUTOCORRECT_TOGGLE_COMBO:
		state.autocorrect_enabled = not state.autocorrect_enabled
		print_status()
		return

	# Mode switching combo
	if combo == frozenset({"t", "y"}):
		state.mode_index = (state.mode_index + 1) % len(MODES)
		state.current_mode = MODES[state.mode_index]
		state.qwerc_gear = 0
		state.muiop_gear = 0
		_finish_word()
		print_status()
		return

	# Gear combos
	if combo == frozenset({"q", "w"}):
		state.qwerc_gear = max(state.qwerc_gear - 1, 0)
		print_status()
		return
	if combo == frozenset({"e", "r"}):
		state.qwerc_gear = min(state.qwerc_gear + 1, len(left_pages) - 1)
		print_status()
		return
	if combo == frozenset({"u", "i"}):
		state.muiop_gear = min(state.muiop_gear + 1, len(right_pages) - 1)
		print_status()
		return
	if combo == frozenset({"o", "p"}):
		state.muiop_gear = max(state.muiop_gear - 1, 0)
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
		# Remove last char from current_word if any
		if state.current_word:
			state.current_word = state.current_word[:-1]
			if state.current_word:
				state.predictions = predictor.predict(state.current_word)
				state.prediction_active = len(state.predictions) > 0
			else:
				state.predictions = []
				state.prediction_active = False
			refresh_ui()
		return


def fire_single(key):
	"""Execute a single-key action with multi-tap gear cycling."""
	shift_held = keyboard.is_pressed("shift")
	now = time.time()

	# Handle mode keys
	if key == "t":
		state.qwerc_gear = 0
		state.last_fired_key = None
		print_status()
		return
	if key == "y":
		state.muiop_gear = 0
		state.last_fired_key = None
		print_status()
		return

	# Multi-tap detection
	if key == state.last_fired_key and (now - state.last_fired_time) < MULTI_TAP_WINDOW:
		state.tap_gear_offset += 1
		send_key("backspace")
		# Also trim from current_word
		if state.current_word:
			state.current_word = state.current_word[:-1]
	else:
		state.tap_gear_offset = 0

	state.last_fired_key = key
	state.last_fired_time = now

	left_pages, right_pages = get_current_pages()

	if key in QWERC_KEYS:
		idx = QWERC_KEYS.index(key)
		num_pages = len(left_pages)
		effective_gear = (state.qwerc_gear + state.tap_gear_offset) % num_pages
		char_page = get_page(left_pages, effective_gear)
		emit_char(char_page[idx], shift_held)
	elif key in MUIOP_KEYS:
		idx = MUIOP_KEYS.index(key)
		num_pages = len(right_pages)
		effective_gear = (state.muiop_gear + state.tap_gear_offset) % num_pages
		char_page = get_page(right_pages, effective_gear)
		emit_char(char_page[idx], shift_held)


def boxed(chars):
	return " ".join(f"[{c}]" for c in chars)


def print_header():
	from config import FREQUENCY_ORDER
	print("\U0001f524 English letter frequency: " + " ".join(FREQUENCY_ORDER))
	print("   Interleaved blocks of 5 (QWERC/MUIOP alternating)")
	print("   QWERC pages: " + " | ".join("".join(page) for page in QWERC_PAGES))
	print("   MUIOP pages: " + " | ".join("".join(page) for page in MUIOP_PAGES))


def print_status():
	label = "\u25b6 ACTIVE" if state.active else "\u23f8 PAUSED"
	mode_display = f"[{state.current_mode.upper()}]"
	RESET = "\033[0m"
	ACTIVE_COLOR = "\033[1;96m"
	ACTIVE_COLOR_ALT = "\033[1;92m"
	HELP_COLOR = "\033[1;93m"
	THUMB_COLOR = "\033[1;95m"

	def colored_boxed(chars, color1, color2):
		result = []
		for i, c in enumerate(chars):
			color = color1 if i % 2 == 0 else color2
			result.append(f"{color}[{c}]{RESET}")
		return " ".join(result)

	left_pages, right_pages = get_current_pages()
	max_pages = max(len(left_pages), len(right_pages))

	print(f"\n {label} {mode_display}")
	print(f"    {HELP_COLOR}4   3   2   1{RESET}           {HELP_COLOR}1   2   3   4{RESET}")

	for g in range(max_pages):
		left_chars = get_page(left_pages, g) if g < len(left_pages) else ["\u00b7"] * 5
		right_chars = get_page(right_pages, g) if g < len(right_pages) else ["\u00b7"] * 5

		left_active = (g == state.qwerc_gear)
		right_active = (g == state.muiop_gear)

		left_main = left_chars[:4]
		right_main = right_chars[1:]
		left_thumb = left_chars[4]
		right_thumb = right_chars[0]

		if left_active:
			left_marker = "\u25b6"
			left_text = colored_boxed(left_main, ACTIVE_COLOR, ACTIVE_COLOR_ALT)
		else:
			left_marker = "\u2715"
			left_text = boxed(left_main)

		if right_active:
			right_text = colored_boxed(right_main, ACTIVE_COLOR, ACTIVE_COLOR_ALT)
			right_marker = "\u25c0"
		else:
			right_text = boxed(right_main)
			right_marker = "\u2715"

		if left_active:
			lt = f"{THUMB_COLOR}[{left_thumb}]{RESET}"
		else:
			lt = f"[{left_thumb}]"
		if right_active:
			rt = f"{THUMB_COLOR}[{right_thumb}]{RESET}"
		else:
			rt = f"[{right_thumb}]"

		print(f" {left_marker} {left_text}    \u2502    {right_text} {right_marker}")
		print(f"                  {lt} \u2502 {rt}")

	# Show predictions in terminal too
	if state.prediction_active and state.predictions:
		pred_str = "  ".join(f"[{i+1}] {w}" for i, w in enumerate(state.predictions))
		print(f"\n  \U0001f4a1 {pred_str}")

	refresh_ui()
