# Auto-correction engine
#
# - Edit-distance based correction against the known dictionary
# - Built-in common typo map for instant fixes
# - Learns user corrections (if user backspaces and retypes)
# - Persists learned corrections to disk

import os
import json
import threading

_USER_DATA_DIR = os.path.dirname(os.path.abspath(__file__))
_USER_CORRECTIONS_FILE = os.path.join(_USER_DATA_DIR, "user_corrections.json")

# Common English typos: wrong -> correct
_BUILTIN_TYPOS = {
	"teh": "the", "hte": "the", "thier": "their", "recieve": "receive",
	"occured": "occurred", "seperate": "separate", "definately": "definitely",
	"occurence": "occurrence", "accomodate": "accommodate", "wierd": "weird",
	"untill": "until", "wich": "which", "becuase": "because", "beleive": "believe",
	"freind": "friend", "goverment": "government", "happend": "happened",
	"immediatly": "immediately", "neccessary": "necessary", "occurr": "occur",
	"succesful": "successful", "tommorow": "tomorrow", "togehter": "together",
	"enviroment": "environment", "begining": "beginning", "doesnt": "doesn't",
	"didnt": "didn't", "dont": "don't", "wont": "won't", "cant": "can't",
	"shouldnt": "shouldn't", "wouldnt": "wouldn't", "couldnt": "couldn't",
	"isnt": "isn't", "wasnt": "wasn't", "werent": "weren't", "arent": "aren't",
	"havent": "haven't", "hasnt": "hasn't", "im": "i'm", "ive": "i've",
	"youre": "you're", "theyre": "they're", "weve": "we've", "hes": "he's",
	"shes": "she's", "thats": "that's", "whats": "what's", "whos": "who's",
	"adn": "and", "jsut": "just", "taht": "that", "waht": "what",
	"ahve": "have", "tiem": "time", "liek": "like", "knwo": "know",
	"form": "from", "soem": "some", "owrk": "work", "yera": "year",
	"baout": "about", "coudl": "could", "shoudl": "should", "woudl": "would",
	"peopel": "people", "htink": "think", "beacuse": "because",
}


def _edit_distance(a, b):
	"""Compute Levenshtein edit distance between two strings."""
	la, lb = len(a), len(b)
	if la == 0:
		return lb
	if lb == 0:
		return la

	# Use single-row DP for memory efficiency
	prev = list(range(lb + 1))
	for i in range(1, la + 1):
		curr = [i] + [0] * lb
		for j in range(1, lb + 1):
			cost = 0 if a[i - 1] == b[j - 1] else 1
			curr[j] = min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
		prev = curr
	return prev[lb]


class AutoCorrector:
	"""Edit-distance auto-corrector with typo map and learning."""

	def __init__(self):
		# typo -> correction (user-learned overrides built-in)
		self._corrections = dict(_BUILTIN_TYPOS)
		self._user_corrections = {}
		self._dirty = False
		self._save_timer = None
		self._load_user_corrections()

	def correct(self, word, dictionary):
		"""
		Try to correct a word. Returns (corrected_word, was_corrected).
		
		dictionary: dict of {word: rank} from the predictor — used for
		            edit-distance matching when no direct typo map hit.
		"""
		wl = word.lower()

		# 1) Direct typo map hit (instant, no distance calc)
		if wl in self._corrections:
			return self._corrections[wl], True

		# 2) Already a known word — no correction needed
		if wl in dictionary:
			return word, False

		# 3) Edit-distance search: find closest word within distance 1-2
		#    Only consider words of similar length to avoid nonsense matches
		best_word = None
		best_dist = 2  # only accept distance 1 (this is the threshold, strict <)
		best_rank = float("inf")

		for candidate, rank in dictionary.items():
			# Skip if length difference alone exceeds our threshold
			if abs(len(candidate) - len(wl)) > 2:
				continue
			dist = _edit_distance(wl, candidate)
			if dist < best_dist or (dist == best_dist and rank < best_rank):
				best_dist = dist
				best_word = candidate
				best_rank = rank

		if best_word:
			return best_word, True

		return word, False

	def learn_correction(self, wrong, right):
		"""Learn a user correction: wrong -> right."""
		wl = wrong.lower()
		rl = right.lower()
		if wl != rl and len(wl) >= 2:
			self._corrections[wl] = rl
			self._user_corrections[wl] = rl
			self._schedule_save()

	# --- Persistence ---

	def _load_user_corrections(self):
		if not os.path.isfile(_USER_CORRECTIONS_FILE):
			return
		try:
			with open(_USER_CORRECTIONS_FILE, "r", encoding="utf-8") as f:
				data = json.load(f)
			if isinstance(data, dict):
				for wrong, right in data.items():
					self._corrections[wrong.lower()] = right.lower()
					self._user_corrections[wrong.lower()] = right.lower()
		except Exception:
			pass

	def _schedule_save(self):
		self._dirty = True
		if self._save_timer is not None:
			self._save_timer.cancel()
		self._save_timer = threading.Timer(5.0, self._save_user_corrections)
		self._save_timer.daemon = True
		self._save_timer.start()

	def _save_user_corrections(self):
		if not self._dirty:
			return
		try:
			with open(_USER_CORRECTIONS_FILE, "w", encoding="utf-8") as f:
				json.dump(self._user_corrections, f, ensure_ascii=False)
			self._dirty = False
		except Exception:
			pass

	def save_now(self):
		if self._save_timer is not None:
			self._save_timer.cancel()
			self._save_timer = None
		self._save_user_corrections()


# Singleton
autocorrector = AutoCorrector()
