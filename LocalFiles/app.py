from flask_restful import Resource, reqparse, abort
from flask import session, request
from tools import *
import requests
from furl import furl
import json
from model import *


class LocalFiles(Resource):
    def __init__(self):
        if 'uid' not in session:
            abort_msg(403, '您未登录，请先登录!')

    def get(self, path=None):
        token = get_token_from_cache(app_config.SCOPE)
        if not token:
            abort_msg(500, '未能查询到您的token，请退出登录后重新登录...')
        if path is None:
            url = app_config.LocalFiles_root
        else:
            if path[-1] == '/':
                url = app_config.LocalFiles % (path.strip('/'))
            else:
                url = app_config.LocalFiles % (path)
        # 查看有无下一页参数
        skiptoken = request.args.get("skiptoken")
        if skiptoken:
            url += "?$skiptoken=" + skiptoken
        try:
            graph_data = requests.get(  # Use token to call downstream service
                url,
                headers={'Authorization': 'Bearer ' + token['access_token']},
            ).json()
        except:
            abort_msg(500, '请求微软服务器失败...')
            return
        result = list()
        if 'value' not in graph_data:
            abort_msg(404, '文件目录不存在')
        for i in graph_data['value']:
            if 'folder' in i:
                if path:
                    f = {'name': i['name'], 'type': 1, 'path': path.strip('/') + '/' + i['name'] + '/'}
                else:
                    f = {'name': i['name'], 'type': 1, 'path': '/' + i['name'] + '/'}
            elif '@microsoft.graph.downloadUrl' in i:
                f = {'name': i['name'], 'type': 0, 'url': build_speedup_link(i['@microsoft.graph.downloadUrl'])}
            else:
                continue
            f['size'] = i['size']
            f['createdDateTime'] = i['createdDateTime']
            f['lastModifiedDateTime'] = i['lastModifiedDateTime']
            f['id'] = i['id']
            result.append(f)
        if '@odata.nextLink' in graph_data:
            url = graph_data['@odata.nextLink']
            f = furl(url)
            next = f.args['$skiptoken']
            return {'status': 200, 'data': result, 'skiptoken': next}
        else:
            return {'status': 200, 'data': result, 'skiptoken': False}


class ShareFiles(Resource):
    def __init__(self):
        if 'uid' not in session:
            abort_msg(403, '您未登录，请先登录!')

    def post(self, itemId):
        token = get_token_from_cache(app_config.SCOPE)
        if not token:
            abort_msg(500, '未能查询到您的token，请退出登录后重新登录...')
        # 判断itemId是否为字符串
        if not itemId.isalnum():
            abort_msg(500, 'itemId只能为数字和字母')
        url = "https://graph.microsoft.com/v1.0/me/drive/items/%s/createLink" % itemId
        headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token['access_token']}
        data = {
            'type': 'view',
            'scope': 'anonymous'
        }
        try:
            r = requests.post(url=url, headers=headers, data=json.dumps(data)).json()
        except:
            abort_msg(500, '请求微软服务器错误')
            return
        msurl = r['link']['webUrl']
        # 插入数据库
        S = Share_URL.query.filter_by(msurl=msurl, uid=session['uid']).first()
        if S is None:
            # 添加新URL
            try:
                S = Share_URL()
                S.msurl = msurl
                S.uid = session['uid']
                db.session.add(S)
                db.session.flush()
                if S.sid < 0:
                    raise BaseException
                db.session.commit()
            except:
                db.session.rollback()
                abort_msg(500, '添加分享链接到数据库时失败...')
        sid = S.sid
        # 取sid转换
        token = create_token(sid)
        r_data = {
            'status': 200,
            'data':
                {
                    'msurl': msurl,
                    'token': token
            }
        }
        return r_data
