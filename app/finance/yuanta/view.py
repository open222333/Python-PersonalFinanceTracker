"""
元大證券 API 同步 Blueprint
url_prefix: /finance/yuanta

端點：
  POST /finance/yuanta/sync    — 從元大 API 取得交易明細並寫入 finance_stocks
  POST /finance/yuanta/preview — 預覽（只回傳資料，不寫入）
  GET  /finance/yuanta/config  — 檢查設定是否完整（不回傳密碼）
"""

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from src.permissions import require_role, get_current_user_id
from src.models.finance import Stock
from src.yuanta_api import YuantaAPIClient, YuantaAPIError
from src import (
    YUANTA_ACCOUNT,
    YUANTA_PASSWORD,
    YUANTA_ID_NUMBER,
    YUANTA_API_URL,
)

logger = logging.getLogger(__name__)
app_finance_yuanta = Blueprint('app_finance_yuanta', __name__)


def _make_client() -> YuantaAPIClient:
    """從設定建立 API 客戶端"""
    client = YuantaAPIClient(
        account=YUANTA_ACCOUNT,
        password=YUANTA_PASSWORD,
        id_number=YUANTA_ID_NUMBER,
    )
    if YUANTA_API_URL:
        client.BASE_URL = YUANTA_API_URL
    return client


# ─────────────────────────────────────────────────────────
# GET /finance/yuanta/config — 檢查設定完整性
# ─────────────────────────────────────────────────────────
@app_finance_yuanta.route('/config', methods=['GET'])
@jwt_required()
@require_role('admin', 'user')
def check_config():
    """回傳設定狀態（不回傳密碼明文）"""
    return jsonify({
        'success': True,
        'configured': bool(YUANTA_ACCOUNT and YUANTA_PASSWORD),
        'account':    YUANTA_ACCOUNT or '（未設定）',
        'api_url':    YUANTA_API_URL or '（使用預設）',
        'has_password':   bool(YUANTA_PASSWORD),
        'has_id_number':  bool(YUANTA_ID_NUMBER),
    })


# ─────────────────────────────────────────────────────────
# POST /finance/yuanta/preview — 預覽（不寫入 DB）
# ─────────────────────────────────────────────────────────
@app_finance_yuanta.route('/preview', methods=['POST'])
@jwt_required()
@require_role('admin', 'user')
def preview():
    """
    預覽元大 API 交易明細（不寫入資料庫）

    Request JSON：
        {
          "date_from": "2025-01-01",
          "date_to":   "2025-12-31",
          "account":   "可選：覆蓋設定檔帳號",
          "password":  "可選：覆蓋設定檔密碼"
        }

    Response：
        {
          "success": true,
          "count": 5,
          "data": [ {...}, ... ]
        }
    """
    user_id   = get_current_user_id()
    body      = request.get_json() or {}
    date_from = body.get('date_from', _default_month_start())
    date_to   = body.get('date_to',   _today())

    # 允許前端臨時帶入帳密（測試用）
    account  = body.get('account')  or YUANTA_ACCOUNT
    password = body.get('password') or YUANTA_PASSWORD

    if not account or not password:
        return jsonify({'success': False, 'message': '請在 config.ini [YUANTA] 設定帳號密碼'}), 400

    try:
        client = YuantaAPIClient(account=account, password=password, id_number=YUANTA_ID_NUMBER)
        if YUANTA_API_URL:
            client.BASE_URL = YUANTA_API_URL
        client.login()
        trades = client.get_stock_transactions(date_from, date_to)
        return jsonify({'success': True, 'count': len(trades), 'data': trades})

    except YuantaAPIError as e:
        logger.error(f'[Yuanta preview] {e}')
        return jsonify({'success': False, 'message': str(e)}), 502
    except Exception as e:
        logger.exception('[Yuanta preview] 未預期錯誤')
        return jsonify({'success': False, 'message': f'未預期錯誤：{e}'}), 500


