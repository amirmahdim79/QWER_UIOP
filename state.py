# Mutable global state shared across modules

import threading
import queue

current_mode = "letters"
mode_index = 0

qwerc_gear = 0
muiop_gear = 0
active = True
is_emitting = False
quit_event = threading.Event()

# Timer-based chord detection state
lock = threading.Lock()
pending_key = None
pending_timer = None
held_keys = set()
chord_mode = False
chord_fired = False
peak_keys = set()

# Multi-tap gear cycling
last_fired_key = None
last_fired_time = 0.0
tap_gear_offset = 0

# Space double-tap detection
space_tap_timer = None
space_tap_count = 0

# Word prediction state
current_word = ""           # characters typed so far in the current word
predictions = []            # list of predicted words
prediction_active = False   # whether predictions are currently showing

# Floating UI
ui_queue = queue.Queue()
floating_ui = None
