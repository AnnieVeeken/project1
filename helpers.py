import os
import requests
import urllib.parse

from flask import redirect, render_template, request, session
from functools import wraps


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(isbn):
    """Look up info for isbn."""

    # Contact API
    try:
        KEY = "ldtd3BmrpKdVBPnYoSxQ"
        #https://www.goodreads.com/book/review_counts.json?key={apikey}&isbns=9789082425406
        #response = requests.get("https://www.goodreads.com/book/review_counts.json?key=ldtd3BmrpKdVBPnYoSxQ&isbns=1594633665")
        KEY="ldtd3BmrpKdVBPnYoSxQ"
        response = requests.get("https://www.goodreads.com/book/review_counts.json",params={"key":KEY, "isbns":isbn})
        #response = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": KEY, "isbns": isbn})
        print(response)
        #response = requests.get(f"https://cloud-sse.iexapis.com/stable/stock/{urllib.parse.quote_plus(symbol)}/quote?token={api_key}")
        response.raise_for_status()
    except requests.RequestException:
        print("RequestException")
        return None

    # Parse response
    try:
        books = response.json()
        return {
            "ratings_count": books["books"][0]["work_ratings_count"],
            "rating": books["books"][0]["average_rating"]
        }
    except (KeyError, TypeError, ValueError):
        return None

def to_int(stars):
    switcher={
        'one':1,
        'two':2,
        'three':3,
        'four':4,
        'five':5
    }
    return switcher.get(stars)
