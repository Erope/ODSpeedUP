from flask import session, url_for
from flask_restful import abort
import msal
import app_config
import uuid
import hashlib
import time
import base64


def load_cache():
    cache = msal.SerializableTokenCache()
    if session.get("token_cache"):
        cache.deserialize(session["token_cache"])
    return cache


def save_cache(cache):
    if cache.has_state_changed:
        session["token_cache"] = cache.serialize()


def build_msal_app(cache=None, authority=None):
    return msal.ConfidentialClientApplication(
        app_config.CLIENT_ID, authority=authority or app_config.AUTHORITY,
        client_credential=app_config.CLIENT_SECRET, token_cache=cache)


def build_auth_url(authority=None, scopes=None, state=None):
    return build_msal_app(authority=authority).get_authorization_request_url(
        scopes or [],
        state=state or str(uuid.uuid4()),
        redirect_uri=app_config.REDIRECT_URL)


def get_token_from_cache(scope=None):
    cache = load_cache()  # This web app maintains one cache per session
    cca = build_msal_app(cache=cache)
    accounts = cca.get_accounts()
    if accounts:  # So all account(s) belong to the current signed-in user
        result = cca.acquire_token_silent(scope, account=accounts[0])
        save_cache(cache)
        return result


def build_speedup_link(link):
    md5 = hashlib.md5()
    t = str(int(time.time()) + 60 * 60 * 8)
    md5.update(t.encode(encoding='utf-8'))
    if str(link).find('?') != -1:
        md5.update((link + "&uid=" + str(session.get('uid'))).encode(encoding='utf-8'))
    else:
        md5.update((link + "?uid=" + str(session.get('uid'))).encode(encoding='utf-8'))
    md5.update(app_config.URL_DOWN_SECURE_KEY.encode(encoding='utf-8'))
    h = base64.b64encode(md5.digest()).decode('utf-8').rstrip('=').replace('+', '-').replace('/', '_')
    if str(link).find('?') != -1:
        u_l = "&uid=" + str(session.get('uid')) + "&md5=" + h + '&expires=' + t
    else:
        u_l = "?uid=" + str(session.get('uid')) + "&md5=" + h + '&expires=' + t
    return app_config.URL_DOWN_HOST + link + u_l


def abort_msg(status, msg):
    abort(status, message={'status': status, 'msg': msg})
