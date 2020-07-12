from flask_restful import Resource, reqparse, abort
from flask import session
from model import *
from tools import *


class Session(Resource):
    def post(self):
        # 检查用户当前登录状态
        if 'uid' in session:
            abort_msg(409, '您当前已经登录，不可重复登录!')
        # 返回微软登录地址
        session["state"] = str(uuid.uuid4())
        auth_url = build_auth_url(scopes=app_config.SCOPE, state=session["state"])
        return {'status': 200, 'url': auth_url}

    def delete(self):
        session.clear()
        return {'status': 200, 'url': app_config.AUTHORITY + "/oauth2/v2.0/logout" +
        "?post_logout_redirect_uri=" + app_config.APP_INDEX}

    def get(self):
        if 'uid' in session:
            U = User.query.get(session.get('uid', -1))
            if U is None or U.uid <= 1:
                abort_msg(500, '数据库中不存在您的账户，可能是数据库离线也可能是您的账户被删除...')
            return {'status': 200, 'data': {
                'uid': session.get('uid'),
                'name': session.get('user').get('name'),
                'used': U.used
            }}
        else:
            abort_msg(404, '账户未登录')