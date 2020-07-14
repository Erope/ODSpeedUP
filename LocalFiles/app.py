from flask_restful import Resource, reqparse, abort
from flask import session, request
from model import *
from tools import *
import requests
from furl import furl


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
            result.append(f)
        if '@odata.nextLink' in graph_data:
            url = graph_data['@odata.nextLink']
            f = furl(url)
            next = f.args['$skiptoken']
            return {'status': 200, 'data': result, 'skiptoken': next}
        else:
            return {'status': 200, 'data': result}