from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, func
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import sessionmaker
from flask_login import UserMixin, login_user, logout_user, login_required
from typing import Any
from database import engine

Base = declarative_base()
Session = sessionmaker(bind=engine)


class User(UserMixin, Base):
  __tablename__ = 'users'
  user_id: Any = Column(Integer, primary_key=True)
  username: Any = Column(String(100), unique=True, nullable=False)
  password = Column(String(255), nullable=False)
  profile_picture_link = Column(String(255))
  created_at = Column(DateTime, default=func.now())

  def get_id(self):
    return str(self.user_id)

def register_user(username, password, profile_picture):
  # Normalize the username to lowercase
  normalized_username = username.lower()

  if not (4 <= len(username) < 21):
      raise ValueError("Username must be between 4 and 20 characters long")

  session = Session()
  # Check if the username already exists
  existing_user = session.query(User).filter(func.lower(User.username) == normalized_username).first()
  if existing_user:
      session.close()
      raise ValueError("Username already taken")

  hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

  new_user = User()
  new_user.username = normalized_username
  new_user.password = hashed_password
  new_user.profile_picture_link = profile_picture

  try:
      session.add(new_user)
      session.commit()
  finally:
      session.close()


def authenticate_user(username, password):
  session = Session()
  try:
    user = session.query(User).filter_by(username=username).first()
    if user and check_password_hash(user.password, password):
      return user
    return None
  finally:
    session.close()


def user_loader(user_id):
  session = Session()
  try:
    return session.query(User).get(int(user_id))
  finally:
    session.close()


Base.metadata.create_all(engine)
