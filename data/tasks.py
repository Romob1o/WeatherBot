import sqlalchemy
import sqlalchemy.schema
from sqlalchemy import orm
from .db_session import SqlAlchemyBase


class Task(SqlAlchemyBase):
    __tablename__ = 'tasks'

    user_tg_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.user_tg_id"), primary_key=True)
    city = sqlalchemy.Column(sqlalchemy.String, primary_key=True)
    time = sqlalchemy.Column(sqlalchemy.String, primary_key=True)

    # sqlalchemy.schema.ForeignKeyConstraint(
    #     ["user_tg_id"], ["users.user_tg_id"], name="foreign_key"
    # )

    user = orm.relationship('User')
