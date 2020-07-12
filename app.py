import uuid
import requests
from flask import Flask, render_template, session, request, redirect, url_for
from flask_session import Session
import msal
import app_config
import hashlib
import base64
import time
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_sqlalchemy import SQLAlchemy
from furl import furl
from bs4 import BeautifulSoup
import re


app = Flask(__name__)
app.config.from_object(app_config)
app.wsgi_app = ProxyFix(app.wsgi_app)
db = SQLAlchemy()
db.init_app(app)
from model import *
Session(app)

herf = '''<a href="%s">%s</a><br>'''

@app.route("/")
def index():
    # print(json.dumps(dict(session)))
    if not session.get("user"):
        return redirect(url_for("login"))
    return render_template('index.html', user=session["user"], version=msal.__version__)

@app.route("/login")
def login():
    session["state"] = str(uuid.uuid4())
    # Technically we could use empty list [] as scopes to do just sign in,
    # here we choose to also collect end user consent upfront
    auth_url = _build_auth_url(scopes=app_config.SCOPE, state=session["state"])
    return render_template("login.html", auth_url=auth_url)

@app.route(app_config.REDIRECT_PATH)  # Its absolute URL must match your app's redirect_uri set in AAD
def authorized():
    if request.args.get('state') != session.get("state"):
        return redirect(url_for("index"))  # No-OP. Goes back to Index page
    if "error" in request.args:  # Authentication/Authorization failure
        return render_template("auth_error.html", result=request.args)
    if request.args.get('code'):
        cache = _load_cache()
        result = _build_msal_app(cache=cache).acquire_token_by_authorization_code(
            request.args['code'],
            scopes=app_config.SCOPE,  # Misspelled scope would cause an HTTP 400 error here
            redirect_uri=url_for("authorized", _external=True))
        if "error" in result:
            return render_template("auth_error.html", result=result)
        # 得到当前用户UID
        if len(result.get("id_token_claims").get("oid")) != 36:
            return "您的ID校验失败..."
        try:
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
                    return "您的账户添加失败...请联系管理员"
            if u.uid <= 1:
                return "您的账户查询失败...请联系管理员"
            session["user"] = result.get("id_token_claims")
            session["uid"] = u.uid
            _save_cache(cache)
        except:
            db.session.rollback()
            return "数据连接失败..."
        return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.clear()  # Wipe out user and its token cache from session
    return redirect(  # Also logout from your tenant's web session
        app_config.AUTHORITY + "/oauth2/v2.0/logout" +
        "?post_logout_redirect_uri=" + url_for("index", _external=True))


@app.route("/graphcall/")
@app.route("/graphcall/<path:path>")
def graphcall(path=None):
    token = _get_token_from_cache(app_config.SCOPE)
    if not token:
        return redirect(url_for("login"))
    if path is None:
        url = app_config.ENDPOINT
    else:
        if path[-1] == '/':
            url = app_config.ENDPOINT_s % (path.strip('/'))
        else:
            url = app_config.ENDPOINT_s % (path)
    graph_data = requests.get(  # Use token to call downstream service
        url,
        headers={'Authorization': 'Bearer ' + token['access_token']},
        ).json()
    U = User.query.get(session.get('uid', -1))
    if U is None or U.uid <= 1:
        return redirect(url_for("index"))
    result = "<p>您当前已用流量: %.3f GB</p><p>" % (U.used / (1024 * 1024 * 1024))
    for i in graph_data['value']:
        if 'folder' in i:
            result += herf % (i['name'] + '/', i['name'])
        elif '@microsoft.graph.downloadUrl' in i:
            result += herf % (_build_speedup_link(i['@microsoft.graph.downloadUrl']), i['name'])
        else:
            result += herf % ('', i['name'])
    result += '</p>'
    return result


@app.route("/shares/<path:s_url>")
def shares(s_url):
    token = _get_token_from_cache(app_config.SCOPE)
    if not token:
        return redirect(url_for("login"))
    s_url = base64.b64decode(s_url.encode('utf-8')).decode('utf-8')
    # 获取到跳转链接
    r = requests.get(s_url, allow_redirects=False)
    t_url = r.headers['Location']
    url_list = t_url.split('/')
    ss = '/'.join(url_list[0:5])
    f = furl(t_url)
    full = f.args['id'].strip('/')
    # 录入session
    session['FedAuth'] = r.cookies.get_dict()['FedAuth']
    return redirect(url_for('share_dir', host_head=ss.replace('/', '#').replace('https://', ''), dir=full))


@app.route("/shares_person/<path:s_url>")
def shares_person(s_url):
    token = _get_token_from_cache(app_config.SCOPE)
    if not token:
        return redirect(url_for("login"))
    s_url = base64.b64decode(s_url.encode('utf-8')).decode('utf-8')
    s = requests.session()
    r = s.get(s_url, allow_redirects=False)
    url = r.headers['Location']
    txt = s.get(url).text
    soup = BeautifulSoup(txt, 'lxml')
    full_url = str(soup.find('noscript').find('meta').get('content'))
    # 取出url
    url = full_url[6:]
    f = furl(url)
    cid = f.args['cid']
    id = f.args['id']
    authkey = f.args['authkey']
    return redirect(url_for('share_dir_person', cid=cid, id=id, authkey=authkey))


