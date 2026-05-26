"""
報表分析 Blueprint
url_prefix: /finance/report

端點：
  GET  /finance/report/monthly           — 月報
  GET  /finance/report/yearly            — 年報
  GET  /finance/report/category          — 分類統計
  GET  /finance/report/dashboard         — 儀表板摘要
  GET  /finance/report/export            — 匯出（CSV / Excel）
  GET  /finance/report/import-template   — 下載匯入範本
  POST /finance/report/import            — 批次匯入（CSV / Excel）
"""

import io
import logging
from datetime import datetime, date
from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required
from src.models.finance import Report, Transaction, Stock, Category
from src.permissions import require_role, get_current_user_id

logger = logging.getLogger(__name__)

app_finance_report = Blueprint('app_finance_report', __name__)


def _serialize(obj):
    """遞迴序列化 date/datetime 物件"""
    if isinstance(obj, list):
        return [_serialize(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    return obj


@app_finance_report.route('/monthly', methods=['GET'])
@jwt_required()
@require_role('admin', 'user')
def monthly_report():
    """
    月報：當月總收入、支出、淨額、各分類明細
    QueryString: year, month
    """
    now   = datetime.now()
    year  = int(request.args.get('year',  now.year))
    month = int(request.args.get('month', now.month))
    user_id = get_current_user_id()
    try:
        data = Report.monthly(year, month, user_id=user_id)
        return jsonify({'success': True, 'data': _serialize(data)})
    except Exception as e:
        return jsonify({'success': False, 'message': f'查詢失敗：{e}'}), 500


@app_finance_report.route('/yearly', methods=['GET'])
@jwt_required()
@require_role('admin', 'user')
def yearly_report():
    """
    年報：12個月收支趨勢
    QueryString: year
    """
    year = int(request.args.get('year', datetime.now().year))
    user_id = get_current_user_id()
    try:
        data = Report.yearly(year, user_id=user_id)
        return jsonify({'success': True, 'data': _serialize(data), 'year': year})
    except Exception as e:
        return jsonify({'success': False, 'message': f'查詢失敗：{e}'}), 500


@app_finance_report.route('/category', methods=['GET'])
@jwt_required()
@require_role('admin', 'user')
def category_stats():
    """
    分類統計：指定期間各分類金額及佔比
    QueryString: date_from, date_to, type (income/expense)
    """
    now       = datetime.now()
    first_day = now.replace(day=1).strftime('%Y-%m-%d')
    date_from = request.args.get('date_from', first_day)
    date_to   = request.args.get('date_to',   now.strftime('%Y-%m-%d'))
    type_     = request.args.get('type', 'expense')

    if type_ not in ('income', 'expense'):
        return jsonify({'success': False, 'message': 'type 必須為 income 或 expense'}), 400

    user_id = get_current_user_id()
    try:
        data = Report.category_stats(date_from, date_to, type_, user_id=user_id)
        return jsonify({'success': True, 'data': _serialize(data)})
    except Exception as e:
        return jsonify({'success': False, 'message': f'查詢失敗：{e}'}), 500


@app_finance_report.route('/dashboard', methods=['GET'])
@jwt_required()
@require_role('admin', 'user')
def dashboard_summary():
    """
    儀表板摘要：本月收支、預算執行率、持股數、最近5筆交易
    QueryString: year, month
    """
    now   = datetime.now()
    year  = int(request.args.get('year',  now.year))
    month = int(request.args.get('month', now.month))
    user_id = get_current_user_id()
    try:
        data = Report.dashboard(year, month, user_id=user_id)
        return jsonify({'success': True, 'data': _serialize(data)})
    except Exception as e:
        return jsonify({'success': False, 'message': f'查詢失敗：{e}'}), 500


@app_finance_report.route('/export', methods=['GET'])
@jwt_required()
@require_role('admin', 'user')
def export_data():
    """
    匯出資料
    QueryString:
        type:      transactions / stocks
        date_from: 起始日期
        date_to:   結束日期
        format:    csv / excel
    """
    try:
        import pandas as pd
    except ImportError:
        return jsonify({'success': False, 'message': '請先安裝 pandas 套件'}), 500

    export_type = request.args.get('type', 'transactions')
    fmt         = request.args.get('format', 'csv')
    now         = datetime.now()
    first_day   = now.replace(day=1).strftime('%Y-%m-%d')
    date_from   = request.args.get('date_from', first_day)
    date_to     = request.args.get('date_to',   now.strftime('%Y-%m-%d'))

    user_id = get_current_user_id()
    # 取得資料
    if export_type == 'stocks':
        rows, _ = Stock.find(date_from=date_from, date_to=date_to, limit=10000, offset=0, user_id=user_id)
    else:
        rows, _ = Transaction.find(date_from=date_from, date_to=date_to, limit=10000, offset=0, user_id=user_id)

    # 序列化 date/datetime
    serialized = _serialize(rows)
    df = pd.DataFrame(serialized)

    buf = io.BytesIO()

    if fmt == 'excel':
        try:
            import openpyxl  # noqa: F401
        except ImportError:
            return jsonify({'success': False, 'message': '請先安裝 openpyxl 套件'}), 500

        with pd.ExcelWriter(buf, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
        buf.seek(0)
        filename = f'{export_type}_{date_from}_{date_to}.xlsx'
        mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    else:
        # 預設 CSV（UTF-8 BOM，Excel 可正確開啟）
        csv_str = df.to_csv(index=False)
        buf.write(('﻿' + csv_str).encode('utf-8'))
        buf.seek(0)
        filename = f'{export_type}_{date_from}_{date_to}.csv'
        mimetype = 'text/csv; charset=utf-8'

    return send_file(
        buf,
        mimetype=mimetype,
        as_attachment=True,
        download_name=filename,
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /finance/report/import-template — 下載匯入範本 CSV
# ─────────────────────────────────────────────────────────────────────────────

# 欄位定義
_TX_COLS  = ['date', 'type', 'amount', 'category_name', 'description', 'note']
_SK_COLS  = ['date', 'ticker', 'company_name', 'market', 'action',
             'shares', 'price', 'amount', 'fee', 'tax', 'note']

_TX_SAMPLE = [
    ['2025-01-15', 'expense', '150', '餐飲', '午餐', ''],
    ['2025-01-16', 'income',  '50000', '薪資', '月薪', ''],
]
_SK_SAMPLE = [
    ['2025-01-10', '2330', '台積電', 'TW', 'buy',  '1000', '650', '650000', '999', '0', ''],
    ['2025-01-20', '2330', '台積電', 'TW', 'sell', '500',  '700', '350000', '499', '525', ''],
]

@app_finance_report.route('/import-template', methods=['GET'])
@jwt_required()
@require_role('admin', 'user')
def import_template():
    """
    下載匯入範本 CSV
    QueryString: type = transactions（預設）/ stocks
    """
    import_type = request.args.get('type', 'transactions')
    if import_type == 'stocks':
        cols, sample = _SK_COLS, _SK_SAMPLE
        filename = 'import_stocks_template.csv'
    else:
        cols, sample = _TX_COLS, _TX_SAMPLE
        filename = 'import_transactions_template.csv'

    lines = [','.join(cols)] + [','.join(str(v) for v in row) for row in sample]
    content = '﻿' + '\n'.join(lines) + '\n'   # UTF-8 BOM for Excel

    buf = io.BytesIO(content.encode('utf-8'))
    return send_file(buf, mimetype='text/csv; charset=utf-8',
                     as_attachment=True, download_name=filename)


# ─────────────────────────────────────────────────────────────────────────────
# POST /finance/report/import — 批次匯入 CSV / Excel
# ─────────────────────────────────────────────────────────────────────────────
@app_finance_report.route('/import', methods=['POST'])
@jwt_required()
@require_role('admin', 'user')
def import_data():
    """
    批次匯入收支或股票記錄。

    Form-data：
        file            — CSV 或 .xlsx 檔案（必填）
        type            — transactions（預設）/ stocks
        skip_duplicate  — true（預設）/ false

    Response：
        {
          "success":  true,
          "fetched":  10,
          "inserted": 8,
          "skipped":  1,
          "errors":   [{"row": 3, "data": {...}, "message": "..."}]
        }
    """
    try:
        import pandas as pd
    except ImportError:
        return jsonify({'success': False, 'message': '請先安裝 pandas 套件'}), 500

    file = request.files.get('file')
    if not file or not file.filename:
        return jsonify({'success': False, 'message': '請上傳檔案'}), 400

    import_type     = request.form.get('type', 'transactions')
    skip_duplicate  = request.form.get('skip_duplicate', 'true').lower() != 'false'
    user_id         = get_current_user_id()

    # ── 讀取檔案 ──────────────────────────────────────────────
    fname = file.filename.lower()
    try:
        if fname.endswith('.xlsx') or fname.endswith('.xls'):
            try:
                import openpyxl  # noqa
            except ImportError:
                return jsonify({'success': False, 'message': '請先安裝 openpyxl 套件'}), 500
            df = pd.read_excel(file, dtype=str)
        else:
            raw = file.read()
            # 嘗試偵測 BOM 或 encoding
            for enc in ('utf-8-sig', 'utf-8', 'big5', 'gbk'):
                try:
                    df = pd.read_csv(io.BytesIO(raw), dtype=str, encoding=enc)
                    break
                except Exception:
                    continue
            else:
                return jsonify({'success': False, 'message': '無法解析 CSV 編碼，請使用 UTF-8 或 Big5'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'檔案讀取失敗：{e}'}), 400

    # 欄名統一小寫、去除空白
    df.columns = [c.strip().lower() for c in df.columns]
    df = df.where(pd.notnull(df), '')   # NaN → ''
    rows = df.to_dict('records')

    if not rows:
        return jsonify({'success': False, 'message': '檔案內容為空'}), 400

    # ── 分類名稱快取（transactions 專用）─────────────────────
    _cat_cache: dict = {}
    def _cat_id(name: str) -> int | None:
        if not name:
            return None
        if name in _cat_cache:
            return _cat_cache[name]
        cats = Category.find_all(user_id=user_id)
        for c in cats:
            _cat_cache[c['name']] = c['id']
        return _cat_cache.get(name)

    # ── 重複檢查 ──────────────────────────────────────────────
    from src.mysql import query as db_query

    def _is_tx_dup(r: dict) -> bool:
        rows_ = db_query(
            '''SELECT id FROM finance_transactions
               WHERE user_id=%s AND date=%s AND type=%s AND amount=%s
               LIMIT 1''',
            (user_id, r['date'], r['type'], float(r.get('amount', 0)))
        )
        return len(rows_) > 0

    def _is_sk_dup(r: dict) -> bool:
        rows_ = db_query(
            '''SELECT id FROM finance_stocks
               WHERE user_id=%s AND date=%s AND ticker=%s AND action=%s AND shares=%s AND amount=%s
               LIMIT 1''',
            (user_id, r['date'], r['ticker'].upper(),
             r['action'], float(r.get('shares', 0)), float(r.get('amount', 0)))
        )
        return len(rows_) > 0

    # ── 逐列處理 ─────────────────────────────────────────────
    inserted, skipped, errors = 0, 0, []

    for i, raw in enumerate(rows, start=2):   # row 1 = header
        try:
            if import_type == 'stocks':
                # ── 股票欄位驗證 ──
                date_   = str(raw.get('date', '')).strip()
                ticker  = str(raw.get('ticker', '')).strip().upper()
                if not date_ or not ticker:
                    errors.append({'row': i, 'data': raw, 'message': 'date / ticker 不得為空'})
                    continue

                action  = str(raw.get('action', 'buy')).strip().lower()
                # 中文別名
                if action in ('買入', '買'):
                    action = 'buy'
                elif action in ('賣出', '賣'):
                    action = 'sell'
                if action not in ('buy', 'sell', 'dividend'):
                    errors.append({'row': i, 'data': raw, 'message': f'action 值無效：{action}'})
                    continue

                record = {
                    'date':         date_,
                    'ticker':       ticker,
                    'company_name': str(raw.get('company_name', '')).strip(),
                    'market':       str(raw.get('market', 'TW')).strip().upper() or 'TW',
                    'action':       action,
                    'shares':       float(raw.get('shares', 0) or 0),
                    'price':        float(raw.get('price',  0) or 0),
                    'amount':       float(raw.get('amount', 0) or 0),
                    'fee':          float(raw.get('fee',    0) or 0),
                    'tax':          float(raw.get('tax',    0) or 0),
                    'note':         str(raw.get('note', '')).strip(),
                }

                if skip_duplicate and _is_sk_dup(record):
                    skipped += 1
                    continue

                Stock.create(**record, user_id=user_id)
                inserted += 1

            else:
                # ── 收支欄位驗證 ──
                date_  = str(raw.get('date', '')).strip()
                type_  = str(raw.get('type', '')).strip().lower()
                amount = raw.get('amount', '')

                if not date_:
                    errors.append({'row': i, 'data': raw, 'message': 'date 不得為空'})
                    continue

                # 中文別名
                if type_ in ('支出', 'expense'):
                    type_ = 'expense'
                elif type_ in ('收入', 'income'):
                    type_ = 'income'
                else:
                    errors.append({'row': i, 'data': raw, 'message': f'type 值無效（需為 income/expense）：{type_}'})
                    continue

                try:
                    amount = float(amount)
                except (ValueError, TypeError):
                    errors.append({'row': i, 'data': raw, 'message': f'amount 非數字：{amount}'})
                    continue

                cat_name = str(raw.get('category_name', '')).strip()
                cat_id   = _cat_id(cat_name) if cat_name else None

                record = {
                    'date':        date_,
                    'type_':       type_,
                    'amount':      amount,
                    'category_id': cat_id,
                    'description': str(raw.get('description', '')).strip(),
                    'note':        str(raw.get('note', '')).strip(),
                }

                if skip_duplicate and _is_tx_dup({'date': date_, 'type': type_, 'amount': amount}):
                    skipped += 1
                    continue

                Transaction.create(**record, user_id=user_id)
                inserted += 1

        except Exception as e:
            errors.append({'row': i, 'data': raw, 'message': str(e)})
            logger.error(f'[import] row {i} 寫入失敗：{e}')

    logger.info(f'[import] type={import_type} 取得={len(rows)} 寫入={inserted} 跳過={skipped} 失敗={len(errors)}')
    return jsonify({
        'success':  True,
        'fetched':  len(rows),
        'inserted': inserted,
        'skipped':  skipped,
        'errors':   errors,
    })
