# Word prediction engine
#
# Architecture:
#   - Dictionary-based prefix matching (fast, works offline)
#   - Frequency-weighted results (common words rank higher)
#   - Pluggable: swap in n-gram or LLM backend later
#
# The word list is loaded once at startup from a bundled frequency file.
# If no file exists, a built-in top-5000 list is used as fallback.

import os
import json
from config import MAX_PREDICTIONS

# ---------------------------------------------------------------------------
# Built-in fallback: top ~1000 English words by frequency
# Source: condensed from various public-domain frequency lists
# ---------------------------------------------------------------------------
_BUILTIN_WORDS = [
	"the", "be", "to", "of", "and", "a", "in", "that", "have", "i",
	"it", "for", "not", "on", "with", "he", "as", "you", "do", "at",
	"this", "but", "his", "by", "from", "they", "we", "say", "her", "she",
	"or", "an", "will", "my", "one", "all", "would", "there", "their", "what",
	"so", "up", "out", "if", "about", "who", "get", "which", "go", "me",
	"when", "make", "can", "like", "time", "no", "just", "him", "know", "take",
	"people", "into", "year", "your", "good", "some", "could", "them", "see",
	"other", "than", "then", "now", "look", "only", "come", "its", "over",
	"think", "also", "back", "after", "use", "two", "how", "our", "work",
	"first", "well", "way", "even", "new", "want", "because", "any", "these",
	"give", "day", "most", "us", "great", "between", "need", "large", "under",
	"never", "same", "last", "long", "another", "right", "still", "own",
	"point", "keep", "help", "every", "home", "while", "off", "old", "might",
	"school", "very", "through", "life", "much", "before", "turn", "here",
	"where", "after", "world", "should", "call", "still", "high", "each",
	"must", "place", "little", "begin", "being", "hand", "part", "once",
	"those", "tell", "run", "real", "left", "open", "seem", "show", "always",
	"next", "too", "move", "such", "public", "both", "end", "does", "live",
	"number", "house", "change", "water", "read", "question", "city", "area",
	"small", "find", "head", "down", "side", "since", "group", "problem",
	"line", "start", "name", "play", "state", "move", "try", "late", "talk",
	"few", "may", "put", "let", "many", "hard", "far", "best", "set", "book",
	"eye", "close", "love", "power", "story", "become", "family", "child",
	"again", "different", "country", "learn", "answer", "important", "stop",
	"men", "women", "room", "young", "social", "early", "case", "money",
	"idea", "enough", "eat", "face", "watch", "above", "really", "already",
	"believe", "body", "nothing", "bring", "together", "without", "possible",
	"human", "until", "less", "morning", "company", "example", "during",
	"fact", "kind", "sure", "mean", "often", "car", "night", "light", "word",
	"almost", "table", "program", "system", "write", "might", "never",
	"interest", "against", "per", "plan", "better", "though", "second",
	"away", "mother", "father", "friend", "mind", "door", "anything",
	"today", "done", "feel", "follow", "game", "leave", "week", "thing",
	"level", "stand", "clear", "order", "full", "whole", "reason",
	"half", "person", "art", "war", "history", "party", "within", "grow",
	"result", "spend", "among", "ever", "bad", "street", "white", "black",
	"language", "experience", "along", "able", "often", "town", "drive",
	"paper", "offer", "care", "share", "hold", "land", "service", "voice",
	"market", "support", "note", "office", "wife", "team", "report", "bit",
	"member", "carry", "add", "building", "strong", "teacher", "process",
	"window", "produce", "picture", "class", "control", "period", "recent",
	"common", "value", "cut", "rate", "cover", "usually", "past", "yes",
	"music", "pay", "west", "position", "total", "wish", "sometimes",
	"contain", "south", "son", "daughter", "husband", "age", "red",
	"across", "behind", "sort", "rather", "sit", "low", "date", "send",
	"expect", "record", "cause", "continue", "perhaps", "true", "step",
	"remember", "hundred", "five", "similar", "center", "measure", "toward",
	"data", "cost", "include", "develop", "probably", "act", "form",
	"stay", "general", "simple", "free", "single", "suddenly", "study",
	"happy", "appear", "model", "either", "minute", "walk", "view", "hour",
	"force", "front", "type", "later", "chance", "short", "road", "rise",
	"north", "computer", "break", "fall", "edge", "sign", "wait", "pass",
	"sell", "fight", "surface", "deep", "industry", "test", "wall",
	"actually", "rest", "lay", "accept", "deal", "piece", "allow", "arm",
	"heart", "bank", "join", "season", "draw", "board", "hair", "age",
	"list", "energy", "quite", "base", "indeed", "store", "present",
	"thought", "national", "amount", "course", "sound", "meet", "image",
	"field", "policy", "several", "health", "create", "boat", "buy",
	"consider", "figure", "huge", "plant", "color", "brother", "baby",
	"material", "film", "hundred", "rule", "effort", "treat", "return",
	"kill", "trip", "food", "sea", "likely", "summer", "river", "hot",
	"cold", "dark", "glass", "oil", "player", "direct", "manager",
	"letter", "blue", "ball", "ground", "chance", "product", "anyone",
	"fish", "term", "rock", "size", "modern", "top", "whole", "king",
	"current", "fear", "design", "catch", "cup", "practice", "reach",
	"unit", "fly", "bed", "mile", "garden", "finish", "church", "close",
	"fire", "dog", "win", "drop", "purpose", "hospital", "future",
	"ready", "green", "press", "space", "everyone", "tree", "lake",
	"earth", "save", "animal", "window", "song", "imagine", "manage",
	"enter", "source", "bird", "attack", "river", "pain", "enjoy",
	"safe", "trouble", "smile", "wrong", "prepare", "miss", "event",
	"supply", "agree", "star", "pull", "skin", "brother", "dress",
	"husband", "student", "require", "sweet", "captain", "teach", "goal",
	"hit", "dead", "soft", "count", "loss", "street", "beautiful",
	"discover", "serve", "throw", "dry", "clean", "hang", "gather",
	"weather", "central", "fill", "corner", "pick", "sir", "camp",
	"brain", "impossible", "favor", "rain", "finger", "nor", "spot",
	"train", "teeth", "ring", "leg", "speed", "tall", "crowd", "boat",
	"band", "wild", "truck", "sing", "month", "sleep", "project", "raise",
	"shot", "wish", "chair", "whose", "forest", "nor", "snow", "warm",
	"charge", "hill", "kitchen", "mass", "glad", "wood", "key", "ear",
	"seat", "evening", "farm", "fly", "gray", "chief", "sand", "quiet",
	"push", "nose", "soldier", "horse", "island", "thick", "thin",
	"deep", "storm", "village", "screen", "iron", "wing", "peace",
	"strange", "rush", "stone", "bone", "sharp", "judge", "gold",
	"moon", "sun", "stick", "wire", "mark", "shock", "fresh", "steel",
	"neck", "tool", "root", "lake", "crowd", "gift", "coat", "milk",
	"price", "bread", "block", "luck", "tip", "mad", "guard", "rich",
]


