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
MUIOP_KEYS = ["n", "u", "i", "o", "p"]
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
MAX_PREDICTIONS = 4
