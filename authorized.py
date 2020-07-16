from flask_restful import Resource, reqparse, abort
from flask import session, request, redirect
from model import *
from app import db
import msal
from tools import *


class authorized(Resource):
    def get(self):
        if request.args.get('state') != session.get("state"):
            abort_msg(400, '请求登录的账户与最终登录的账户不符合...')
        if "error" in request.args:  # Authentication/Authorization failure
            abort_msg(400, '验证失败...下面是错误信息...    ' + request.args.get("error") + "    "
                      + request.args.get("error_description"))
        if request.args.get('code'):
            cache = load_cache()
            result = build_msal_app(cache=cache).acquire_token_by_authorization_code(
                request.args['code'],
                scopes=app_config.SCOPE,
                redirect_uri=url_for("authorized", _external=True))
            if "error" in result:
                abort_msg(400, '验证失败...下面是错误信息...    ' + result.get("error") + "    "
                          + result.get("error_description"))
            # 得到当前用户UID
            if len(result.get("id_token_claims").get("oid")) != 36:
                abort_msg(400, '您的ID校验失败...')
            u = User.query.filter_by(oid=result.get("id_token_claims").get("oid")).first()
            if u is None:
                # 添加新用户
                try:
                    u = User()
                    u.oid = result.get("id_token_claims").get("oid")
                    db.session.add(u)
                    db.session.flush()
                    if u.uid <= 1:
                        raise BaseException
                    db.session.commit()
                except:
                    db.session.rollback()
                    abort_msg(500, '您的账户添加失败...请联系管理员')
            session["user"] = result.get("id_token_claims")
            session["uid"] = u.uid
            save_cache(cache)
            return redirect(app_config.APP_INDEX)
        return {'status': 200, 'msg': '什么也没有发生嘤嘤嘤'}