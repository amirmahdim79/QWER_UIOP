# QWERC — main entry point

import keyboard
import threading

import state
from config import MANAGED_KEYS
from chords import on_key
from input_handler import print_header, print_status
from floating_ui import FloatingUI
from predictor import predictor
from autocorrect import autocorrector


def toggle_pause():
	state.active = not state.active
	print_status()


def quit_app():
	print("\n\U0001f44b Quitting...")
	predictor.save_now()
	autocorrector.save_now()
	keyboard.unhook_all()
	if state.floating_ui is not None:
		state.floating_ui.close()
		state.floating_ui = None
	state.quit_event.set()


def _run_floating_ui():
	try:
		state.floating_ui = FloatingUI()
		state.floating_ui.run()
	except Exception as e:
		print(f"[FloatingUI] Could not start: {e}")
		state.floating_ui = None


def main():
	print_header()
	print("\nControls:")
	print("  Q W E R C     \u2192 type QWERC page letters (left hand)")
	print("  M U I O P     \u2192 type MUIOP page letters (right hand)")
	print("  Shift+key     \u2192 uppercase")
	print("  T             \u2192 reset left gear to 0")
	print("  Y             \u2192 reset right gear to 0")
	print("  Q+W hold      \u2192 left gear down")
	print("  E+R hold      \u2192 left gear up")
	print("  U+I hold      \u2192 right gear up")
	print("  O+P hold      \u2192 right gear down")
	print("  Q+M hold      \u2192 \u2190 arrow")
	print("  C+P hold      \u2192 \u2192 arrow")
	print("  W+O hold      \u2192 backspace")
	print("  T+Y hold      \u2192 cycle modes (letters/numbers/symbols)")
	print("  Q+P hold      \u2192 accept top word prediction")
	print("  C+M/U/I/O     \u2192 accept prediction #1/#2/#3/#4")
	print("  M+P hold      \u2192 toggle autocorrect on/off")
	print("  Space         \u2192 space (double-tap \u2192 enter)")
	print("\n  3-key chords:")
	print("  Q+W+E         \u2192 delete word left")
	print("  W+E+R         \u2192 delete word right")
	print("  Q+W+R         \u2192 delete line")
	print("  U+I+O         \u2192 select word")
	print("  I+O+P         \u2192 select line")
	print("  M+U+I         \u2192 word left")
	print("  U+O+P         \u2192 word right")
	print("  Q+W+M         \u2192 copy")
	print("  E+R+M         \u2192 paste")
	print("  Q+R+M         \u2192 cut")
	print("  Q+E+C         \u2192 undo")
	print("  W+R+C         \u2192 redo")
	print("  Q+W+C         \u2192 tab")
	print("  M+O+P         \u2192 home")
	print("  M+U+P         \u2192 end")
	print("\n  Ctrl+Shift+A  \u2192 pause / resume")
	print("  Ctrl+Shift+Z  \u2192 quit")

	ui_thread = threading.Thread(target=_run_floating_ui, daemon=True)
	ui_thread.start()

	print_status()

	for key in MANAGED_KEYS:
		keyboard.hook_key(key, on_key, suppress=True)

	keyboard.hook_key("space", on_key, suppress=True)

	keyboard.add_hotkey("ctrl+shift+a", toggle_pause)
	keyboard.add_hotkey("ctrl+shift+z", quit_app)

	state.quit_event.wait()


if __name__ == "__main__":
	main()
