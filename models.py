import datetime
import sqlalchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy.orm import Session
import sqlalchemy.ext.declarative as dec

SqlAlchemyBase = dec.declarative_base()
engine = sa.create_engine("sqlite:///db/main.db", echo=False)

class User(SqlAlchemyBase, UserMixin):
    __tablename__ = 'users'

    id = sqlalchemy.Column(sqlalchemy.Integer, 
                           primary_key=True, autoincrement=True)
    nickname = sqlalchemy.Column(sqlalchemy.String, nullable=True, unique=True)
    email = sqlalchemy.Column(sqlalchemy.String, index=True, unique=True, nullable=True)
    hashed_password = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    forum_id = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)
    follow = sqlalchemy.Column(sqlalchemy.String, nullable=True)

    def set_password(self, password):
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.hashed_password, password)


class Forum(SqlAlchemyBase):
    __tablename__ = 'forums'

    id = sqlalchemy.Column(sqlalchemy.Integer, 
                           primary_key=True, autoincrement=True)
    title = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    private = sqlalchemy.Column(sqlalchemy.Boolean, default=False)
    personal = sqlalchemy.Column(sqlalchemy.Boolean, default=False)
    admin_id = sqlalchemy.Column(sqlalchemy.Integer)
    # admin_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id"))
    editors = sqlalchemy.Column(sqlalchemy.String, default="")
    # user = orm.relation('User')


class Message(SqlAlchemyBase):
    __tablename__ = 'messages'

    id = sqlalchemy.Column(sqlalchemy.Integer, 
                           primary_key=True, autoincrement=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id"))
    forum_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("forums.id"))
    message = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    datetime = sqlalchemy.Column(sqlalchemy.DateTime, nullable=True)
    user = orm.relation('User')
    forum = orm.relation('Forum')


class Event(SqlAlchemyBase):
    __tablename__ = 'events'

    id = sqlalchemy.Column(sqlalchemy.Integer, 
                           primary_key=True, autoincrement=True)
    forum_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("forums.id"))
    title = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    desc = sqlalchemy.Column(sqlalchemy.Text, nullable=True)
    geo_point = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    datetime = sqlalchemy.Column(sqlalchemy.DateTime, nullable=True)
    forum = orm.relation('Forum')


class Bots(SqlAlchemyBase):
    __tablename__ = 'bots'

    id = sqlalchemy.Column(sqlalchemy.Integer, 
                           primary_key=True, autoincrement=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id"))
    server = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    user = orm.relation('User')


SqlAlchemyBase.metadata.create_all(engine)
session_maker = orm.sessionmaker(bind=engine)