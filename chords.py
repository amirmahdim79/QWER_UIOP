# Chord detection — timer-based approach
# Detects single keys vs simultaneous key combos within a timing window

import threading
import keyboard

import state
from config import MANAGED_KEYS, CHORD_WINDOW
from input_handler import fire_single, execute_combo, handle_space


def _fire_pending():
	"""Timer callback: no second key arrived within CHORD_WINDOW, fire as single key."""
	with state.lock:
		key = state.pending_key
		state.pending_key = None
		state.pending_timer = None
	if key and state.active:
		fire_single(key)


def on_key(event):
	if state.is_emitting:
		return

	key = event.name

	# Handle space separately for double-tap
	if key == "space":
		if event.event_type == "down":
			if not state.active:
				return
			handle_space()
		return

	if key not in MANAGED_KEYS:
		return

	if event.event_type == "down":
		if key in state.held_keys:
			return  # key repeat — ignore

		state.held_keys.add(key)

		if not state.active:
			return

		with state.lock:
			if state.chord_mode:
				if len(state.held_keys) > len(state.peak_keys):
					state.peak_keys = set(state.held_keys)
			elif state.pending_key is not None:
				if state.pending_timer is not None:
					state.pending_timer.cancel()
					state.pending_timer = None
				state.chord_mode = True
				state.chord_fired = False
				state.peak_keys = set(state.held_keys)
				state.pending_key = None
			else:
				state.pending_key = key
				state.pending_timer = threading.Timer(CHORD_WINDOW, _fire_pending)
				state.pending_timer.start()

	else:  # up
		state.held_keys.discard(key)

		if not state.active:
			return

		with state.lock:
			if state.chord_mode:
				if len(state.held_keys) == 0:
					if not state.chord_fired:
						state.chord_fired = True
						execute_combo(state.peak_keys)
					state.chord_mode = False
					state.chord_fired = False
					state.peak_keys = set()
