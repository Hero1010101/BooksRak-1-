from flask import Flask, jsonify, redirect, render_template, request, url_for, flash
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, RadioField, validators
from flask_simple_captcha import CAPTCHA
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
import os
import re
from user import register_user, authenticate_user, User, user_loader
from database import (add_review_to_db, load_books_from_db, load_book_details,
                      load_reviews_from_db, engine)
from filter import REPLACEMENTS

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'alies_grises')
login_manager = LoginManager()
login_manager.init_app(app)

DEFAULT_CONFIG = {
    'SECRET_CAPTCHA_KEY':
    'Petrogradsmeltofcarbolicacid',  # use for JWT encoding/decoding

    # CAPTCHA GENERATION SETTINGS
    'EXPIRE_SECONDS': 60 * 10,  # takes precedence over EXPIRE_MINUTES
    'CAPTCHA_IMG_FORMAT': 'JPEG',  # 'PNG' or 'JPEG' (JPEG is 3X faster)

    # CAPTCHA TEXT SETTINGS
    'CAPTCHA_LENGTH': 6,  # Length of the generated CAPTCHA text
    'CAPTCHA_DIGITS': True,  # Should digits be added to the character pool?
    'EXCLUDE_VISUALLY_SIMILAR': True,  # Exclude visually similar characters
    'BACKGROUND_COLOR':
    (190, 10, 50),  # RGB(A?) background color (default black)
    'TEXT_COLOR': (0, 0, 0),
}

SIMPLE_CAPTCHA = CAPTCHA(config=DEFAULT_CONFIG)
app = SIMPLE_CAPTCHA.init_app(app)


@login_manager.user_loader
def loading_user(user_id):
  return user_loader(user_id)


Session = sessionmaker(bind=engine)

# Search bar for books</li>
# To enable search and recommendation, use some ML nonsense</li>


class ReviewForm(FlaskForm):
  title = StringField(
      'title', [validators.Length(min=1, max=100),
                validators.DataRequired()])
  review_content = TextAreaField(
      'review-content', [validators.Length(min=1),
                         validators.DataRequired()])
  rating = RadioField('Rating',
                      choices=[('1', '1 Star'), ('2', '2 Stars'),
                               ('3', '3 Stars'), ('4', '4 Stars'),
                               ('5', '5 Stars')],
                      validators=[validators.DataRequired()])


@app.errorhandler(401)
def unauthorized(error):
  url = '/login'
  return render_template(
      'error.html',
      error_code=401,
      error_message=
      'You must be logged in to access this page. Please log in or sign up.',
      url=url), 401


@app.errorhandler(403)
def forbidden(error):
  url = '/'
  return render_template('error.html',
                         error_code=403,
                         error_message='Forbidden, Classified Information.',
                         url=url), 403


@app.errorhandler(404)
def page_not_found(error):
  url = '/'
  return render_template('error.html',
                         error_code=404,
                         error_message='Page Not Found.',
                         url=url), 404


@app.errorhandler(405)
def method_not_allowed(error):
  return render_template('error.html',
                         error_code=405,
                         error_message='Method Not Allowed.'), 405


@app.route("/")
def home():
  #books = load_books_from_db()
  return render_template('home.html')


@app.route("/books")
def bookspage():
  books = load_books_from_db()
  return render_template('oldhome.html', books=books)


@app.route("/new")
def new():
  return render_template('new.html')


@app.route("/about")
def about():
  return render_template('about.html', title='About')


@app.route("/api/books")
def list():
  api_books = load_books_from_db()
  return jsonify(api_books)


@app.route("/book/<id>")
@login_required
def details(id):
  book = load_book_details(id)
  if not book:
    return render_template('error.html',
                           error_code=404,
                           error_message='Book not found'), 404
  if request.method == 'GET':
    new_captcha_dict = SIMPLE_CAPTCHA.create()
    return render_template('book.html', book=book, captcha=new_captcha_dict)


