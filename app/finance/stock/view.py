"""
股票交易管理 Blueprint
url_prefix: /finance/stock
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from src.models.finance import Stock
from src.permissions import require_role, get_current_user_id

app_finance_stock = Blueprint('app_finance_stock', __name__)


def _serialize_rows(rows: list) -> list:
    """將查詢結果中的 date / datetime 轉為字串"""
    result = []
    for row in rows:
        r = dict(row)
        for k, v in r.items():
            if hasattr(v, 'isoformat'):
                r[k] = v.isoformat()
            elif not isinstance(v, (int, float, str, bool, type(None))):
                r[k] = str(v)
        result.append(r)
    return result


@app_finance_stock.route('/', methods=['GET'])
@jwt_required()
@require_role('admin', 'user')
def list_stocks():
    """查詢股票交易記錄（支援 limit/offset 及 page/per_page）"""
    date_from = request.args.get('date_from')
    date_to   = request.args.get('date_to')
    ticker    = request.args.get('ticker')
    action    = request.args.get('action')
    if 'limit' in request.args:
        limit  = max(1, min(200, int(request.args.get('limit',  20))))
        offset = max(0, int(request.args.get('offset', 0)))
    else:
        page    = max(1, int(request.args.get('page',     1)))
        limit   = max(1, min(200, int(request.args.get('per_page', 20))))
        offset  = (page - 1) * limit

    user_id = get_current_user_id()
    try:
        rows, total = Stock.find(
            date_from=date_from,
            date_to=date_to,
            ticker=ticker,
            action=action,
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


@app_finance_stock.route('/<int:id>', methods=['GET'])
@jwt_required()
@require_role('admin', 'user')
def get_stock(id):
    """查詢單筆股票交易記錄"""
    user_id = get_current_user_id()
    try:
        row = Stock.find_by_id(id, user_id)
        if not row:
            return jsonify({'success': False, 'message': '記錄不存在'}), 404
        return jsonify({'success': True, 'data': _serialize_rows([row])[0]})
    except Exception as e:
        return jsonify({'success': False, 'message': f'查詢失敗：{e}'}), 500


@app_finance_stock.route('/', methods=['POST'])
@jwt_required()
@require_role('admin', 'user')
def create_stock():
    """新增股票交易記錄"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '缺少請求參數'}), 400

    date         = data.get('date', '').strip()
    ticker       = data.get('ticker', '').strip()
    company_name = data.get('company_name', '')
    market       = data.get('market', 'TW')
    action       = data.get('action', '')
    shares       = data.get('shares', 0)
    price        = data.get('price', 0)
    amount       = data.get('amount')
    fee          = data.get('fee', 0)
    tax          = data.get('tax', 0)
    note         = data.get('note', '')

    if not date:
        return jsonify({'success': False, 'message': 'date 不得為空'}), 400
    if not ticker:
        return jsonify({'success': False, 'message': 'ticker 不得為空'}), 400
    if action not in ('buy', 'sell', 'dividend'):
        return jsonify({'success': False, 'message': 'action 必須為 buy/sell/dividend'}), 400
    if amount is None:
        return jsonify({'success': False, 'message': 'amount 不得為空'}), 400

    user_id = get_current_user_id()
    try:
        new_id = Stock.create(
            date=date, ticker=ticker, company_name=company_name,
            market=market, action=action, shares=float(shares),
            price=float(price), amount=float(amount),
            fee=float(fee), tax=float(tax), note=note,
            user_id=user_id,
        )
        return jsonify({'success': True, 'id': new_id}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': f'新增失敗：{e}'}), 500


@app_finance_stock.route('/<int:id>', methods=['PUT'])
@jwt_required()
@require_role('admin', 'user')
def update_stock(id):
    """更新股票交易記錄"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '缺少請求參數'}), 400

    allowed = {'date', 'ticker', 'company_name', 'market', 'action',
               'shares', 'price', 'amount', 'fee', 'tax', 'note'}
    kwargs = {k: v for k, v in data.items() if k in allowed}

    user_id = get_current_user_id()
    try:
        if not Stock.update(id, user_id, **kwargs):
            return jsonify({'success': False, 'message': '記錄不存在或無變更'}), 404
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': f'更新失敗：{e}'}), 500


@app_finance_stock.route('/<int:id>', methods=['DELETE'])
@jwt_required()
@require_role('admin', 'user')
def delete_stock(id):
    """刪除股票交易記錄"""
    user_id = get_current_user_id()
    try:
        if not Stock.delete(id, user_id):
            return jsonify({'success': False, 'message': '記錄不存在'}), 404
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': f'刪除失敗：{e}'}), 500


@app_finance_stock.route('/portfolio', methods=['GET'])
@jwt_required()
@require_role('admin', 'user')
def portfolio():
    """持倉彙總（各 ticker 持有股數、平均成本、總成本）"""
    user_id = get_current_user_id()
    try:
        data = Stock.portfolio(user_id)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'message': f'查詢失敗：{e}'}), 500


@app_finance_stock.route('/pnl', methods=['GET'])
@jwt_required()
@require_role('admin', 'user')
def pnl():
    """損益彙總（各 ticker 已實現損益）"""
    user_id = get_current_user_id()
    try:
        data = Stock.pnl(user_id)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'message': f'查詢失敗：{e}'}), 500


@app_finance_stock.route('/dividend', methods=['GET'])
@jwt_required()
@require_role('admin', 'user')
def dividend():
    """股利彙總（各 ticker 累計股利）"""
    user_id = get_current_user_id()
    try:
        rows = Stock.dividend_summary(user_id)
        data = []
        for r in rows:
            row = dict(r)
            for k, v in row.items():
                if hasattr(v, 'isoformat'):
                    row[k] = v.isoformat()
            data.append(row)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'message': f'查詢失敗：{e}'}), 500
