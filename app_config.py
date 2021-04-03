import os
env_dist = os.environ
CLIENT_SECRET = "CLIENT_SECRET"
AUTHORITY = "https://login.microsoftonline.com/common"
CLIENT_ID = "CLIENT_ID"
# 如果环境中存在OD这个变量
if env_dist.get('OD'):
    REDIRECT_URL = "https://xxx/api/authorized"
    APP_INDEX = "https://xxx/"
    # 设置mysql的错误跟踪信息显示
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # 打印每次模型操作对应的SQL语句
    SQLALCHEMY_ECHO = False
else:
    REDIRECT_URL = "http://localhost:5000/api/authorized"
    APP_INDEX = "http://localhost:5000/"
    # 设置mysql的错误跟踪信息显示
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    # 打印每次模型操作对应的SQL语句
    SQLALCHEMY_ECHO = True

SCOPE = ["User.Read", "files.readwrite.all"]
SESSION_TYPE = "filesystem"
URL_DOWN_SECURE_KEY = " md5key"
URL_DOWN_HOST = "https://speeduphost/"

SQLALCHEMY_DATABASE_URI = "mysql+pymysql://user:passwd@host:3306/OD"

SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_recycle': 120,
    'echo_pool': True,
    'pool_pre_ping': True,
    'pool_timeout': 5
}
# 随机字母表，记得修改
ALPHABET = "SxpYsEM1u2mhyGHjFQZJCTAfWkL3NXtB7z58qKnw6vPber4cgRU9adVD"

LocalFiles_root = 'https://graph.microsoft.com/v1.0/me/drive/root/children'
LocalFiles = 'https://graph.microsoft.com/v1.0/me/drive/root:/%s:/children'
OFP_Dir_URL = 'https://skyapi.onedrive.live.com/API/2/GetItems?caller=4A0A38E76EA967FA&sb=0&ps=%d&sd=0&gb=0,1,2&d=1&m=zh-CN&iabch=1&pi=5&path=1&lct=1&rset=odweb&urlType=0&si=%d&authKey=%s&id=%s&cid=%s'
Down_Token = 'Token'
