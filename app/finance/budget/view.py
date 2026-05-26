"""
預算管理 Blueprint
url_prefix: /finance/budget
"""

from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from src.models.finance import Budget
from src.permissions import require_role, get_current_user_id

app_finance_budget = Blueprint('app_finance_budget', __name__)


def _serialize(rows) -> list:
    """將 datetime 物件轉為字串"""
    result = []
    for row in rows:
        r = dict(row)
        for k, v in r.items():
            if hasattr(v, 'isoformat'):
                r[k] = v.isoformat()
        result.append(r)
    return result


@app_finance_budget.route('/', methods=['GET'])
@jwt_required()
@require_role('admin', 'user')
def list_budgets():
    """查詢指定年月的預算清單"""
    now   = datetime.now()
    year  = int(request.args.get('year',  now.year))
    month = int(request.args.get('month', now.month))
    user_id = get_current_user_id()
    try:
        rows = Budget.find(year, month, user_id=user_id)
        return jsonify({'success': True, 'data': _serialize(rows)})
    except Exception as e:
        return jsonify({'success': False, 'message': f'查詢失敗：{e}'}), 500


@app_finance_budget.route('/', methods=['POST'])
@jwt_required()
@require_role('admin', 'user')
def set_budget():
    """設定預算（使用 UPSERT）"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '缺少請求參數'}), 400

    category_id = data.get('category_id')
    year        = data.get('year')
    month       = data.get('month')
    amount      = data.get('amount')

    if not all([category_id, year, month, amount is not None]):
        return jsonify({'success': False, 'message': 'category_id, year, month, amount 皆必填'}), 400

    user_id = get_current_user_id()
    try:
        Budget.upsert(int(category_id), int(year), int(month), float(amount), user_id=user_id)
        return jsonify({'success': True}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': f'設定失敗：{e}'}), 500


@app_finance_budget.route('/<int:id>', methods=['PUT'])
@jwt_required()
@require_role('admin', 'user')
def update_budget(id):
    """更新預算金額"""
    data = request.get_json()
    if not data or 'amount' not in data:
        return jsonify({'success': False, 'message': '缺少 amount 欄位'}), 400

    user_id = get_current_user_id()
    try:
        if not Budget.update(id, user_id, float(data['amount'])):
            return jsonify({'success': False, 'message': '預算記錄不存在'}), 404
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': f'更新失敗：{e}'}), 500


@app_finance_budget.route('/<int:id>', methods=['DELETE'])
@jwt_required()
@require_role('admin', 'user')
def delete_budget(id):
    """刪除預算"""
    user_id = get_current_user_id()
    try:
        if not Budget.delete(id, user_id):
            return jsonify({'success': False, 'message': '預算記錄不存在'}), 404
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': f'刪除失敗：{e}'}), 500


@app_finance_budget.route('/status', methods=['GET'])
@jwt_required()
@require_role('admin', 'user')
def budget_status():
    """預算執行狀況（各分類預算 vs 實際支出）"""
    now   = datetime.now()
    year  = int(request.args.get('year',  now.year))
    month = int(request.args.get('month', now.month))
    user_id = get_current_user_id()
    try:
        data = Budget.status(year, month, user_id=user_id)
        return jsonify({'success': True, 'data': data, 'year': year, 'month': month})
    except Exception as e:
        return jsonify({'success': False, 'message': f'查詢失敗：{e}'}), 500
