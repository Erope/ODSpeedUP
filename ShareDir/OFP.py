from flask_restful import Resource
from flask import session, request
from tools import build_speedup_link, abort_msg
import app_config
import requests
from furl import furl
from urllib.parse import urlparse
from bs4 import BeautifulSoup


def deal_ofp(url):
    if not urlparse(url).netloc == "1drv.ms":
        abort_msg(403, '输入的链接非OneDrive分享链接')
    s = requests.session()
    try:
        r = s.get(url, allow_redirects=False)
    except:
        abort_msg(500, '无法访问这个分享链接，请等待修复~~')
        return
    try:
        url = r.headers['Location']
    except:
        abort_msg(500, '您提交的链接可能不是分享链接或链接不可游客访问或者服务器错误')
    try:
        txt = s.get(url).text
    except:
        abort_msg(500, '服务器访问链接出错，请等待修复~')
        return
    try:
        soup = BeautifulSoup(txt, 'lxml')
        full_url = str(soup.find('noscript').find('meta').get('content'))
        url = full_url[6:]
        f = furl(url)
        cid = f.args['cid']
        id = f.args['id']
        authkey = f.args['authkey']
    except:
        abort_msg(500, '链接分析错误，请等待修复~~')
        return
    return {
        'status': 200,
        'is_dir': True,
        'OFB': False,
        'data': {
            'cid': cid,
            'id': id,
            'authkey': authkey
        }
    }


class OFP_DIR(Resource):
    def __init__(self):
        if 'uid' not in session:
            abort_msg(403, '您未登录，请先登录!')

    def get(self, cid, id, authkey):
        ps = int(request.args.get('ps', 30))
        si = int(request.args.get('si', 0))
        url = app_config.OFP_Dir_URL % (ps, si, authkey, id, cid)
        print(url)
        h = {
            'appid': '1141147648',
            'accept': 'application/json'
        }
        try:
            graph_data = requests.get(url, headers=h).json()
        except:
            abort_msg(500, '无法访问这个分享链接，请等待修复~~')
            return
        # print(requests.get(url, headers=h).text)
        if 'items' not in graph_data:
            abort_msg(500, '无法获取这个分享链接的信息，可能是链接授权过期了，返回重新进入试试?')
        result = list()
        for i in graph_data['items'][0]['folder']['children']:
            if 'folder' in i:
                r = {
                    'is_dir': True,
                    'cid': i['ownerCid'],
                    'id': i['id'],
                    'authkey': authkey,
                    'name': i['name'],
                }
            else:
                # 对link做处理，替换掉尾部
                d_url = i['urls']['download']
                l = d_url.rfind('/')
                r = {
                    'is_dir': False,
                    'down_url': build_speedup_link(d_url[:l]),
                    'name': i['name']+i['extension'],
                    'size': i['size']
                }
            r['CreationDate'] = i['displayCreationDate']
            r['ModifiedDate'] = i['displayModifiedDate']
            result.append(r)
        r_data = {
            'status': 200,
            'data': result,
            'startIndex': graph_data['items'][0]['folder']['startIndex'],
            'totalCount': graph_data['items'][0]['folder']['totalCount']
        }
        return r_data
