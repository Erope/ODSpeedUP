from flask_restful import Resource
from flask import session, request
from tools import get_token_from_cache, abort_msg, rec_token
import app_config
from urllib.parse import urlparse
from model import Share_URL

from ShareDir.OFB import deal_ofb, OFB_DIR, OFB_DIR_DOWN
from ShareDir.OFP import deal_ofp, OFP_DIR


class ShareDir(Resource):
    def __init__(self):
        if 'uid' not in session:
            abort_msg(403, '您未登录，请先登录!')

    def get(self, url):
        url = url + '?from=ODSpeedUP'
        for arg, value in request.args.items():
            url += "&%s=%s" % (arg, value)
        token = get_token_from_cache(app_config.SCOPE)
        if not token:
            abort_msg(500, '未能查询到您的token，请退出登录后重新登录...')
        if len(url) <= 15:
            abort_msg(400, '输入的链接过短')
        # 对url解码
        if url.startswith('http://'):
            url = url.replace('http://', 'https://')
        elif not url.startswith('https://'):
            url = 'https://' + url
        if urlparse(url).netloc.endswith('sharepoint.com'):
            return deal_ofb(url)
        if urlparse(url).netloc == "1drv.ms":
            return deal_ofp(url)


class LocalShare(Resource):
    def __init__(self):
        if 'uid' not in session:
            abort_msg(403, '您未登录，请先登录!')

    def get(self, token):
        token = rec_token(token)
        try:
            S = Share_URL.query.get(token)
        except:
            abort_msg(500, '无法访问数据库...')
            return
        if not S:
            abort_msg(404, '此分享链接不存在或已删除!')
            return
        r_data = {
            'status': 200,
            'data': {
                'msurl': S.msurl
            }
        }
        return r_data
