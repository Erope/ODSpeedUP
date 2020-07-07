from app import db

Base = db.Model
class User(Base):
    __tablename__ = "User"

    uid = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    oid = db.Column(db.CHAR(36), nullable=False)
    used = db.Column(db.BIGINT, default=0)
