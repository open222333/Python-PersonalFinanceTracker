"""
報表分析 Blueprint
url_prefix: /finance/report
"""

import io
from datetime import datetime, date
from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required
from src.models.finance import Report, Transaction, Stock
from src.permissions import require_role

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
@require_role('admin', 'operator')
def monthly_report():
    """
    月報：當月總收入、支出、淨額、各分類明細
    QueryString: year, month
    """
    now   = datetime.now()
    year  = int(request.args.get('year',  now.year))
    month = int(request.args.get('month', now.month))
    try:
        data = Report.monthly(year, month)
        return jsonify({'success': True, 'data': _serialize(data)})
    except Exception as e:
        return jsonify({'success': False, 'message': f'查詢失敗：{e}'}), 500


@app_finance_report.route('/yearly', methods=['GET'])
@jwt_required()
@require_role('admin', 'operator')
def yearly_report():
    """
    年報：12個月收支趨勢
    QueryString: year
    """
    year = int(request.args.get('year', datetime.now().year))
    try:
        data = Report.yearly(year)
        return jsonify({'success': True, 'data': _serialize(data), 'year': year})
    except Exception as e:
        return jsonify({'success': False, 'message': f'查詢失敗：{e}'}), 500


@app_finance_report.route('/category', methods=['GET'])
@jwt_required()
@require_role('admin', 'operator')
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

    try:
        data = Report.category_stats(date_from, date_to, type_)
        return jsonify({'success': True, 'data': _serialize(data)})
    except Exception as e:
        return jsonify({'success': False, 'message': f'查詢失敗：{e}'}), 500


@app_finance_report.route('/dashboard', methods=['GET'])
@jwt_required()
@require_role('admin', 'operator')
def dashboard_summary():
    """
    儀表板摘要：本月收支、預算執行率、持股數、最近5筆交易
    QueryString: year, month
    """
    now   = datetime.now()
    year  = int(request.args.get('year',  now.year))
    month = int(request.args.get('month', now.month))
    try:
        data = Report.dashboard(year, month)
        return jsonify({'success': True, 'data': _serialize(data)})
    except Exception as e:
        return jsonify({'success': False, 'message': f'查詢失敗：{e}'}), 500


@app_finance_report.route('/export', methods=['GET'])
@jwt_required()
@require_role('admin', 'operator')
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

    # 取得資料
    if export_type == 'stocks':
        rows, _ = Stock.find(date_from=date_from, date_to=date_to, limit=10000, offset=0)
    else:
        rows, _ = Transaction.find(date_from=date_from, date_to=date_to, limit=10000, offset=0)

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
