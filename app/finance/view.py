"""
財務分類管理 Blueprint
url_prefix: /finance/category
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from src.models.finance import Category
from src.permissions import require_role

app_finance_category = Blueprint('app_finance_category', __name__)


@app_finance_category.route('/', methods=['GET'])
@jwt_required()
@require_role('admin', 'operator')
def list_categories():
    """查詢分類清單（可依 type 篩選）"""
    type_filter = request.args.get('type')
    try:
        data = Category.find_all(type_filter)
        # 將 datetime 物件轉為字串
        for row in data:
            if row.get('created_at'):
                row['created_at'] = str(row['created_at'])
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'message': f'查詢失敗：{e}'}), 500


@app_finance_category.route('/', methods=['POST'])
@jwt_required()
@require_role('admin', 'operator')
def create_category():
    """新增分類"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '缺少請求參數'}), 400

    name  = data.get('name', '').strip()
    type_ = data.get('type', '')
    color = data.get('color', '#808080')
    icon  = data.get('icon', 'bi-tag')

    if not name:
        return jsonify({'success': False, 'message': '分類名稱不得為空'}), 400
    if type_ not in ('income', 'expense'):
        return jsonify({'success': False, 'message': 'type 必須為 income 或 expense'}), 400

    try:
        new_id = Category.create(name, type_, color, icon)
        return jsonify({'success': True, 'id': new_id}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': f'新增失敗：{e}'}), 500


@app_finance_category.route('/<int:id>', methods=['PUT'])
@jwt_required()
@require_role('admin', 'operator')
def update_category(id):
    """更新分類"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '缺少請求參數'}), 400

    name  = data.get('name')
    color = data.get('color')
    icon  = data.get('icon')

    try:
        if not Category.update(id, name=name, color=color, icon=icon):
            return jsonify({'success': False, 'message': '分類不存在或無變更'}), 404
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': f'更新失敗：{e}'}), 500


@app_finance_category.route('/<int:id>', methods=['DELETE'])
@jwt_required()
@require_role('admin', 'operator')
def delete_category(id):
    """刪除分類"""
    try:
        if not Category.delete(id):
            return jsonify({'success': False, 'message': '分類不存在'}), 404
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': f'刪除失敗：{e}'}), 500
