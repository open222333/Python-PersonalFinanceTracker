from flask import Blueprint, render_template
from src import ADMIN_TITLE

app_admin = Blueprint('app_admin', __name__)


@app_admin.route('/')
def index():
    return render_template('admin/index.html', admin_title=ADMIN_TITLE)
