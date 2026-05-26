"""
收支記錄管理 Blueprint
url_prefix: /finance/transaction
"""

from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from src.models.finance import Transaction
from src.permissions import require_role, get_current_user_id

app_finance_transaction = Blueprint('app_finance_transaction', __name__)


def _serialize_rows(rows: list) -> list:
    """將查詢結果中的 date / datetime 轉為字串"""
    result = []
    for row in rows:
        r = dict(row)
        for k, v in r.items():
            if hasattr(v, 'isoformat'):
                r[k] = v.isoformat()
            elif hasattr(v, '__str__') and not isinstance(v, (int, float, str, bool, type(None))):
                r[k] = str(v)
        result.append(r)
    return result


@app_finance_transaction.route('/', methods=['GET'])
@jwt_required()
@require_role('admin', 'user')
def list_transactions():
    """
    查詢收支記錄
    QueryString: date_from, date_to, type, category_id, keyword, limit, offset
                 （也接受 page + per_page 舊格式）
    """
    date_from   = request.args.get('date_from')
    date_to     = request.args.get('date_to')
    type_       = request.args.get('type')
    category_id = request.args.get('category_id')
    keyword     = request.args.get('keyword')
    # 支援 limit/offset 和 page/per_page 兩種格式
    if 'limit' in request.args:
        limit  = max(1, min(200, int(request.args.get('limit',  20))))
        offset = max(0, int(request.args.get('offset', 0)))
    else:
        page     = max(1, int(request.args.get('page',     1)))
        limit    = max(1, min(200, int(request.args.get('per_page', 20))))
        offset   = (page - 1) * limit

    user_id = get_current_user_id()
    try:
        rows, total = Transaction.find(
            date_from=date_from,
            date_to=date_to,
            type_=type_,
            category_id=int(category_id) if category_id else None,
            keyword=keyword,
            limit=limit,
            offset=offset,
            user_id=user_id,
        )
        return jsonify({
            'success':  True,
            'data':     _serialize_rows(rows),
            'total':    total,
            'page':     (offset // limit) + 1 if limit else 1,
            'per_page': limit,
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'查詢失敗：{e}'}), 500


@app_finance_transaction.route('/<int:id>', methods=['GET'])
@jwt_required()
@require_role('admin', 'user')
def get_transaction(id):
    """查詢單筆收支記錄"""
    user_id = get_current_user_id()
    try:
        row = Transaction.find_by_id(id, user_id)
        if not row:
            return jsonify({'success': False, 'message': '記錄不存在'}), 404
        return jsonify({'success': True, 'data': _serialize_rows([row])[0]})
    except Exception as e:
        return jsonify({'success': False, 'message': f'查詢失敗：{e}'}), 500


@app_finance_transaction.route('/', methods=['POST'])
@jwt_required()
@require_role('admin', 'user')
def create_transaction():
    """新增收支記錄"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '缺少請求參數'}), 400

    date        = data.get('date', '').strip()
    type_       = data.get('type', '')
    amount      = data.get('amount')
    category_id = data.get('category_id')
    description = data.get('description', '')
    note        = data.get('note', '')

    if not date:
        return jsonify({'success': False, 'message': 'date 不得為空'}), 400
    if type_ not in ('income', 'expense'):
        return jsonify({'success': False, 'message': 'type 必須為 income 或 expense'}), 400
    if amount is None:
        return jsonify({'success': False, 'message': 'amount 不得為空'}), 400

    user_id = get_current_user_id()
    try:
        new_id = Transaction.create(
            date=date,
            type_=type_,
            amount=float(amount),
            category_id=int(category_id) if category_id else None,
            description=description,
            note=note,
            user_id=user_id,
        )
        return jsonify({'success': True, 'id': new_id}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': f'新增失敗：{e}'}), 500


@app_finance_transaction.route('/<int:id>', methods=['PUT'])
@jwt_required()
@require_role('admin', 'user')
def update_transaction(id):
    """更新收支記錄"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '缺少請求參數'}), 400

    kwargs = {}
    if 'date'        in data: kwargs['date']        = data['date']
    if 'type'        in data: kwargs['type']        = data['type']
    if 'amount'      in data: kwargs['amount']      = float(data['amount'])
    if 'category_id' in data: kwargs['category_id'] = data['category_id']
    if 'description' in data: kwargs['description'] = data['description']
    if 'note'        in data: kwargs['note']        = data['note']

    user_id = get_current_user_id()
    try:
        if not Transaction.update(id, user_id, **kwargs):
            return jsonify({'success': False, 'message': '記錄不存在或無變更'}), 404
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': f'更新失敗：{e}'}), 500


@app_finance_transaction.route('/<int:id>', methods=['DELETE'])
@jwt_required()
@require_role('admin', 'user')
def delete_transaction(id):
    """刪除收支記錄"""
    user_id = get_current_user_id()
    try:
        if not Transaction.delete(id, user_id):
            return jsonify({'success': False, 'message': '記錄不存在'}), 404
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': f'刪除失敗：{e}'}), 500


@app_finance_transaction.route('/summary', methods=['GET'])
@jwt_required()
@require_role('admin', 'user')
def monthly_summary():
    """當月收支概況"""
    now   = datetime.now()
    year  = int(request.args.get('year',  now.year))
    month = int(request.args.get('month', now.month))
    try:
        data = Transaction.monthly_summary(year, month)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'message': f'查詢失敗：{e}'}), 500
