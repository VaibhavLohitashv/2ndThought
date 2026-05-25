import enum

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    LargeBinary,
    func,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# SECURITY: Define constant to avoid duplicating literal string
USERS_TABLE_ID = "users.id"


# Role inside a specific thread
class ThreadRole(enum.Enum):
    admin = "admin"  # thread owner
    moderator = "moderator"  # thread moderator
    participant = "participant"  # normal member
    member = "member"  # alias for participant (route compatibility)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    firebase_uid = Column(String, unique=True)
    full_name = Column(String)
    avatar_url = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # user.threads -> thread membership list
    thread_memberships = relationship("ThreadMembership", back_populates="user")


class Thread(Base):
    __tablename__ = "threads"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text)

    created_by = Column(Integer, ForeignKey(USERS_TABLE_ID), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # thread.memberships -> list of ThreadMembership
    memberships = relationship("ThreadMembership", back_populates="thread")

    # thread.posts -> list of posts inside thread
    posts = relationship("Post", back_populates="thread")


class ThreadMembership(Base):
    __tablename__ = "thread_memberships"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey(USERS_TABLE_ID), nullable=False)
    thread_id = Column(Integer, ForeignKey("threads.id"), nullable=False)

    role = Column(Enum(ThreadRole), nullable=False, server_default="participant")

    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="thread_memberships")
    thread = relationship("Thread", back_populates="memberships")


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    thread_id = Column(Integer, ForeignKey("threads.id"), nullable=False)

    parent_id = Column(Integer, ForeignKey("posts.id"), nullable=True)
    content = Column(Text, nullable=False)
    image_data = Column(LargeBinary, nullable=True)
    image_filename = Column(String, nullable=True)

    user_id = Column(Integer, ForeignKey(USERS_TABLE_ID), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    thread = relationship("Thread", back_populates="posts")
    parent = relationship("Post", remote_side=[id], backref="children")
    user = relationship("User")