@app.route("/book/<id>/review", methods=['POST'])
@login_required
def create_review(id):
  book = load_book_details(id)
  data = request.form
  review_title = data['title']
  review_content = data['review_content']
  rating = int(data['rating'])

  c_hash = str(request.form.get('captcha-hash'))
  c_text = str(request.form.get('captcha-text'))

  if SIMPLE_CAPTCHA.verify(c_text, c_hash):
    processed_review_content = replace(review_content)
    status = add_review_to_db(id, review_title, processed_review_content,
                              rating, current_user.username)
    if status:
      flash('Your review has been successfully posted.', 'success')
      return redirect(url_for('review_submitted', id=id))
    else:
      message = 'You have already reviewed this book.'
      return render_template('epicfail.html', message=message)
  else:
    message = 'Yikes sweetie, you failed the CAPTCHA, not a good look 💅'
    return render_template('epicfail.html', message=message)


def replace(text):
  for word, replacement in REPLACEMENTS.items():
    text = re.sub(re.escape(word), replacement, text, flags=re.IGNORECASE)
  return text


@app.route("/book/<id>/review/submitted")
def review_submitted(id):
  book = load_book_details(id)
  return render_template('reviewsuccess.html', book=book)


@app.route("/book/<id>/reviews")
def load_reviews(id):
  book = load_book_details(id)
  reviews_data = load_reviews_from_db(id)
  # If load_reviews_from_db returned None, meaning there are no reviews
  if reviews_data is None:
    return render_template('error.html',
                           error_code=404,
                           error_message='No reviews for this book'), 404
  else:
    return render_template('reviews.html',
                           reviews_data=reviews_data,
                           book=book)


@app.route("/review/<int:review_id>/like", methods=['POST'])
@login_required
def like_review(review_id):
  with engine.connect() as conn:
    transaction = conn.begin()  # Start a transaction explicitly
    try:
      # Increment the likes column for the given review
      conn.execute(
          text(
              "UPDATE reviews SET likes = likes + 1 WHERE review_id = :review_id"
          ), {'review_id': review_id})

      # Fetch the new likes count to return it
      result = conn.execute(
          text("SELECT likes FROM reviews WHERE review_id = :review_id"),
          {'review_id': review_id})
      new_likes = result.scalar()  # Fetch the single like count value

      transaction.commit()  # Commit the transaction
      return jsonify(success=True, new_likes=new_likes)
    except SQLAlchemyError as e:
      transaction.rollback()  # Rollback the transaction on error
      print(f"Error during transaction: {e}")
      return jsonify(success=False, message="Failed to update likes."), 500


@app.route('/register', methods=['GET', 'POST'])
def register():
  if request.method == 'POST':
    username = request.form['username']
    password = request.form['password']
    profile_picture = request.form.get('profile_picture')

    c_hash = str(request.form.get('captcha-hash'))
    c_text = str(request.form.get('captcha-text'))

    if SIMPLE_CAPTCHA.verify(c_text, c_hash):
      register_user(username, password, profile_picture)
      return redirect(url_for('home'))
    else:
      return 'failed captcha'
  if request.method == 'GET':
    new_captcha_dict = SIMPLE_CAPTCHA.create()
    return render_template('register.html', captcha=new_captcha_dict)


@app.route('/login', methods=['GET', 'POST'])
def login():
  if request.method == 'POST':
    username = request.form['username']
    password = request.form['password']
    username = username.lower()
    user = authenticate_user(username, password)
    if user:
      login_user(user)
      return redirect(url_for('bookspage'))
    else:
      message = 'Invalid username or password'
      return render_template('epicfail.html', message=message)
  return render_template('login.html')


@app.route('/@<username>')
def profile(username):
  session = Session()
  user = session.query(User).filter_by(username=username).first()
  if not user:
    return render_template('error.html',
                           error_code=404,
                           error_message='User not found'
                           ), 404  # Handling case where user does not exist
  return render_template('profile.html', user=user)


@app.route('/logout')
@login_required
def logout():
  logout_user()
  return redirect(url_for('home'))


if __name__ == '__main__':
  app.run(host='0.0.0.0', debug=True)
