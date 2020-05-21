import os

from flask import Flask, session, redirect, render_template, request, jsonify, flash
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

import requests
from loginredirect import login_required


from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)


# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
@login_required
def index():
    return render_template("index.html")

# _________________________________________________________________________________________________________________________________________________


@app.route("/login", methods=["GET", "POST"])
def login():

	# start fresh, no more user id
	session.clear()
	login_username = request.form.get("username")
	login_password = request.form.get("password")
	# if user has just registered an account
	if request.method == "POST":

		

		# make sure that the username field was filled in:
		if not login_username:
			return render_template("error.html", message="username field is empty")
		# make sure that the password field was filled in:
		
		elif not login_password:
			return render_template("error.html", message="password field is empty")


		# grab the user from the database:
		query_user = db.execute("SELECT * FROM users WHERE username = :login_username",
			{"login_username": login_username}).fetchone()

		# make sure that this username is registered:
		if query_user == None:
			return render_template("error.html", message="wrong user or non existent user")

		# make sure that passwords match up:
		if not check_password_hash(query_user.password, login_password):
			return render_template("error.html", message="incorrect password")

		# Remember logged in user
		session["user_id"] = query_user.id
		session["user_name"] = query_user.username

        # Redirect user to home page
		return redirect("/")

	# if the user is coming directly to the login
	# 	page through the specified URL 
	else:
		return render_template("login.html")

# _________________________________________________________________________________________________________________________________________________


@app.route("/register", methods=["GET","POST"])
def register():

	# if the user 
	if request.method == "POST":

		# POSSIBLE USERNAME ERRORS:
		registered_username = request.form.get("username")

		# check if a username was actually submitted:
		if not registered_username:
			return render_template("error.html", message="username field is empty")
		# check if the username is already taken:
		existing_user = db.execute("SELECT * FROM users WHERE username = :registered_username", 
			{"registered_username": registered_username}).fetchone()
		if not existing_user:

			# POSSIBLE PASSWORD ERRORS:
			registered_password = request.form.get("password")

			# check if a password was actually submitted
			if registered_password == None:
				return render_template("error.html", message="password field is empty")

			hashedpassword = generate_password_hash(registered_password, method='pbkdf2:sha256', salt_length=8)

			db.execute("INSERT INTO users (username, password) VALUES(:registered_username, :registered_password)",
				{"registered_username": registered_username, "registered_password": hashedpassword})

			db.commit()

			#flash("Your account has been created!", "info")

			return redirect("/login")

		# the username already exists
		else:
			return render_template("error.html", message="sorry this username is taken")

	else:
		return render_template("register.html")

# _________________________________________________________________________________________________________________________________________________
@app.route("/search", methods=["GET"])
@login_required
def search():

	user_search = request.args.get("book")

	if not user_search:
		return render_template("error.html", message="search field is empty")

	query_wildcard = "%" + user_search + "%"

	# ensures that words are capitalized, this is for matching titles and authors that are written in this format
	query_wildcard = query_wildcard.title()

	rows = db.execute("SELECT isbn, title, author, year from books WHERE \
	isbn LIKE :query OR title LIKE :query OR author LIKE :query", 
	{"query": query_wildcard})

	if rows.rowcount == 0:
		return render_template("error.html", message="sorry our database doesn't contain your book")

	result_books = rows.fetchall()

	return render_template("searchresults.html", result_books  = result_books)




# _________________________________________________________________________________________________________________________________________________
@app.route("/book/<isbn>", methods=["GET","POST"])
@login_required
def book(isbn):
	if request.method == "POST":

		username = session["user_name"]
		rating = request.form.get("rating")
		comment = request.form.get("comment")

		book_id = db.execute("SELECT id FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()[0]
		

		db.execute("INSERT INTO reviews (username, book_id, rating, comment) VALUES (:username, :book_id, :user_rating, :user_comment)",
			{"username": username, "book_id": book_id, "user_rating": rating, "user_comment": comment})
		db.commit()

		# flash("Your review has been submitted!")

		return redirect("/book/" + isbn)

	else:

		# info specific to the book being under review
		book_info = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchall()
		
		# getting id
		book_id = db.execute("SELECT id FROM books WHERE isbn = :isbn",
			{"isbn": isbn}).fetchone()[0]

		# goodreads info
		goodreads_key = os.getenv("GOODREADS_KEY")
		res = requests.get("https://www.goodreads.com/book/review_counts.json", 
			params={"key": goodreads_key, "isbns": isbn})

		# clean the api call
		res = res.json()
		# get the needed info
		res = res['books'][0]

		book_info.append(res)

		# creating reviews and returning them
		reviews = db.execute("SELECT username, rating, comment FROM reviews WHERE book_id = :book_id",
			{"book_id": book_id}).fetchall()

		return render_template("book.html", bookInfo=book_info, reviews=reviews)

# _________________________________________________________________________________________________________________________________________________


@app.route("/logout")
def logout():
	session.clear()
	return redirect("/")

# _________________________________________________________________________________________________________________________________________________

@app.route("/api/<isbn>", methods=["GET"])
def book_api(isbn):

	book = db.execute("SELECT * FROM books WHERE isbn = :isbn",
		{"isbn": isbn}).fetchone()

	if not book:
		return render_template("error.html", message="invalid isbn")


	goodreads_key = os.getenv("GOODREADS_KEY")
	res = requests.get("https://www.goodreads.com/book/review_counts.json", 
		params={"key": goodreads_key, "isbns": isbn})

	# clean the api call
	res = res.json()
	res = res['books'][0]

	'''<h5>Total Number of goodreads Ratings: {{bookInfo[1]['work_ratings_count']}}</h5>
            <h5>Average goodreads Rating: {{bookInfo[1]['average_rating']}}</h5>
    '''

	return jsonify ({
		"title": book.title,
		"author": book.author,
		"publication year": book.year,
		"number of ratings": res['work_ratings_count'],
		"rating": res['average_rating']	
		})








if __name__ == '__main__':
	app.run(debug=True)
