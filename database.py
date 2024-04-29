from sqlalchemy import create_engine, text
import os

DB_STRING = os.environ['DB_CONN_STR']

engine = create_engine(DB_STRING, echo=True)


def load_authors_from_db():
  with engine.connect() as conn:
    result = conn.execute(text("select * from authors"))
    authors = []
    for row in result.all():
      authors.append(row._asdict())
    return authors


def load_book_details(id):
  with engine.connect() as conn:
    result = conn.execute(text("SELECT * FROM authors WHERE id = :val"),
                          {"val": id})
    rows = result.all()
    if len(rows) == 0:
      return None
    else:
      return rows[0]._asdict()


def load_reviews_from_db(id):
  with engine.connect() as conn:
    result = conn.execute(text("SELECT * FROM reviews WHERE book_id = :val"),
                          {"val": id})
    rows = result.all()
    if len(rows) == 0:
      return None
    else:
      return rows


def add_review_to_db(book_id, data):
  with engine.connect() as conn:
    trans = conn.begin()  # Start a transaction
    try:
      query = text(
          "INSERT INTO reviews (book_id, title, content) VALUES (:book_id, :title, :content)"
      )
      params = {
          'book_id': book_id,
          'title': data['title'],
          'content': data['review_content']
      }
      conn.execute(query, params)
      trans.commit()  # Commit the transaction
    except:
      trans.rollback()  # Rollback the transaction on error
      raise
