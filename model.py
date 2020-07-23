from app import db


class User(db.Model):
    __tablename__ = "User"

    uid = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    oid = db.Column(db.CHAR(36), nullable=False)
    used = db.Column(db.BIGINT, default=0)


class Share_URL(db.Model):
    __tablename__ = "Share_URL"

    sid = db.Column(db.BIGINT, primary_key=True, autoincrement=True, nullable=False)
    msurl = db.Column(db.VARCHAR(400), nullable=False)
    uid = db.Column(db.BIGINT, db.ForeignKey('User.uid'), default=0, nullable=False)
    user = db.relationship('User', backref=db.backref('shares'))
