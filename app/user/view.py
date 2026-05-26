"""
使用者管理 Blueprint（管理者專用）
url_prefix: /user

端點：
  GET    /user/        — 列出所有使用者
  POST   /user/        — 新增使用者
  GET    /user/<id>    — 取得單一使用者
  PUT    /user/<id>    — 更新使用者
  DELETE /user/<id>    — 刪除使用者
  POST   /user/<id>/toggle-active — 切換啟用狀態
"""
import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from src.models.user import User, ROLES
from src.permissions import require_role, get_current_user_id

logger = logging.getLogger(__name__)
app_user = Blueprint('app_user', __name__)


def _safe(user: dict) -> dict:
    """移除密碼欄位"""
    if not user:
        return {}
    return {k: v for k, v in user.items() if k != 'password'}


@app_user.route('/', methods=['GET'])
@jwt_required()
@require_role('admin')
def list_users():
    """列出所有使用者（管理者專用）"""
    return jsonify({'success': True, 'data': User.find_all()})


@app_user.route('/<int:user_id>', methods=['GET'])
@jwt_required()
@require_role('admin')
def get_user(user_id):
    """取得單一使用者"""
    user = User.find_by_id(user_id)
    if not user:
        return jsonify({'success': False, 'message': '使用者不存在'}), 404
    return jsonify({'success': True, 'data': _safe(user)})


@app_user.route('/', methods=['POST'])
@jwt_required()
@require_role('admin')
def create_user():
    """新增使用者（管理者專用）"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '缺少請求參數'}), 400

    username     = data.get('username', '').strip()
    password     = data.get('password', '')
    role         = data.get('role', 'user')
    display_name = data.get('display_name', '')
    email        = data.get('email', '')

    if not username or not password:
        return jsonify({'success': False, 'message': 'username 或 password 不得為空'}), 400
    if len(password) < 6:
        return jsonify({'success': False, 'message': '密碼長度至少 6 個字元'}), 400
    if role not in ROLES:
        return jsonify({'success': False, 'message': f'無效角色，可用值：{", ".join(ROLES)}'}), 400
    if User.find_by_username(username):
        return jsonify({'success': False, 'message': '使用者帳號已存在'}), 409

    user_id = User.create(username, password, role=role,
                          display_name=display_name, email=email)

    # 為新使用者初始化預設財務分類
    try:
        from src.models.finance import Category
        Category.init_defaults_for_user(user_id)
    except Exception as e:
        logger.warning(f'[user] 初始化分類失敗（user_id={user_id}）：{e}')

    logger.info(f'[user] 新增使用者：{username} (id={user_id}, role={role})')
    return jsonify({'success': True, 'id': user_id}), 201


@app_user.route('/<int:user_id>', methods=['PUT'])
@jwt_required()
@require_role('admin')
def update_user(user_id):
    """更新使用者資訊（管理者專用）"""
    data = request.get_json() or {}

    password     = data.get('password') or None
    role         = data.get('role') or None
    display_name = data.get('display_name')  # allow empty string
    email        = data.get('email')
    is_active    = data.get('is_active')

    if role and role not in ROLES:
        return jsonify({'success': False, 'message': f'無效角色：{", ".join(ROLES)}'}), 400
    if password and len(password) < 6:
        return jsonify({'success': False, 'message': '密碼長度至少 6 個字元'}), 400

    if not User.update(user_id, password=password, role=role,
                       display_name=display_name, email=email, is_active=is_active):
        return jsonify({'success': False, 'message': '使用者不存在或無需更新'}), 404

    return jsonify({'success': True})


@app_user.route('/<int:user_id>', methods=['DELETE'])
@jwt_required()
@require_role('admin')
def delete_user(user_id):
    """刪除使用者（不可刪除自己）"""
    current_id = get_current_user_id()
    if current_id == user_id:
        return jsonify({'success': False, 'message': '無法刪除自己的帳號'}), 400

    if not User.delete(user_id):
        return jsonify({'success': False, 'message': '使用者不存在'}), 404

    logger.info(f'[user] 刪除使用者 id={user_id}（操作者 id={current_id}）')
    return jsonify({'success': True})


@app_user.route('/<int:user_id>/toggle-active', methods=['POST'])
@jwt_required()
@require_role('admin')
def toggle_active(user_id):
    """切換使用者啟用狀態（不可停用自己）"""
    current_id = get_current_user_id()
    if current_id == user_id:
        return jsonify({'success': False, 'message': '無法停用自己的帳號'}), 400

    user = User.find_by_id(user_id)
    if not user:
        return jsonify({'success': False, 'message': '使用者不存在'}), 404

    new_active = 0 if user.get('is_active', 1) else 1
    User.update(user_id, is_active=new_active)
    return jsonify({'success': True, 'is_active': new_active})