@app.route("/share_dir_person/<string:cid>/<string:id>/<string:authkey>")
def share_dir_person(cid, id, authkey):
    token = _get_token_from_cache(app_config.SCOPE)
    if not token:
        return redirect(url_for("login"))
    url = "https://skyapi.onedrive.live.com/API/2/GetItems?caller=4A0A38E76EA967FA&sb=0&ps=100&sd=0&gb=0,1,2&d=1&m=zh-CN&iabch=1&pi=5&path=1&lct=1&rset=odweb&v=0.3431471585423471&urlType=0&si=0&authKey=%s&id=%s&cid=%s" % (
    authkey, id, cid)
    h = {
        'appid': '1141147648',
        'accept': 'application/json'
    }
    graph_data = requests.get(url, headers=h).json()
    U = User.query.get(session.get('uid', -1))
    if U is None or U.uid <= 1:
        return redirect(url_for("index"))
    result = "<p>您当前已用流量: %.3f GB</p><p>" % (U.used / (1024 * 1024 * 1024))
    for i in graph_data['items'][0]['folder']['children']:
        if 'folder' in i:
            result += herf % (url_for('share_dir_person', cid=i['ownerCid'], id=i['id'], authkey=authkey), i['name'])
        else:
            # 对link做处理，替换掉尾部
            d_url = i['urls']['download']
            l = d_url.rfind('/')
            result += herf % (_build_speedup_link(d_url[:l]), i['name']+i['extension'])
    result += '</p>'
    return result


@app.route("/share_dir/<string:host_head>/<path:dir>")
def share_dir(host_head, dir):
    token = _get_token_from_cache(app_config.SCOPE)
    if not token:
        return redirect(url_for("login"))
    ss = host_head.replace('#', '/')
    full = '/' + dir
    first = '/'.join(full.split('/')[0:4])
    # 读取session
    FedAuth = session.get('FedAuth')
    cookies = {
        'FedAuth': FedAuth
    }
    r_url = "https://%s/_api/web/GetListUsingPath(DecodedUrl=@a1)/RenderListDataAsStream?@a1='%s'&RootFolder=%s" % (
    ss, first, full)
    h = {
        'accept': 'application/json;odata=verbose',
        'content-type': 'application/json;odata=verbose',
    }
    d = '{"parameters":{"__metadata":{"type":"SP.RenderListDataParameters"},"RenderOptions":1185543,"AllowMultipleValueFilterForTaxonomyFields":true,"AddRequiredFields":true}}'
    graph_data = requests.post(r_url, data=d, headers=h, cookies=cookies).json()
    U = User.query.get(session.get('uid', -1))
    if U is None or U.uid <= 1:
        return redirect(url_for("index"))
    db.session.commit()
    result = "<p>您当前已用流量: %.3f GB</p><p>" % (U.used / (1024 * 1024 * 1024))
    for i in graph_data['ListData']['Row']:
        if i['FSObjType'] == '1':
            result += herf % (url_for('share_dir', host_head=host_head, dir=dir+'/'+i['FileLeafRef']), i['FileLeafRef'])
        else:
            Item_url = i['.spItemUrl']
            reg = "https://(.*)-my.sharepoint.com:443/_api/v2.0/drives/(.*)/items/(.*)?version=Published"
            matchObj = re.match(reg, Item_url)
            result += herf % (url_for('get_share_down', host_head=matchObj.group(1), dirver=matchObj.group(2), item=matchObj.group(3)), i['FileLeafRef'])
    result += '</p>'
    return result


@app.route("/get_share_down/<string:host_head>/<string:dirver>/<string:item>")
def get_share_down(host_head, dirver, item):
    token = _get_token_from_cache(app_config.SCOPE)
    if not token:
        return redirect(url_for("login"))
    # 读取session
    FedAuth = session.get('FedAuth')
    cookies = {
        'FedAuth': FedAuth
    }
    h = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36 Edg/83.0.478.58'}
    r_url = "https://%s-my.sharepoint.com/_api/v2.0/drives/%s/items/%s?version=Published" % (host_head, dirver, item)
    graph_data = requests.get(r_url, cookies=cookies, headers=h).json()
    return redirect(_build_speedup_link(graph_data['@content.downloadUrl']))


def _load_cache():
    cache = msal.SerializableTokenCache()
    if session.get("token_cache"):
        cache.deserialize(session["token_cache"])
    return cache

def _save_cache(cache):
    if cache.has_state_changed:
        session["token_cache"] = cache.serialize()

def _build_msal_app(cache=None, authority=None):
    return msal.ConfidentialClientApplication(
        app_config.CLIENT_ID, authority=authority or app_config.AUTHORITY,
        client_credential=app_config.CLIENT_SECRET, token_cache=cache)

def _build_auth_url(authority=None, scopes=None, state=None):
    return _build_msal_app(authority=authority).get_authorization_request_url(
        scopes or [],
        state=state or str(uuid.uuid4()),
        redirect_uri=url_for("authorized", _external=True))

def _get_token_from_cache(scope=None):
    cache = _load_cache()  # This web app maintains one cache per session
    cca = _build_msal_app(cache=cache)
    accounts = cca.get_accounts()
    if accounts:  # So all account(s) belong to the current signed-in user
        result = cca.acquire_token_silent(scope, account=accounts[0])
        _save_cache(cache)
        return result


def _build_speedup_link(link):
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


app.jinja_env.globals.update(_build_auth_url=_build_auth_url)