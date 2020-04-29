import os

from flask import Flask, session, render_template, jsonify, request, redirect, flash
from models import *
from flask_session import Session
from sqlalchemy import create_engine
from tempfile import mkdtemp
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import login_required, lookup, to_int


app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        #check text filled
        if not request.form.get("searchtext"):
            return render_template("message.html", header = "Error", message="must provide text")
        # get object: isbn, author or title
        else:
            object = request.form.get("object")
            searchtexttemp =  request.form.get("searchtext")
            searchtext = "%"+searchtexttemp+"%"

            if object == "ISBN":
                rows = db.execute("SELECT * FROM books WHERE isbn ILIKE :searchtext", {"searchtext": searchtext}).fetchall()

            elif object == "Title":
                rows = db.execute("SELECT * FROM books WHERE title ILIKE :searchtext", {"searchtext": searchtext}).fetchall()

            else:  #search for author
                rows = db.execute("SELECT * FROM books WHERE author ILIKE :searchtext", {"searchtext": searchtext}).fetchall()

            if not rows:
                return render_template("message.html", header = "Sorry", message="no results")
            else:
                return render_template("results.html", rows=rows)
    # User reached route via GET
    else:
        return render_template("index.html")


@app.route("/book/<int:book_id>", methods=["GET", "POST"])
@login_required
def book(book_id):
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        #check text filled
        if not request.form.get("review_text"):
            return render_template("message.html", header = "Error", message="must provide text")
        #check rating filled
        if not request.form.get("stars"):
            return render_template("message.html", header = "Error", message="must provide score")
        user_id = int(session["user_id"])
        book_id = book_id
        starstext = request.form.get("stars")
        stars = to_int(starstext)
        review_text = request.form.get("review_text")

        #check if user already reviewed this book
        if db.execute("SELECT * FROM reviews WHERE user_id = :user_id AND book_id = :book_id",
                          {"user_id": user_id, "book_id": book_id}).rowcount > 0:
            return render_template("message.html", header = "Sorry", message="you already reviewed this book")
        else:
            db.execute("INSERT INTO reviews (user_id, book_id, stars, review_text) VALUES (:user_id, :book_id, :stars, :review_text)",
                          {"user_id": user_id, "book_id": book_id, "stars": stars, "review_text": review_text })
            db.commit()
            return render_template("message.html", header = "Succes", message="your review is added")


    # User reached route via GET
    else:
        # get book info
        book = db.execute("SELECT * FROM books WHERE id = :id", {"id": book_id}).fetchone()
        if book is None:
            return render_template("message.html", header = "Error", message="book not found")
        # get goodread info
        isbn = book.isbn
        print(isbn)
        dictgr = lookup(isbn)
        ratings_count = dictgr["ratings_count"]
        rating = dictgr["rating"]

        #get reviews
        rows = db.execute("SELECT review_text FROM reviews WHERE book_id = :book_id",
                              {"book_id": book_id}).fetchall()

        return render_template("book.html", book=book, rows=rows, ratings_count=ratings_count, rating=rating)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return render_template("message.html", header = "Error", message="must provide username")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return render_template("message.html", header = "Error", message="must provide password")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                  {"username": request.form.get("username")}).fetchall()

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return render_template("message.html", header = "Error", message="Invalid username and/or password")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return render_template("message.html", header = "Error", message="must provide new username")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return render_template("message.html", header = "Error", message="must provide new password")

        # Ensure password check was submitted
        elif not request.form.get("password-check"):
            return render_template("message.html", header = "Error", message="must provide same password again")

        # Ensure password is equal to  password-check
        elif request.form.get("password") != request.form.get("password-check"):
            return render_template("message.html", header = "Error", message="password check should be equal to password")

        # Query database for username to check if it is not already in use
        username = request.form.get("username")
        if db.execute("SELECT * FROM users WHERE username = :username",
                          {"username": username}).rowcount > 0:
            return render_template("message.html", header = "Error", message="username already in use")

        # Generate hash from password
        hash = generate_password_hash(request.form.get("password"))
        db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)", {"username": username, "hash": hash})
        db.commit()

        # Get id
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          {"username": username}).fetchall()

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        flash("Registered!")
        return redirect("/")

    # User reached route via GET
    else:
        return render_template("register.html")

@app.route("/api/<isbn>")
def book_api(isbn):
    """Return details about a book."""

  # Make sure book exists and select attributes.

    book = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()

    if book is None:
        return jsonify({"error": "Invalid flight_id"}), 404

    book_id = book.id

    # select reviews
    data = db.execute("SELECT AVG(stars) as average, COUNT(stars) as countstars FROM reviews WHERE book_id = :book_id", {"book_id": book_id}).fetchone()

    return jsonify({
        "title": book.title,
        "author": book.author,
        "year": book.year,
        "isbn": book.isbn,
        "review_count": data.countstars,
        "average_score": float(data.average)
     })
