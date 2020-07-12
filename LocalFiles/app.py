from flask_restful import Resource, reqparse, abort
from flask import session
from model import *
from tools import *
import requests


class LocalFiles(Resource):
    def __init__(self):
        if 'uid' not in session:
            abort_msg(404, '您未登录，请先登录!')

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
        graph_data = requests.get(  # Use token to call downstream service
            url,
            headers={'Authorization': 'Bearer ' + token['access_token']},
        ).json()
        result = list()
        for i in graph_data['value']:
            if 'folder' in i:
                if path:
                    f = {'name': i['name'], 'type': 1, 'path': path.strip('/') + '/' + i['name']}
                else:
                    f = {'name': i['name'], 'type': 1, 'path': '/' + i['name']}
                result.append(f)
            elif '@microsoft.graph.downloadUrl' in i:
                f = {'name': i['name'], 'type': 0, 'url': build_speedup_link(i['@microsoft.graph.downloadUrl'])}
                result.append(f)
            else:
                continue
        return {'status': 200, 'data': result}