class WordPredictor:
	"""Prefix-based word predictor with frequency ranking."""

	def __init__(self, word_file=None):
		# word -> frequency rank (lower = more common)
		self._words = {}
		self._load(word_file)

	def _load(self, word_file):
		"""Load word list. Try external file first, fall back to built-in."""
		if word_file and os.path.isfile(word_file):
			try:
				with open(word_file, "r", encoding="utf-8") as f:
					ext = os.path.splitext(word_file)[1].lower()
					if ext == ".json":
						data = json.load(f)
						# Support {"word": freq} or ["word", ...]
						if isinstance(data, dict):
							self._words = {w.lower(): r for w, r in data.items()}
						else:
							self._words = {w.lower(): i for i, w in enumerate(data)}
					else:
						# Plain text: one word per line, rank = line number
						for i, line in enumerate(f):
							w = line.strip().lower()
							if w and w not in self._words:
								self._words[w] = i
				if self._words:
					return
			except Exception:
				pass

		# Fallback: built-in list
		seen = set()
		rank = 0
		for w in _BUILTIN_WORDS:
			wl = w.lower()
			if wl not in seen:
				self._words[wl] = rank
				seen.add(wl)
				rank += 1

	def predict(self, prefix, max_results=MAX_PREDICTIONS):
		"""Return up to max_results words starting with prefix, ranked by frequency."""
		if not prefix:
			return []
		p = prefix.lower()
		matches = [(w, r) for w, r in self._words.items() if w.startswith(p) and w != p]
		matches.sort(key=lambda x: x[1])
		return [w for w, _ in matches[:max_results]]

	def add_word(self, word):
		"""Learn a new word (user-typed). Assign high frequency (will appear in results)."""
		wl = word.lower()
		if wl not in self._words and len(wl) >= 2:
			# Give it a middling rank so it shows up but doesn't dominate
			self._words[wl] = len(self._words) // 2

	def boost_word(self, word):
		"""Boost a word's rank after the user accepts it (make it appear sooner)."""
		wl = word.lower()
		if wl in self._words and self._words[wl] > 0:
			self._words[wl] = max(0, self._words[wl] - 5)


# Singleton instance — created at import time
predictor = WordPredictor()
