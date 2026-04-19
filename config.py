# Character layouts, key mappings, and constants

# English letter frequency (sorted, lowercase)
FREQUENCY_ORDER = list("etaoinshrdlcumwfgypbvkjxqz")

# Interleaved blocks of 5 from frequency order:
# block1 -> QWERC, block2 -> MUIOP, block3 -> QWERC, block4 -> MUIOP, ...
_BLOCKS = [FREQUENCY_ORDER[i:i+5] for i in range(0, len(FREQUENCY_ORDER), 5)]
QWERC_PAGES = [_BLOCKS[i] for i in range(0, len(_BLOCKS), 2)]
MUIOP_PAGES = [_BLOCKS[i] for i in range(1, len(_BLOCKS), 2)]

QWERC_CHARS = [ch for page in QWERC_PAGES for ch in page]
MUIOP_CHARS = [ch for page in MUIOP_PAGES for ch in page]

# Numbers (0-9)
NUMBER_PAGES = [["0", "1", "2", "3", "4"], ["5", "6", "7", "8", "9"], [".", ",", "+", "-", "*"]]

# Common symbols (sorted by usage frequency, most -> least)
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

# Timing constants
CHORD_WINDOW = 0.04        # 40ms — fast enough to feel instant, wide enough to catch chords
MULTI_TAP_WINDOW = 0.3     # 300ms window to detect repeated taps on same key
SPACE_DOUBLE_TAP_WINDOW = 0.3  # 300ms window to detect double-tap

# Prediction
PREDICTION_ACCEPT_COMBO = frozenset({"q", "p"})  # chord to accept top prediction
PREDICTION_PICK_COMBOS = {
	frozenset({"c", "m"}): 0,  # C+M → prediction #1
	frozenset({"c", "u"}): 1,  # C+U → prediction #2
	frozenset({"c", "i"}): 2,  # C+I → prediction #3
	frozenset({"c", "o"}): 3,  # C+O → prediction #4
}
MAX_PREDICTIONS = 4

# Auto-correction
AUTOCORRECT_TOGGLE_COMBO = frozenset({"m", "p"})  # M+P to toggle autocorrect on/off

# 3-key chords — editing & selection
THREE_KEY_COMBOS = {
	# Left hand: word-level editing
	frozenset({"q", "w", "e"}): "delete_word_left",    # Q+W+E → delete word left
	frozenset({"w", "e", "r"}): "delete_word_right",   # W+E+R → delete word right
	frozenset({"q", "w", "r"}): "delete_line",         # Q+W+R → delete entire line

	# Right hand: selection & movement
	frozenset({"u", "i", "o"}): "select_word",         # U+I+O → select word (double-click equivalent)
	frozenset({"i", "o", "p"}): "select_line",         # I+O+P → select entire line
	frozenset({"m", "u", "i"}): "word_left",           # M+U+I → move cursor one word left
	frozenset({"i", "o", "p"}): "select_line",         # I+O+P → select line
	frozenset({"u", "o", "p"}): "word_right",          # U+O+P → move cursor one word right

	# Cross-hand: clipboard
	frozenset({"q", "w", "m"}): "copy",                # Q+W+M → copy
	frozenset({"e", "r", "m"}): "paste",               # E+R+M → paste
	frozenset({"q", "r", "m"}): "cut",                 # Q+R+M → cut
	frozenset({"q", "e", "c"}): "undo",                # Q+E+C → undo
	frozenset({"w", "r", "c"}): "redo",                # W+R+C → redo

	# Tab / navigation
	frozenset({"q", "w", "c"}): "tab",                 # Q+W+C → tab
	frozenset({"m", "o", "p"}): "home",                # M+O+P → home
	frozenset({"m", "u", "p"}): "end",                 # M+U+P → end
}
