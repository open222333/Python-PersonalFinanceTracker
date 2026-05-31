"""
文件 Blueprint
url_prefix: /docs

端點：
  GET /docs/  — 系統使用說明頁面
"""
from flask import Blueprint, render_template

app_docs = Blueprint('docs', __name__)


@app_docs.route('/', methods=['GET'])
def index():
    """系統使用說明頁面"""
    return render_template('docs/index.html')
