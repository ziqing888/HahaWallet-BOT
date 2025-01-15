import json
import os
import time
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from fake_useragent import UserAgent
import pytz
import random
import pyfiglet
from logging.handlers import RotatingFileHandler
from requests.exceptions import RequestException

# 配置日志格式器
class BeijingFormatter(logging.Formatter):
    """自定义日志格式器，将时间转换为北京时间。"""

    def __init__(self, fmt=None, datefmt=None, style='%', timezone=pytz.timezone('Asia/Shanghai')):
        super().__init__(fmt, datefmt, style)
        self.timezone = timezone

    def formatTime(self, record, datefmt=None):
        dt = datetime.utcfromtimestamp(record.created).replace(tzinfo=pytz.utc).astimezone(self.timezone)
        if datefmt:
            return dt.strftime(datefmt)
        else:
            return dt.strftime('%Y-%m-%d %H:%M:%S')

# 配置日志器
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 创建 RotatingFileHandler
file_handler = RotatingFileHandler('app.log', maxBytes=5*1024*1024, backupCount=5, encoding='utf-8')
file_handler.setFormatter(BeijingFormatter(fmt='%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))

# 创建 StreamHandler（控制台输出）
console_handler = logging.StreamHandler()
console_handler.setFormatter(BeijingFormatter(fmt='%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))

# 添加处理器到日志器
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# 设置时区为北京时间
BEIJING = pytz.timezone('Asia/Shanghai')

# 配置常量
CONFIG = {
    "LOGIN_URL": "https://prod.haha.me/users/login",
    "GRAPHQL_URL": "https://prod.haha.me/wallet-api/graphql",
    "ACCOUNTS_FILE": "accounts.json",
    "ORIGIN": "chrome-extension://andhndehpcjpmneneealacgnmealilal",
    "TIMEOUT": 30,
    "RETRIES": 3,
    "RETRY_DELAY": 2,
    "WAIT_TIME": 86400,  # 24小时
    "FALLBACK_USER_AGENT": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/115.0.0.0 Safari/537.36"
    ),
    "TIMEZONE": "Asia/Shanghai",  # 设置为北京时间
}

def load_accounts(file_path):
    """加载账户信息"""
    if not os.path.exists(file_path):
        logger.error(f"未找到文件 '{file_path}'。")
        return []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            accounts = json.load(f)
            if isinstance(accounts, list):
                logger.info(f"成功加载 {len(accounts)} 个账户。")
                return accounts
            logger.error(f"文件 '{file_path}' 格式无效。")
            return []
    except json.JSONDecodeError:
        logger.error(f"解析 '{file_path}' 失败，请确保 JSON 格式正确。")
        return []
    except Exception as e:
        logger.error(f"加载账户时出错: {e}")
        return []

def mask_email(email):
    """隐藏邮箱中间部分"""
    try:
        local, domain = email.split('@', 1)
        if len(local) <= 6:
            masked = f"{local[:3]}***{local[-3:]}@{domain}"
        else:
            masked = f"{local[:3]}***@{domain}"
        return masked
    except ValueError:
        return email

def get_user_agent():
    """获取随机用户代理"""
    try:
        ua = UserAgent()
        return ua.random
    except Exception:
        return CONFIG["FALLBACK_USER_AGENT"]

def retry(max_retries, delay):
    """重试装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except RequestException as e:
                    logger.warning(f"{func.__name__} 第 {attempt} 次尝试失败: {e}")
                    if attempt < max_retries:
                        time.sleep(delay)
            logger.error(f"{func.__name__} 达到最大重试次数。")
            return None
        return wrapper
    return decorator

class HahaWalletClient:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.token = None
        self.session = requests.Session()
        self.session.headers.update(self._prepare_headers())

    def __del__(self):
        self.session.close()

    def _prepare_headers(self):
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Content-Type": "application/json",
            "Origin": CONFIG["ORIGIN"],
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "none",
            "User-Agent": get_user_agent(),
            "X-Request-Source-Extra": "chrome",
        }
        return headers

    @retry(CONFIG["RETRIES"], CONFIG["RETRY_DELAY"])
    def login(self):
        """用户登录，获取 token"""
        payload = {"email": self.email, "password": self.password}
        response = self.session.post(CONFIG["LOGIN_URL"], json=payload, timeout=CONFIG["TIMEOUT"])
        response.raise_for_status()
        data = response.json()
        token = data.get('id_token')
        if token:
            self.token = token
            logger.info(f"[{mask_email(self.email)}] 登录成功。")
            return token
        else:
            logger.error(f"[{mask_email(self.email)}] 登录成功但未找到 'id_token'。")
            return None

    @retry(CONFIG["RETRIES"], CONFIG["RETRY_DELAY"])
    def graphql_request(self, query, variables=None):
        """发送 GraphQL 请求"""
        if not self.token:
            raise Exception("未登录，无法发送请求。")
        payload = {
            "operationName": None,
            "query": query,
            "variables": variables or {}
        }
        headers = self.session.headers.copy()
        headers["Authorization"] = self.token
        response = self.session.post(CONFIG["GRAPHQL_URL"], json=payload, headers=headers, timeout=CONFIG["TIMEOUT"])
        response.raise_for_status()
        return response.json().get('data', {})

    def get_user_info(self):
        """获取用户信息"""
        query = """
        {
          getRankInfo {
            rank
            karma
            karmaToNextRank
            rankName
            rankImage
            __typename
          }
        }
        """
        data = self.graphql_request(query)
        if data:
            karma = data.get('getRankInfo', {}).get('karma', 'N/A')
            logger.info(f"[{mask_email(self.email)}] 当前 Karma: {karma}")
            return karma
        logger.error(f"[{mask_email(self.email)}] 获取用户信息失败。")
        return 'N/A'

    def get_user_balance(self):
        """获取用户余额"""
        query = """
        {
          getKarmaPoints
        }
        """
        data = self.graphql_request(query)
        if data:
            points = data.get('getKarmaPoints', 'N/A')
            logger.info(f"[{mask_email(self.email)}] 当前余额: {points} Karma")
            return points
        logger.error(f"[{mask_email(self.email)}] 获取用户余额失败。")
        return 'N/A'

    def check_daily_checkin(self):
        """检查每日签到状态"""
        query = """
        query ($timezone: String) {
          getDailyCheckIn(timezone: $timezone)
        }
        """
        variables = {"timezone": CONFIG["TIMEZONE"]}
        data = self.graphql_request(query, variables)
        if data:
            can_claim = data.get('getDailyCheckIn', False)
            status = "可领取" if can_claim else "已领取"
            logger.info(f"[{mask_email(self.email)}] 每日签到状态: {status}")
            return can_claim
        logger.error(f"[{mask_email(self.email)}] 检查每日签到状态失败。")
        return False

    def claim_daily_checkin(self):
        """领取每日签到奖励"""
        mutation = """
        mutation ($timezone: String) {
          setDailyCheckIn(timezone: $timezone)
        }
        """
        variables = {"timezone": CONFIG["TIMEZONE"]}
        data = self.graphql_request(mutation, variables)
        if data:
            success = data.get('setDailyCheckIn', False)
            if success:
                logger.info(f"[{mask_email(self.email)}] 每日签到奖励已领取。")
                return True
        logger.error(f"[{mask_email(self.email)}] 领取每日签到奖励失败。")
        return False

def clear_terminal():
    """清空终端"""
    os.system('cls' if os.name == 'nt' else 'clear')

def display_welcome():
    """显示 ASCII 艺术横幅"""
    ascii_banner = pyfiglet.figlet_format("Haha Wallet", font="slant")
    print(ascii_banner)
    print("自动领取 Karma ")
    print("加入电报：https://t.me/ksqxszq")

def format_time(seconds):
    """格式化秒数为时:分:秒"""
    hrs, rem = divmod(seconds, 3600)
    mins, secs = divmod(rem, 60)
    return f"{int(hrs):02}:{int(mins):02}:{int(secs):02}"

def main():
    accounts = load_accounts(CONFIG["ACCOUNTS_FILE"])
    if not accounts:
        return

    clear_terminal()
    display_welcome()
    logger.info(f"账户总数: {len(accounts)}")
    logger.info("-" * 60)

    with ThreadPoolExecutor(max_workers=5) as executor:
        while True:
            future_to_account = {}
            for account in accounts:
                email = account.get("Email")
                password = account.get("Password")
                if email and password:
                    client = HahaWalletClient(email, password)
                    future = executor.submit(process_account, client)
                    future_to_account[future] = email

            for future in as_completed(future_to_account):
                email = future_to_account[future]
                try:
                    future.result()
                except Exception as exc:
                    logger.error(f"[{mask_email(email)}] 生成异常: {exc}")

            logger.info("-" * 60)
            logger.info("等待下一轮签到循环...")
            countdown(CONFIG["WAIT_TIME"])

def process_account(client):
    """处理单个账户的操作"""
    if client.login():
        client.get_user_info()
        can_claim = client.check_daily_checkin()
        if can_claim:
            if client.claim_daily_checkin():
                client.get_user_balance()
        else:
            logger.info(f"[{mask_email(client.email)}] 今日已签到，无需重复领取。")

def countdown(seconds):
    """倒计时等待，使用 print 显示倒计时"""
    try:
        while seconds > 0:
            formatted = format_time(seconds)
            print(f"等待 {formatted} ...", end='\r', flush=True)
            time.sleep(1)
            seconds -= 1
        print()  # 换行
        logger.info("开始下一轮签到循环。")
    except KeyboardInterrupt:
        print()  # 确保在中断时换行
        logger.info("程序已手动终止。")
        exit()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("程序已手动终止。")
