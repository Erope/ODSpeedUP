from flask_restful import Resource, reqparse, abort
from flask import session, request
from tools import *
import requests
from furl import furl
import json
from model import *


class Offline_Down(Resource):
    def __init__(self):
        if 'uid' not in session:
            abort_msg(403, '您未登录，请先登录!')

    def post(self, path):
        parser = reqparse.RequestParser()
        parser.add_argument('url', type=str, required=True)
        args = parser.parse_args()
        if len(args['url']) < 5:
            abort_msg(400, '请确认下载链接')
        token = get_token_from_cache(app_config.SCOPE)
        if not token:
            abort_msg(500, '未能查询到您的token，请退出登录后重新登录...')
        post_data = '{"item":{"@microsoft.graph.conflictBehavior":"rename"}}'
        # 去除path开头
        path = path.lstrip('/')
        if path[-1] == '/':
            abort_msg(400, '请在路径中输入保存的文件名')
            return
        post_url = "https://graph.microsoft.com/v1.0/me/drive/root:/%s:/createUploadSession" % path
        # 获取post结果
        headers = {
            'content-type': 'application/json',
            'Authorization': 'Bearer ' + token['access_token']
        }
        try:
            r = requests.post(post_url, data=post_data, headers=headers).json()
        except:
            abort_msg(500, '无法与MS服务器取得链接')
            return
        if 'error' in r:
            abort_msg(400, r['error']['message'])
        if 'uploadUrl' not in r:
            abort_msg(500, '无法与MS服务器取得链接')
        upload_url = r['uploadUrl']
        # 放入数据库中
        ds = OfflineDown(Down_url=args['url'],
                         Last_update_time=int(time.time()),
                         Upload_url=upload_url,
                         uid=session['uid'])
        try:
            db.session.add(ds)
            db.session.flush()
            if ds.Did < 0:
                raise BaseException
            db.session.commit()
        except:
            db.session.rollback()
            abort_msg(500, '数据库连接错误!')
            return
        return {'status': 200, 'data': {'Did': ds.Did}}


class Offline_Down_Task(Resource):
    def get(self, Did=None):
        parser = reqparse.RequestParser()
        parser.add_argument('token', type=str, required=True)
        args = parser.parse_args()
        if args['token'] != app_config.Down_Token:
            abort_msg(403, '无权访问')
        if Did is not None:
            Task = OfflineDown.query.get(Did)
            if Task is None:
                abort_msg(404, '任务不存在或已删除')
            return {
                'status': 200,
                'data': {
                    'url': Task.Down_url,
                    'Upload_url': Task.Upload_url
                }
            }
        Task = db.session.query(OfflineDown).filter(OfflineDown.Status == 0).first()
        # 在高并发场景下应该再加一个redis之类 避免重复输出
        # 如果并发低使用mysql锁也可
        if Task is None:
            abort_msg(404, '暂无任务')
        Task.Status = 1
        try:
            db.session.commit()
        except:
            db.session.rollback()
            abort_msg(500, '数据库连接错误')
        return {
            'status': 200,
            'data': {
                'url': Task.Down_url,
                'Upload_url': Task.Upload_url
            }
        }

    def put(self, Did):
        parser = reqparse.RequestParser()
        parser.add_argument('token', type=str, required=True)
        parser.add_argument('Total_size', type=int, required=True)
        parser.add_argument('Down_size', type=int, required=True)
        parser.add_argument('Speed', type=int, required=True)
        parser.add_argument('Status', type=int, required=True)
        args = parser.parse_args()
        Task = OfflineDown.query.get(Did)
        if Task is None:
            abort_msg(404, '任务不存在或已删除')
        Task.Total_size = args['Total_size']
        Task.Down_size = args['Down_size']
        Task.Speed = args['Speed']
        Task.Status = args['Status']
        try:
            db.session.commit()
        except:
            db.session.rollback()
            abort_msg(500, '数据库连接错误')
        return {'status': 204}, 204
