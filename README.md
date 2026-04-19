# QWER-UIOP

> A passion project exploring a new way to type — using fewer keys, smarter layouts, and chord-based input.

## What is this?

This is an experimental keyboard input system that remaps just a handful of keys on a standard QWERTY keyboard to type **every letter, number, and symbol**. Instead of reaching across 40+ keys, you use only the home row and a "gear" system to page through characters ordered by English letter frequency.

The goal? Either **type faster** or **type with fewer keys** — I haven't decided yet! Maybe both.

## How it works

- Each hand controls a set of keys (the "fingers")
- Characters are arranged in **pages** sorted by English letter frequency (`e t a o i n s h r d ...`)
- Press a finger key to type the character mapped to it on the current page
- Press **two keys together** (a chord) to switch pages (gears), navigate, or perform actions
- A **space double-tap** sends Enter

### Modes

- **Letters** — English alphabet, frequency-ordered across pages
- **Numbers** — Digits 0–9 and common arithmetic symbols
- **Symbols** — Punctuation and special characters

## Versions

### v1 — `QWER-UIOP.py`

The original prototype. Four fingers per hand:

| Left hand | Right hand |
|-----------|------------|
| Q W E R   | U I O P    |

- 4 characters per page
- Chord detection via **key release** (wait for all keys to be released before deciding single vs combo)
- Mode keys: T / Y

### v2 — `QWERC.py`

Five fingers per hand — adds the thumb:

| Left hand   | Right hand  |
|-------------|-------------|
| Q W E R C   | M U I O P   |

- 5 characters per page (fewer page switches needed)
- **Timer-based chord detection** (~40ms window) instead of key-release — single keys fire almost instantly, chords are detected if a second key arrives within the window. Much snappier.
- Gear combos: Q+W / E+R (left), U+I / O+P (right)
- Navigation: Q+M (left arrow), C+P (right arrow), W+O (backspace)
- Mode cycle: T+Y

## Quick start

```bash
pip install keyboard
python QWERC.py
```

> Requires **administrator/elevated privileges** on Windows since the `keyboard` library hooks global key events.

## Controls (v2)

| Action              | Keys         |
|---------------------|--------------|
| Type character      | Single finger key |
| Shift (uppercase)   | Hold Shift + key |
| Left gear up        | E+R          |
| Left gear down      | Q+W          |
| Right gear up       | U+I          |
| Right gear down     | O+P          |
| Reset left gear     | T            |
| Reset right gear    | Y            |
| Cycle mode          | T+Y          |
| Left arrow          | Q+M          |
| Right arrow         | C+P          |
| Backspace           | W+O          |
| Space               | Space        |
| Enter               | Space double-tap |
| Pause / Resume      | Ctrl+Shift+A |
| Quit                | Ctrl+Shift+Z |

## Why?

Standard keyboards were designed for typewriters, not humans. This project asks: *what if we could type everything with just 10–12 keys and a bit of muscle memory?*

It's a work in progress, a playground for ideas, and honestly just fun to build.

## License

Do whatever you want with it.