# ─────────────────────────────────────────────────────────
# POST /finance/yuanta/sync — 同步並寫入 DB
# ─────────────────────────────────────────────────────────
@app_finance_yuanta.route('/sync', methods=['POST'])
@jwt_required()
@require_role('admin', 'user')
def sync():
    """
    從元大 API 取得交易明細並批次寫入 finance_stocks 資料表。

    Request JSON：
        {
          "date_from":   "2025-01-01",
          "date_to":     "2025-12-31",
          "skip_duplicate": true    （預設 true：相同日期+代號+股數+金額跳過不重複匯入）
        }

    Response：
        {
          "success": true,
          "fetched":   10,   ← 從 API 取得筆數
          "inserted":   8,   ← 實際寫入筆數
          "skipped":    2,   ← 跳過（重複）筆數
          "errors":     [],  ← 寫入失敗的明細
          "date_from": "2025-01-01",
          "date_to":   "2025-12-31"
        }
    """
    user_id        = get_current_user_id()
    body           = request.get_json() or {}
    date_from      = body.get('date_from', _default_month_start())
    date_to        = body.get('date_to',   _today())
    skip_duplicate = body.get('skip_duplicate', True)

    if not YUANTA_ACCOUNT or not YUANTA_PASSWORD:
        return jsonify({'success': False, 'message': '請在 config.ini [YUANTA] 設定帳號密碼'}), 400

    # ── Step 1: 登入並取得交易明細 ──
    try:
        client = _make_client()
        client.login()
        trades = client.get_stock_transactions(date_from, date_to)
    except YuantaAPIError as e:
        logger.error(f'[Yuanta sync] API 錯誤：{e}')
        return jsonify({'success': False, 'message': str(e)}), 502
    except Exception as e:
        logger.exception('[Yuanta sync] 取得資料時發生未預期錯誤')
        return jsonify({'success': False, 'message': f'未預期錯誤：{e}'}), 500

    # ── Step 2: 批次寫入 DB ──
    inserted, skipped, errors = 0, 0, []

    for t in trades:
        try:
            # 重複檢查：相同 date + ticker + action + shares + amount 視為重複
            if skip_duplicate and _is_duplicate(t, user_id):
                skipped += 1
                continue

            Stock.create(
                date=t['date'],
                ticker=t['ticker'],
                company_name=t.get('company_name', ''),
                market=t.get('market', 'TW'),
                action=t['action'],
                shares=t.get('shares', 0),
                price=t.get('price', 0),
                amount=t['amount'],
                fee=t.get('fee', 0),
                tax=t.get('tax', 0),
                note=t.get('note', '元大API匯入'),
                user_id=user_id,
            )
            inserted += 1

        except Exception as e:
            errors.append({'trade': t, 'error': str(e)})
            logger.error(f'[Yuanta sync] 寫入失敗：{e}，資料：{t}')

    logger.info(
        f'[Yuanta sync] 完成 {date_from}~{date_to}：'
        f'取得={len(trades)}，寫入={inserted}，跳過={skipped}，失敗={len(errors)}'
    )

    return jsonify({
        'success':   True,
        'fetched':   len(trades),
        'inserted':  inserted,
        'skipped':   skipped,
        'errors':    errors,
        'date_from': date_from,
        'date_to':   date_to,
    })


# ── 工具函式 ──────────────────────────────────────────────
def _today() -> str:
    return datetime.now().strftime('%Y-%m-%d')


def _default_month_start() -> str:
    n = datetime.now()
    return f'{n.year}-{n.month:02d}-01'


def _is_duplicate(trade: dict, user_id: int) -> bool:
    """
    查詢 finance_stocks 是否已存在相同的一筆記錄。
    判斷條件：user_id + date + ticker + action + shares + amount 完全一致。
    """
    from src.mysql import query
    rows = query(
        '''SELECT id FROM finance_stocks
           WHERE user_id=%s AND date=%s AND ticker=%s AND action=%s AND shares=%s AND amount=%s
           LIMIT 1''',
        (user_id, trade['date'], trade['ticker'], trade['action'],
         trade.get('shares', 0), trade['amount'])
    )
    return len(rows) > 0
