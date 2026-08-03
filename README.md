# 🎮 Yea — Checker Tools

A collection of powerful checker tools for card validation and Fortnite account checking.

> **Developer:** @xghost123 | **Channel:** https://t.me/wolfstoren

---

## 🔫 Fortnite Account Checker (`fortnitechecker.py`)

Checks Fortnite / Epic Games accounts from a combo list and tells you which ones are valid, 2FA-protected, or dead.

### ✅ Features
- Fast multi-threaded checking (up to 5 threads)
- Supports `email:pass` and `user:pass` combo formats (`:` or `|` separator)
- Results: ✅ Valid / 🔐 2FA / ❌ Invalid / ⚠️ Error
- Saves valid accounts to a timestamped `.txt` file
- Optional proxy support (round-robin or random rotation)
- Optional Telegram notifications for every valid hit + summary

### ⚙️ Requirements

**Python 3.8+** and the following packages:

```
pip install requests colorama brotli requests-toolbelt
```

### 🚀 How to Run

1. Create a combo file (e.g. `combos.txt`), one account per line:
   ```
   email@example.com:password123
   anotheruser@gmail.com:mypass456
   ```

2. Run the checker:
   ```
   python fortnitechecker.py
   ```

3. Follow the on-screen menu — enter your combo file name, set threads/delay, and optionally configure proxies and Telegram.

### 📦 Run as .EXE (Windows)

A pre-built Windows executable can be compiled with the included build script:

```
pip install pyinstaller
python build_exe.py
```

The `.exe` will be output to the `dist/` folder as `FortnitChecker.exe`. No Python installation needed to run it.

---

## 💳 Card Checker (`cardchecker.py`)

Checks credit/debit cards against the Stripe payment gateway.

### ✅ Features
- Luhn algorithm pre-validation
- Multi-threaded (up to 3 threads)
- Proxy support with auto-rotation
- Telegram notifications for approved cards
- Saves approved cards to a timestamped `.txt` file

### ⚙️ Requirements

```
pip install requests colorama fake-useragent brotli requests-toolbelt beautifulsoup4
```

### 🚀 How to Run

1. Create a card list (e.g. `cards.txt`), one card per line in `number|mm|yyyy|cvc` format:
   ```
   4111111111111111|01|2026|123
   ```

2. Run the checker:
   ```
   python cardchecker.py
   ```

---

## 📁 Output Files

| File | Contents |
|------|---------|
| `fortnite_valid_YYYYMMDD_HHMMSS.txt` | Valid Fortnite accounts |
| `approved_YYYYMMDD_HHMMSS.txt` | Approved cards |

---

## ⚠️ Disclaimer

This tool is for **educational purposes only**. Use responsibly and only on accounts you own or have explicit permission to test.
