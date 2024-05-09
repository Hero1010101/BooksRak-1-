from sqlalchemy import create_engine, text, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, query
from sqlalchemy.sql import text
import os

DB_STRING = os.environ['DB_CONN_STR']
Base = declarative_base()
engine = create_engine(DB_STRING, echo=True)
Session = sessionmaker(bind=engine)
session = Session()

class Book(Base):
  __tablename__ = 'books'

  book_id = Column(Integer, primary_key=True)
  book_name = Column(String(255))
  author_name = Column(String(255))
  year_pub = Column(String(4))
  rating_1 = Column(Integer, default=0)
  rating_2 = Column(Integer, default=0)
  rating_3 = Column(Integer, default=0)
  rating_4 = Column(Integer, default=0)
  rating_5 = Column(Integer, default=0)
  ratings_count = Column(Integer, default=0)
  avg_rating = Column(Float, default=0.0)
  img_url = Column(String(255))

  def update_ratings(self, rating_updates):
    for rating, increment in rating_updates.items():
      setattr(self, rating, getattr(self, rating) + increment)

    self.recalculate_ratings()

  def recalculate_ratings(self):
    ratings = [
        self.rating_1, self.rating_2, self.rating_3, self.rating_4,
        self.rating_5
    ]
    self.ratings_count = sum(ratings)
    self.avg_rating = sum(r * (idx + 1) for idx, r in enumerate(
        ratings)) / self.ratings_count if self.ratings_count > 0 else 0

  @staticmethod
  def add_or_update_book(book_id, updates, rating_updates):
    session = Session()
    book = session.query(Book).filter_by(book_id=book_id).first()

    if not book:
      book = Book(**updates)
      session.add(book)

    book.update_ratings(rating_updates)
    session.commit()
    session.close()

# BookQuery = db.session.query_property()

def load_books_from_db():
  with engine.connect() as conn:
    result = conn.execute(text("select * from books"))
    books = []
    for row in result.all():
      books.append(row._asdict())
    return books


def load_book_details(book_id):
  with engine.connect() as conn:
    result = conn.execute(text("SELECT * FROM books WHERE book_id = :val"),
                          {"val": book_id})
    rows = result.all()
    if len(rows) == 0:
      return None
    else:
      return rows[0]._asdict()

def load_reviews_from_db(book_id):
  with engine.connect() as conn:
    # Update the SQL query to include a JOIN with the users table
    # We select specific columns including those from the users table such as username and profile_picture_link
    query = text("""
            SELECT r.review_id, r.book_id, r.title, r.content, r.review_rating, r.likes, r.username, COALESCE(u.profile_picture_link, 'default.jpg') AS profile_picture_link
            FROM reviews r
            LEFT JOIN users u ON r.username = u.username
            WHERE r.book_id = :book_id
        """)
    result = conn.execute(query, {'book_id': book_id})
    reviews = result.fetchall()  # Fetch all results
    if len(reviews) == 0:
      return None
    else:
      return [review._asdict() for review in reviews
              ]  # Convert each SQLAlchemy RowProxy to a dictionary


def add_review_to_db(book_id, title, content, review_rating, username):
  with engine.connect() as conn:
    trans = conn.begin()  # Start a transaction
    try:
      # Insert the new review
      insert_review_query = text(
          "INSERT INTO reviews (book_id, title, content, review_rating, username) VALUES (:book_id, :title, :content, :review_rating, :username)"
      )
      review_params = {
          'book_id': book_id,
          'title': title,
          'content': content,
          'review_rating': review_rating,
          'username': username
      }
      conn.execute(insert_review_query, review_params)

      # Update the book's rating count
      update_rating_query = text(
          f"UPDATE books SET rating_{review_rating} = rating_{review_rating} + 1, ratings_count = ratings_count + 1 WHERE book_id = :book_id"
      )
      conn.execute(update_rating_query, {'book_id': book_id})

      # Recalculate the average rating
      recalc_avg_query = text(
          "UPDATE books SET avg_rating = ((rating_1 * 1) + (rating_2 * 2) + (rating_3 * 3) + (rating_4 * 4) + (rating_5 * 5)) / ratings_count WHERE book_id = :book_id"
      )
      conn.execute(recalc_avg_query, {'book_id': book_id})

      trans.commit()  # Commit the transaction
      return True
    except Exception as e:
      trans.rollback()  # Rollback the transaction on error
      if "Duplicate entry" in str(e):
        return False
      else:
        raise e
