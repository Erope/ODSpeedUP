def init_url():
    from app import api

    import Session.app
    api.add_resource(Session.app.Session, '/api/session')

    import authorized
    api.add_resource(authorized.authorized, '/api/authorized')

    import LocalFiles.app
    api.add_resource(LocalFiles.app.LocalFiles, '/api/files/', '/api/files/<path:path>')