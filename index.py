from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_login import LoginManager, login_required, login_user, logout_user
from user import register_user, authenticate_user, User, user_loader
from sqlalchemy.orm import sessionmaker
import os

from database import (add_review_to_db, load_authors_from_db,
                      load_book_details, load_reviews_from_db, engine)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'alies_grises')
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def loading_user(user_id):
  return user_loader(user_id)


Session = sessionmaker(bind=engine)

# Display all reviews for particular book on that book's reviews page
# Add word filter for reviews
# Add pagination for reviews (that thing with the pages listed (< 1 2 3 >)) OR infinite scroll
# Search bar for books
# Sorting books and reviews
# Getting book info from some API
# Add user login
# Add captcha to form
# Add admin login
# Rating for each book in review
# Like reviews


@app.errorhandler(403)
def forbidden(error):
  return render_template(
      'error.html',
      error_code=403,
      error_message='Forbidden, classified information'), 403


@app.errorhandler(404)
def page_not_found(error):
  return render_template(
      'error.html',
      error_code=404,
      error_message=
      'Not Found, someone typed something wrong and it was probably you.'), 404


@app.errorhandler(405)
def method_not_allowed(error):
  return render_template(
      'error.html',
      error_code=405,
      error_message='Method Not Allowed, do better sweetie.'), 405


@app.route("/")
def home():
  authors = load_authors_from_db()
  return render_template('home.html', authors=authors)


@app.route("/new")
def new():
  return render_template('new.html')


@app.route("/about")
def about():
  return render_template('about.html', title='About')


@app.route("/api/authors")
def list():
  api_authors = load_authors_from_db()
  return jsonify(api_authors)


@app.route("/book/<id>")
@login_required
def details(id):
  book = load_book_details(id)
  if not book:
    return render_template('error.html',
                           error_code=404,
                           error_message='Book not found'), 404
  return render_template('book.html', book=book)
  #return jsonify(author)


@app.route("/book/<id>/review", methods=['post'])
def create_review(id):
  data = request.form
  book = load_book_details(id)
  add_review_to_db(id, data)
  # return render_template('review.html', review=data, book=book)
  return redirect(url_for('review_submitted', id=id))


@app.route("/book/<id>/review/submitted")
def review_submitted(id):
  book = load_book_details(id)
  return render_template('review.html', book=book)


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
    # Since reviews_data is a list of dictionaries, we can pass it directly to the template
    return render_template('reviews.html',
                           reviews_data=reviews_data,
                           book=book)


@app.route('/register', methods=['GET', 'POST'])
def register():
  if request.method == 'POST':
    username = request.form['username']
    password = request.form['password']
    register_user(username, password)
    return redirect(url_for('home'))
  return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
  if request.method == 'POST':
    username = request.form['username']
    password = request.form['password']
    user = authenticate_user(username, password)
    if user:
      login_user(user)
      return redirect(url_for('home'))
    else:
      return '<h1>Invalid username or password</h1>'
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
  return redirect(url_for('login'))


if __name__ == '__main__':
  app.run(host='0.0.0.0', debug=True)
