from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from src.models.log import Log

app_log = Blueprint('app_log', __name__)


@app_log.route('/', methods=['GET'])
@jwt_required()
def list_logs():
    limit = request.args.get('limit', 200, type=int)
    logs = Log.find_all(limit=limit)
    return jsonify({'success': True, 'data': logs})
