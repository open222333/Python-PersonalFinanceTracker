"""
權限控制
從 JWT claims 直接讀取 role，避免每次請求都查詢資料庫
"""
from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt, get_jwt_identity

ROLES = ['admin', 'user']


def require_role(*roles):
    """限制只有指定角色可以存取"""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            claims = get_jwt()
            if claims.get('role') not in roles:
                return jsonify({'success': False, 'message': '權限不足'}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def get_current_user_id() -> int:
    """從 JWT 取得當前使用者 ID（int）"""
    return int(get_jwt_identity())


def get_current_role() -> str:
    """從 JWT 取得當前角色"""
    return get_jwt().get('role', 'user')


def get_current_username() -> str:
    """從 JWT 取得當前使用者帳號"""
    return get_jwt().get('username', '')
