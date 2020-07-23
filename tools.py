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
    abort(status, status=status, msg=msg)

def _base62_encode(num, alphabet=app_config.ALPHABET):
    if (num == 0):
        return alphabet[0]
    arr = []
    base = len(alphabet)
    while num:
        rem = num % base
        num = num // base
        arr.append(alphabet[rem])
    arr.reverse()
    return ''.join(arr)

def _base62_decode(string, alphabet=app_config.ALPHABET):
    base = len(alphabet)
    strlen = len(string)
    num = 0

    idx = 0
    for char in string:
        power = (strlen - (idx + 1))
        try:
            num += alphabet.index(char) * (base ** power)
        except:
            abort_msg(404, '分享链接不存在!')
        idx += 1
    return num


def create_token(id):
    # 通过id生成一串字符并尽可能达到安全
    # 1. 先将id增加到16位
    id = str(id)
    while(len(id)!=16):
        id = "0" + id
    # 2. 再对id进行逆序，取id最后x位做为不变点，将字符串前后颠倒后再把它写到字符串的最前面
    # print(id)
    for i in range(0, 17):
        if i % 2 == 0:
            b = int(id[-i]) + 3
        else:
            b = int(id[-i]) + 6
        n_str_r = id[:b-1]
        n_str_l = id[b:]
        if i % 2 == 0:
            n_str = str(9 - int(b-3)) + n_str_l + str(9 - int(id[b-1])) + n_str_r
        else:
            n_str = str(b-6) + n_str_l + id[b-1] + n_str_r
        id = n_str
        # 替换第二位和倒数第四位，并将它们用9-
        tmp = list(id)
        temp = 9 - int(tmp[2])
        tmp[2] = str(9 - int(tmp[-4]))
        tmp[-4] = str(temp)
        # 替换第五位和倒数第二位，并将它们用9-
        temp = 9 - int(tmp[5])
        tmp[5] = str(9 - int(tmp[-2]))
        tmp[-2] = str(temp)
        # 替换第七位和倒数第五位
        temp = tmp[7]
        tmp[7] = tmp[-5]
        tmp[-5] = temp
        id = ''.join(tmp)
        if i % 2 == 0:
            # 计算md5
            hl = hashlib.md5()
            hl.update(id.encode(encoding='utf-8'))
            md5 = hl.hexdigest()
            # 取出md5最前面一位数字
            mf = None
            for j in md5:
                if j.isdigit():
                    mf = j
                    break
            if not mf:
                mf = '0'
            # 加入字符串的第三位置
            id = id[:3] + str(9 - int(mf)) + id[3:]
    return str(_base62_encode(int(id)))


def rec_token(id):
    id = str(_base62_decode(id))
    # 补充到50位
    while (len(id) != 42):
        id = "0" + id
    for i in range(0, 17):
        # 校验md5
        # 取出mf
        if i % 2 == 0:
            mf = str(9 - int(id[3]))
            id = id[:3] + id[4:]
            hl = hashlib.md5()
            hl.update(id.encode(encoding='utf-8'))
            md5 = hl.hexdigest()
            for j in md5:
                if j.isdigit():
                    if str(mf) != str(j):
                        abort_msg(404, '分享链接不存在!')
                    break
        tmp = list(id)
        temp = tmp[7]
        tmp[7] = tmp[-5]
        tmp[-5] = temp
        temp = 9 - int(tmp[5])
        tmp[5] = str(9 - int(tmp[-2]))
        tmp[-2] = str(temp)
        temp = 9 - int(tmp[2])
        tmp[2] = str(9 - int(tmp[-4]))
        tmp[-4] = str(temp)
        id = ''.join(tmp)
        if i % 2 == 0:
            b = int(9 - int(id[0])) + 3
        else:
            b = int(id[0]) + 6
        id = id[1:]
        n_str_r = id[:len(id) - (b)]
        n_str_l = id[len(id) - (b-1):]
        if i % 2 == 0:
            n_str = n_str_l + str(9 - int(id[-b])) + n_str_r
        else:
            n_str = n_str_l + id[-b] + n_str_r
        id = n_str
    return int(id)
