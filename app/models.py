from sqlalchemy import Boolean, Column, Integer, String, Text

from .db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    carrier_original_name = Column(String(255), nullable=False)
    stego_filename = Column(String(255), unique=True, nullable=False)
    mime_type = Column(String(255), nullable=False)
    start_bit = Column(Integer, nullable=False)
    interval_l = Column(Integer, nullable=False)
    mode = Column(String(50), nullable=False)
    created_by = Column(String(50), nullable=False)
    is_public = Column(Boolean, default=True)
