def init_url():
    from app import api

    import Session.app
    api.add_resource(Session.app.Session, '/api/session')

    import authorized
    api.add_resource(authorized.authorized, '/api/authorized')

    import LocalFiles.app
    api.add_resource(LocalFiles.app.LocalFiles, '/api/files/', '/api/files/<path:path>')

    import ShareDir.app
    api.add_resource(ShareDir.app.ShareDir, '/api/sharedir/<path:url>')
    api.add_resource(ShareDir.app.OFB_DIR, '/api/ofbsharedir/<string:host_head>/<path:dir>')
    api.add_resource(ShareDir.app.OFB_DIR_DOWN, '/api/ofbdown/<string:host_header>/<string:dirver>/<string:item>')
    api.add_resource(ShareDir.app.OFP_DIR, '/api/ofpsharedir/<string:cid>/<string:id>/<string:authkey>')