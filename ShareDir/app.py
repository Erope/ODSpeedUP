from flask_restful import Resource, reqparse, abort
from flask import session, request
from model import *
from tools import *
import requests
from furl import furl
import base64
from urllib.parse import urlparse
import re


class ShareDir(Resource):
    def __init__(self):
        if 'uid' not in session:
            abort_msg(403, '您未登录，请先登录!')

    def get(self, url):
        token = get_token_from_cache(app_config.SCOPE)
        if not token:
            abort_msg(500, '未能查询到您的token，请退出登录后重新登录...')
        url = str(url).replace('-', '+')
        url = url.replace('_', '/')
        if len(url) <= 10:
            abort_msg(400, '输入的链接过短')
        if len(url) % 4 == 2:
            url += '=='
        elif len(url) % 4 == 3:
            url += '='
        # 对url解码
        try:
            url = base64.b64decode(url.encode('utf-8')).decode('utf-8')
        except:
            abort_msg(500, '输入的链接未能成功解码BASE64')
        if not urlparse(url).netloc.endswith('sharepoint.com'):
            abort_msg(403, '输入的链接非OneDrive分享链接')
        try:
            r = requests.get(url, allow_redirects=False)
        except:
            abort_msg(500, '无法请求这个资源，请等待修复')
            return
        try:
            t_url = r.headers['Location']
        except:
            abort_msg(500, '您输入的可能非文件夹分享或服务器内部错误')
            return
        try:
            url_list = t_url.split('/')
            host_head = '/'.join(url_list[2:5])
            f = furl(t_url)
            full_dir = f.args['id'].strip('/')
            # 录入session
            session['FedAuth'] = r.cookies.get_dict()['FedAuth']
        except:
            abort_msg(500, '分析链接时出错')
            return
        # return redirect(url_for('share_dir', host_head=ss.replace('/', '#').replace('https://', ''), dir=full))
        return {
                'status': 200,
                'is_dir': True,
                'OFB': True,
                'data': {
                    'host_head': host_head.replace('/', '!'),
                    'dir': full_dir
                }
        }


class OFB_DIR(Resource):
    def __init__(self):
        if 'uid' not in session:
            abort_msg(403, '您未登录，请先登录!')

    def get(self, host_head, dir):
        host_head_org = host_head
        token = get_token_from_cache(app_config.SCOPE)
        if not token:
            abort_msg(500, '未能查询到您的token，请退出登录后重新登录...')
        try:
            host_head = str(host_head).replace('!', '/')
            full = '/' + str(dir)
            first = '/'.join(full.split('/')[0:4])
        except:
            abort_msg(500, '读取链接时出错')
            return
        # 读取session
        try:
            FedAuth = session['FedAuth']
        except:
            abort_msg(403, '您没有访问此链接的权限!')
            return
        cookies = {
            'FedAuth': FedAuth
        }
        r_url = "https://%s/_api/web/GetListUsingPath(DecodedUrl=@a1)/RenderListDataAsStream?@a1='%s'&RootFolder=%s" % (
            host_head, first, full)
        h = {
            'accept': 'application/json;odata=verbose',
            'content-type': 'application/json;odata=verbose',
        }
        d = '{"parameters":{"__metadata":{"type":"SP.RenderListDataParameters"},"RenderOptions":1185543,"AllowMultipleValueFilterForTaxonomyFields":true,"AddRequiredFields":true}}'
        try:
            graph_data = requests.post(r_url, data=d, headers=h, cookies=cookies).json()
        except:
            abort_msg(500, '请求微软服务器失败...')
            return
        # 缺少错误判断
        result = list()
        for i in graph_data['ListData']['Row']:
            if i['FSObjType'] == '1':
                f = {
                    'is_dir': True,
                    'host_head': host_head_org,
                    'dir': dir + '/' + i['FileLeafRef'],
                    'name': i['FileLeafRef'],
                    'child_num': i['ItemChildCount'],
                    'lastModifiedDateTime': i['Modified']
                }
            else:
                Item_url = i['.spItemUrl']
                reg = "https://(.*)-my.sharepoint.com:443/_api/v2.0/drives/(.*)/items/(.*)?version=Published"
                matchObj = re.match(reg, Item_url)
                f = {
                    'is_dir': False,
                    'host_header': matchObj.group(1),
                    'dirver': matchObj.group(2),
                    'item': matchObj.group(3),
                    'name': i['FileLeafRef'],
                    'size': i['FileSizeDisplay'],
                    'lastModifiedDateTime': i['Modified']
                }
            result.append(f)
        return {'status': 200, 'data': result}


class OFB_DIR_DOWN(Resource):
    def __init__(self):
        if 'uid' not in session:
            abort_msg(403, '您未登录，请先登录!')

    def get(self, host_header, dirver, item):
        token = get_token_from_cache(app_config.SCOPE)
        if not token:
            abort_msg(500, '未能查询到您的token，请退出登录后重新登录...')
        # 读取session
        FedAuth = session.get('FedAuth')
        cookies = {
            'FedAuth': FedAuth
        }
        h = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36 Edg/83.0.478.58'}
        r_url = "https://%s-my.sharepoint.com/_api/v2.0/drives/%s/items/%s?version=Published" % (host_header, dirver, item)
        graph_data = requests.get(r_url, cookies=cookies, headers=h).json()
        return {'status': 200, 'url': build_speedup_link(graph_data['@content.downloadUrl'])}