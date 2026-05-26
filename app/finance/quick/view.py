"""
手機快速記帳 Blueprint
url_prefix: /finance/quick
"""
from flask import Blueprint, render_template

app_finance_quick = Blueprint('app_finance_quick', __name__)


@app_finance_quick.route('/', methods=['GET'])
def quick_page():
    """手機快速記帳頁面（無需後端鑑權，由前端 JWT 控制）"""
    return render_template('finance/quick.html')
