"""
元大證券 API 客戶端
功能：僅實作「取得股票交易明細」部分

官方文件：https://developer.yuanta.com.tw  （需先申請 API 權限）
認證方式：帳號 + 密碼 → 取得 access_token，後續請求帶入 Authorization header

回傳欄位對應 finance_stocks 資料表：
  date, ticker, company_name, market, action, shares, price, amount, fee, tax
"""

import logging
import requests
from datetime import datetime, date
from typing import Optional

logger = logging.getLogger(__name__)


class YuantaAPIError(Exception):
    """元大 API 呼叫失敗"""


# ─────────────────────────────────────────────────────────
# 主設定（依照實際 API 文件調整）
# ─────────────────────────────────────────────────────────
class YuantaAPIClient:
    """
    元大證券 API 客戶端 — 僅「取得交易明細」部分

    使用方式：
        client = YuantaAPIClient(
            account='券商帳號',
            password='密碼',
            id_number='身分證字號',  # 部分 API 版本需要
        )
        client.login()
        trades = client.get_stock_transactions('2025-01-01', '2025-12-31')

    回傳範例：
        [
          {
            'date': '2025-03-15',
            'ticker': '2330',
            'company_name': '台積電',
            'market': 'TW',
            'action': 'buy',
            'shares': 1000,
            'price': 880.0,
            'amount': 880000.0,
            'fee': 1276.0,
            'tax': 0.0,
          },
          ...
        ]
    """

    # ── 基礎設定 ──────────────────────────────────────────
    # 元大證券 API 基礎 URL（依官方文件確認）
    BASE_URL = 'https://api.yuantaapi.com'

    # 端點路徑（依官方文件確認）
    ENDPOINTS = {
        # 登入：POST → 取得 access_token
        'login': '/api/auth/login',
        # 股票交易明細：GET → 回傳 list
        'stock_trades': '/api/stock/trade-history',
    }

    # 買賣別對照表（API 回傳值 → finance_stocks.action）
    # 依照實際 API 回傳的買賣別格式調整
    ACTION_MAP = {
        'B':  'buy',
        'S':  'sell',
        'BUY': 'buy',
        'SELL': 'sell',
        '買': 'buy',
        '賣': 'sell',
        '1':  'buy',
        '2':  'sell',
    }

    # 市場對照表（依 ticker 格式判斷）
    MARKET_MAP = {
        'TW': 'TW',   # 台股（4 碼數字）
        'US': 'US',   # 美股
        'HK': 'HK',   # 港股
    }

    # ── 初始化 ────────────────────────────────────────────
    def __init__(
        self,
        account: str,
        password: str,
        id_number: str = '',
        timeout: int = 30,
    ):
        self.account   = account
        self.password  = password
        self.id_number = id_number
        self.timeout   = timeout

        self._token: Optional[str] = None
        self._session = requests.Session()
        self._session.headers.update({
            'Content-Type': 'application/json',
            'Accept':       'application/json',
            'User-Agent':   'PersonalFinanceTracker/1.0',
        })

    # ── 屬性 ──────────────────────────────────────────────
    @property
    def is_logged_in(self) -> bool:
        return self._token is not None

    # ── 認證 ──────────────────────────────────────────────
    def login(self) -> None:
        """
        登入元大證券 API，取得 access_token 並存入 self._token。

        ⚠️  請依照官方 API 文件確認：
            - 請求格式（JSON / Form-data）
            - 必要欄位（是否需要 id_number、captcha 等）
            - 回傳 token 的欄位名稱（token / access_token / data.token 等）
        """
        url  = self.BASE_URL + self.ENDPOINTS['login']
        body = {
            'account':   self.account,
            'password':  self.password,
            'id_number': self.id_number,   # 若不需要可移除
        }
        try:
            resp = self._session.post(url, json=body, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()

            # ── 依 API 文件調整 token 取出方式 ──
            token = (
                data.get('token')
                or data.get('access_token')
                or (data.get('data') or {}).get('token')
            )
            if not token:
                raise YuantaAPIError(f'登入成功但回傳無 token，回應：{data}')

            self._token = token
            self._session.headers['Authorization'] = f'Bearer {token}'
            logger.info('[YuantaAPI] 登入成功')

        except requests.RequestException as e:
            raise YuantaAPIError(f'登入請求失敗：{e}') from e

    # ── 取得交易明細 ──────────────────────────────────────
    def get_stock_transactions(
        self,
        date_from: str,
        date_to:   str,
    ) -> list:
        """
        取得指定日期範圍的股票交易明細。

        Args:
            date_from: 起始日期，格式 YYYY-MM-DD
            date_to:   結束日期，格式 YYYY-MM-DD

        Returns:
            list[dict]，每筆已轉換為 finance_stocks 的欄位格式

        ⚠️  請依照官方 API 文件確認：
            - Query param 名稱（start_date / startDate / begin_date 等）
            - 是否需要帶帳號 param
            - 分頁機制（若有，需迴圈取完）
            - 回傳資料的陣列欄位名稱（data / result / trades 等）
        """
        if not self.is_logged_in:
            raise YuantaAPIError('尚未登入，請先呼叫 login()')

        url    = self.BASE_URL + self.ENDPOINTS['stock_trades']
        params = {
            'start_date': date_from,   # 依 API 文件調整 param 名稱
            'end_date':   date_to,
            'account':    self.account,
        }

        try:
            resp = self._session.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()

            # ── 依 API 文件調整陣列欄位 ──
            raw_list = (
                data.get('data')
                or data.get('result')
                or data.get('trades')
                or (data if isinstance(data, list) else [])
            )
            logger.info(f'[YuantaAPI] 取得 {len(raw_list)} 筆交易明細（{date_from} ~ {date_to}）')

        except requests.RequestException as e:
            raise YuantaAPIError(f'取得交易明細請求失敗：{e}') from e

        return [self._map_transaction(r) for r in raw_list]

    # ── 欄位對應（API → finance_stocks）───────────────────
    def _map_transaction(self, raw: dict) -> dict:
        """
        將 API 原始回傳的單筆資料，轉換為 finance_stocks 資料表的格式。

        ⚠️  依照官方 API 文件調整下方欄位名稱（raw.get('...')）。
            常見欄位名稱變體已列出，請移除不需要的備選項。
        """
        # ── 日期 ──────────────────────────────────────────
        trade_date_raw = (
            raw.get('trade_date')
            or raw.get('tradeDate')
            or raw.get('date')
            or raw.get('成交日期')
            or ''
        )
        trade_date = self._parse_date(trade_date_raw)

        # ── 股票代號 ──────────────────────────────────────
        ticker = (
            raw.get('ticker')
            or raw.get('stock_no')
            or raw.get('stockNo')
            or raw.get('stock_code')
            or raw.get('證券代號')
            or ''
        ).strip().upper()

        # ── 公司名稱 ──────────────────────────────────────
        company_name = (
            raw.get('company_name')
            or raw.get('stock_name')
            or raw.get('stockName')
            or raw.get('證券名稱')
            or ''
        )

        # ── 買賣別 ────────────────────────────────────────
        action_raw = str(
            raw.get('action')
            or raw.get('buy_sell')
            or raw.get('buySell')
            or raw.get('trade_type')
            or raw.get('買賣別')
            or ''
        ).strip()
        action = self.ACTION_MAP.get(action_raw, self.ACTION_MAP.get(action_raw.upper(), 'buy'))

        # ── 股數 ──────────────────────────────────────────
        shares = float(
            raw.get('shares')
            or raw.get('qty')
            or raw.get('quantity')
            or raw.get('成交股數')
            or 0
        )

        # ── 成交單價 ──────────────────────────────────────
        price = float(
            raw.get('price')
            or raw.get('trade_price')
            or raw.get('tradePrice')
            or raw.get('成交價')
            or 0
        )

        # ── 成交金額 ──────────────────────────────────────
        # 若 API 有直接提供金額則優先使用，否則由股數×單價計算
        amount_raw = (
            raw.get('amount')
            or raw.get('trade_amount')
            or raw.get('tradeAmount')
            or raw.get('成交金額')
        )
        amount = float(amount_raw) if amount_raw is not None else round(shares * price, 2)

        # ── 手續費 ────────────────────────────────────────
        fee = float(
            raw.get('fee')
            or raw.get('commission')
            or raw.get('手續費')
            or 0
        )

        # ── 交易稅 ────────────────────────────────────────
        tax = float(
            raw.get('tax')
            or raw.get('transaction_tax')
            or raw.get('transactionTax')
            or raw.get('交易稅')
            or raw.get('證交稅')
            or 0
        )

        # ── 市場 ──────────────────────────────────────────
        market = self._detect_market(ticker, raw)

        return {
            'date':         trade_date,
            'ticker':       ticker,
            'company_name': company_name,
            'market':       market,
            'action':       action,
            'shares':       shares,
            'price':        price,
            'amount':       amount,
            'fee':          fee,
            'tax':          tax,
            'note':         f'元大API匯入（原始：{action_raw}）',
        }

    # ── 工具方法 ──────────────────────────────────────────
    @staticmethod
    def _parse_date(raw: str) -> str:
        """
        嘗試將 API 回傳的日期字串統一為 YYYY-MM-DD 格式。
        支援：YYYY-MM-DD、YYYYMMDD、民國 NNN/MM/DD 等常見格式。
        """
        if not raw:
            return date.today().isoformat()

        raw = str(raw).strip()

        # 已是 ISO 格式
        if len(raw) == 10 and raw[4] == '-':
            return raw

        # YYYYMMDD
        if len(raw) == 8 and raw.isdigit():
            return f'{raw[:4]}-{raw[4:6]}-{raw[6:]}'

        # 民國年 NNN/MM/DD 或 NNN-MM-DD
        if '/' in raw or (raw[:3].isdigit() and len(raw) <= 9):
            parts = raw.replace('-', '/').split('/')
            if len(parts) == 3 and int(parts[0]) < 200:
                y = int(parts[0]) + 1911
                return f'{y}-{parts[1].zfill(2)}-{parts[2].zfill(2)}'

        # 嘗試 dateutil 解析
        try:
            from dateutil import parser as dp
            return dp.parse(raw).strftime('%Y-%m-%d')
        except Exception:
            pass

        logger.warning(f'[YuantaAPI] 無法解析日期格式：{raw}，使用今日')
        return date.today().isoformat()

    @staticmethod
    def _detect_market(ticker: str, raw: dict) -> str:
        """依股票代號格式或 API 欄位自動判斷市場"""
        # 若 API 有明確提供市場欄位
        market_raw = str(
            raw.get('market') or raw.get('exchange') or raw.get('市場') or ''
        ).upper()
        if market_raw in ('TW', 'TSE', 'OTC', 'TWSE'):
            return 'TW'
        if market_raw in ('US', 'NYSE', 'NASDAQ', 'AMEX'):
            return 'US'
        if market_raw in ('HK', 'HKEX'):
            return 'HK'

        # 依代號格式猜測
        if ticker.isdigit() and len(ticker) in (4, 5):
            return 'TW'   # 台股：4~5 碼純數字
        if ticker.isdigit() and len(ticker) == 5:
            return 'TW'
        if any(c.isalpha() for c in ticker):
            return 'US'   # 有英文字母視為美股

        return 'TW'   # 預設台股
