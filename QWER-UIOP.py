import keyboard
import threading

# 🔤 English letter frequency (sorted, lowercase)
FREQUENCY_ORDER = list("etaoinshrdlcumwfgypbvkjxqz")

# Split into two halves: 13 each
QWER_CHARS = FREQUENCY_ORDER[:13]  # e t a o i n s h r d l c u
UIOP_CHARS = FREQUENCY_ORDER[13:]  # m w f g y p b v k j x q z

# Pages of 4 for each half
QWER_PAGES = [QWER_CHARS[i:i+4] for i in range(0, len(QWER_CHARS), 4)]
UIOP_PAGES = [UIOP_CHARS[i:i+4] for i in range(0, len(UIOP_CHARS), 4)]

QWER_KEYS = ["q", "w", "e", "r"]
UIOP_KEYS = ["u", "i", "o", "p"]

MANAGED_KEYS = set(QWER_KEYS + UIOP_KEYS + ["c", "v", "n", "m"])

qwer_gear = 0
uiop_gear = 0
active = True
is_emitting = False
quit_event = threading.Event()

# Chord detection state
held_keys = set()       # currently held managed keys
peak_keys = set()       # max set of keys held during current chord
chord_active = False    # are we in a chord (2+ keys were held)?
chord_fired = False     # did we already fire for this chord?


def get_page(pages, gear):
	"""Get current page of 4 chars for the gear (clamped)."""
	g = max(0, min(gear, len(pages) - 1))
	page = pages[g]
	# Pad to 4 if last page is short
	return (page + ["·"] * 4)[:4]


def boxed(chars):
	"""Format chars in boxes: [e] [t] [a] [o]"""
	return " ".join(f"[{c}]" for c in chars)


def print_header():
	print("🔤 English letter frequency: " + " ".join(FREQUENCY_ORDER))
	print("   Left half (QWER):  " + " ".join(QWER_CHARS))
	print("   Right half (UIOP): " + " ".join(UIOP_CHARS))


def print_status():
	state = "▶ ACTIVE" if active else "⏸ PAUSED"

	def gear_line(left_pages, left_gear, right_pages, right_gear):
		if 0 <= left_gear < len(left_pages):
			left_text = boxed(get_page(left_pages, left_gear))
			left_label = f"⟨{left_gear}⟩"
		else:
			left_text = boxed(["·", "·", "·", "·"])
			left_label = "⟨-⟩"

		if 0 <= right_gear < len(right_pages):
			right_text = boxed(get_page(right_pages, right_gear))
			right_label = f"⟨{right_gear}⟩"
		else:
			right_text = boxed(["·", "·", "·", "·"])
			right_label = "⟨-⟩"

		return f" {left_label} {left_text} │ {right_text} {right_label}"

	prev_line = gear_line(QWER_PAGES, qwer_gear - 1, UIOP_PAGES, uiop_gear - 1)
	curr_line = gear_line(QWER_PAGES, qwer_gear, UIOP_PAGES, uiop_gear)
	next_line = gear_line(QWER_PAGES, qwer_gear + 1, UIOP_PAGES, uiop_gear + 1)

	print(f"\n {state}")
	print(prev_line)
	print(curr_line)
	print(next_line)


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


def execute_combo(keys):
	"""Execute action for non-overlapping two-key combos."""
	global qwer_gear, uiop_gear
	combo = frozenset(keys)

	# Gear combos
	if combo == frozenset({"q", "w"}):
		qwer_gear = max(qwer_gear - 1, 0)
		print_status()
		return
	if combo == frozenset({"e", "r"}):
		qwer_gear = min(qwer_gear + 1, len(QWER_PAGES) - 1)
		print_status()
		return
	if combo == frozenset({"u", "i"}):
		uiop_gear = min(uiop_gear + 1, len(UIOP_PAGES) - 1)
		print_status()
		return
	if combo == frozenset({"o", "p"}):
		uiop_gear = max(uiop_gear - 1, 0)
		print_status()
		return

	# Navigation / edit combos (non-overlapping)
	if combo == frozenset({"q", "u"}):
		send_key("left")
		return
	if combo == frozenset({"r", "p"}):
		send_key("right")
		return
	if combo == frozenset({"w", "o"}):
		send_key("backspace")
		return


def fire_single(key):
	"""Execute a single-key action."""
	global qwer_gear, uiop_gear

	shift_held = keyboard.is_pressed("shift")

	if key == "v":
		qwer_gear = min(qwer_gear + 1, len(QWER_PAGES) - 1)
		print_status()
		return
	if key == "c":
		qwer_gear = max(qwer_gear - 1, 0)
		print_status()
		return
	if key == "n":
		uiop_gear = min(uiop_gear + 1, len(UIOP_PAGES) - 1)
		print_status()
		return
	if key == "m":
		uiop_gear = max(uiop_gear - 1, 0)
		print_status()
		return

	left = get_page(QWER_PAGES, qwer_gear)
	right = get_page(UIOP_PAGES, uiop_gear)

	if key in QWER_KEYS:
		idx = QWER_KEYS.index(key)
		emit_char(left[idx], shift_held)
	elif key in UIOP_KEYS:
		idx = UIOP_KEYS.index(key)
		emit_char(right[idx], shift_held)


def on_key(event):
	global chord_active, chord_fired, peak_keys

	if is_emitting:
		return

	key = event.name
	if key not in MANAGED_KEYS:
		return

	if event.event_type == "down":
		if key in held_keys:
			return  # key repeat
		held_keys.add(key)

		if not active:
			return

		# If 2+ keys now held, we're in a chord — accumulate peak
		if len(held_keys) >= 2:
			chord_active = True
			chord_fired = False
			if len(held_keys) > len(peak_keys):
				peak_keys = set(held_keys)  # keep largest simultaneous set seen
		# else: single key down, don't emit yet — wait for up

	else:  # up
		held_keys.discard(key)

		if not active:
			return

		if chord_active:
			# Fire combo only when chord fully ends (all managed keys released)
			if len(held_keys) == 0:
				if not chord_fired:
					chord_fired = True
					execute_combo(peak_keys)
				chord_active = False
				chord_fired = False
				peak_keys = set()
		else:
			# Single key tap: key went down and back up without another key joining
			if len(held_keys) == 0:
				fire_single(key)


def toggle_pause():
	global active
	active = not active
	print_status()


def quit_app():
	print("\n👋 Quitting...")
	keyboard.unhook_all()
	quit_event.set()


def main():
	print_header()
	print("\nControls:")
	print("  Q W E R       → type left-half letters")
	print("  U I O P       → type right-half letters")
	print("  Shift+key     → uppercase")
	print("  C / V         → left gear down / up")
	print("  N / M         → right gear up / down")
	print("  Q+W hold      → left gear down")
	print("  E+R hold      → left gear up")
	print("  U+I hold      → right gear up")
	print("  O+P hold      → right gear down")
	print("  Q+U hold      → ← arrow")
	print("  R+P hold      → → arrow")
	print("  W+O hold      → backspace")
	print("  Ctrl+Shift+C  → pause / resume")
	print("  Ctrl+Shift+Z  → quit")
	print("  All other keys work normally.")

	print_status()

	for key in MANAGED_KEYS:
		keyboard.hook_key(key, on_key, suppress=True)

	keyboard.add_hotkey("ctrl+shift+c", toggle_pause)
	keyboard.add_hotkey("ctrl+shift+z", quit_app)

	quit_event.wait()


if __name__ == "__main__":
	main()
