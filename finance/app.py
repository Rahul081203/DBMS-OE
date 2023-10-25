import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")
rows=db.execute("select cash from users where username='ABC'")
print(rows)

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/",methods=["GET","POST"])
@login_required
def index():
    """Show portfolio of stocks"""
    if request.method=="GET":
        return render_template("login.html")
    else:
        sum=0
        username=request.form.get("username")
        records=db.execute("SELECT * from shares where username=?",username)
        for record in records:
            sum+=float(record['cash'])
        return render_template("index.html",records=records,sum=sum)

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method=="GET":
        return render_template("buy.html")
    else:
        sum=0
        symbol=request.form.get("symbol")
        shares=request.form.get("shares")
        quote=lookup(symbol)
        username=request.form.get("username")
        password=request.form.get("password")
        rows=db.execute("SELECT * FROM users where username=?",username)
        if len(rows)!=1 or not check_password_hash(rows[0]["hash"], password):
            return apology("Invalid Credentials.")
        try:
            shares=int(shares)
        except:
            return apology("Please enter a valid number of shares")
        if shares <= 0:
            return apology("Please enter a valid number of shares")
        elif not quote:
            return apology("Not a valid symbol.")
        elif not username or not password:
            return apology("Must verify Credentials..", 500)

        else:
            record=db.execute("SELECT cash from users where username=?",username)
            cash=int(record[0]["cash"])
            cost=int(quote["price"]*shares)
            if cost > cash:
                return apology("Not enough cash.")
            else:
                cash=cash-cost
                db.execute("UPDATE users set cash=? where username=?",cash,username)
                share_record=db.execute("SELECT * FROM shares where username=? and symbol=?",username,symbol)
                if len(share_record)!=1:
                    db.execute("INSERT INTO shares(username,symbol,current_price,shares,cash) values (?,?,?,?,?)",username,symbol,quote["price"],shares,cash)
                else:
                    db.execute("UPDATE shares set shares=shares+?,cash=?,current_price=? where username=? and symbol=?",shares,cash,quote["price"],username,symbol)
                db.execute("UPDATE users set cash=? where username=?",cash,username)
                db.execute("UPDATE shares set cash=? where username=?",cash,username)
                db.execute("INSERT INTO transaction_details(username, type, symbol, quantity, Transaction_Date_time, price) values (?,'BUY',?,?,?,?)",username,symbol,shares,datetime.now(),cost)
                records=db.execute("SELECT * from shares where username=?",username)
                for record in records:
                    sum+=float(record['cash'])
                return render_template("index.html",records=records,sum=sum)

@app.route("/history",methods=["GET","POST"])
@login_required
def history():
    """Show history of transactions"""
    if request.method=="GET":
        return render_template("history_user.html")
    else:
        username=request.form.get("username")
        rows=db.execute("SELECT * FROM transaction_details where username=?",username)
        if len(rows)==0:
            return apology("No Record Found..")
        else:
            return render_template("history.html",records=rows)




@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"],request.form.get("password")):
            return apology("invalid username and/or password", 403)
        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        # Redirect user to home page
        records=db.execute("SELECT * FROM shares where username=?",request.form.get("username"))
        sum=0
        for record in records:
            sum+=float(record['cash'])
        return render_template("index.html",records=records,sum=sum)

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
@app.route("/add", methods=["GET", "POST"])
def add():
    """ Add Cash """
    if request.method=='GET':
        return render_template("add.html")
    else:
        sum=0
        username=request.form.get("username")
        if not (db.execute("SELECT * FROM users where username=?",username)):
            return apology("Not a valid Username")
        cash=request.form.get("add-bal")
        try:
            cash=int(cash)
        except:
            return apology("Must enter an integer..")
        if not cash:
            return apology('Must enter a valid amount of cash')
        else:
            db.execute("update users set cash = (cash + ?) where username=?",cash,username)
            db.execute("UPDATE shares set cash=(cash+?) where username=?",cash,username)
            db.execute("INSERT INTO transaction_details(username, type, Transaction_Date_time, price) values (?,'ADD CASH',?,?)",username,datetime.now(),cash)
            records=db.execute("SELECT * from shares where username=?",username)
            for record in records:
                sum+=float(record['cash'])
            return render_template("index.html",records=records,sum=sum)

@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method=='GET':
        return render_template("quote.html")
    else:
        symbol=request.form.get("symbol")
        if not symbol:
            return apology("Must Enter A Symbol",400)
        quote=lookup(symbol.upper())
        print(quote)
        if not quote:
            return apology("Symbol Doesn't Exist..",400)
        return render_template("quoted.html",name=quote["name"],price=quote["price"],symbol=quote["symbol"])


@app.route("/register", methods=['GET','POST'])
def register():

    if request.method=='GET':
        return render_template("register.html")
    else:
        temp=db.execute("SELECT * FROM users where username=?",request.form.get("username"))
        usernames=[]
        for row in temp:
            usernames+=[row['username']]
        if (not request.form.get("username")):
                return apology("Must provide Unique username", 400)
        elif(request.form.get("username") in usernames):
            return apology("Must provide Unique Username",400)
        elif not request.form.get("password"):
                return apology("Must provide password", 400)
        elif not request.form.get("confirmation"):
                return apology("Must re-enter password", 400)
        elif (request.form.get("password") == request.form.get("confirmation")):
            hash=generate_password_hash(request.form.get("password"), method='pbkdf2:sha256', salt_length=8)
            db.execute("INSERT INTO users(username,hash,cash) values (?,?,10000)",request.form.get("username"), hash)
            rows=db.execute("SELECT * FROM USERS")
            session["user_id"] = rows[0]["id"]
            records=db.execute("SELECT * from shares where username=?",request.form.get("username"))
            sum=0
            for record in records:
                sum+=float(record['cash'])
            return render_template("index.html",records=records,sum=sum)
        return apology("Password Not Match..", 400)

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method=="GET":
        return render_template("sell.html")
    else:
        symbol=request.form.get("symbol")
        shares=request.form.get("shares")
        username=request.form.get("username")
        password=request.form.get("password")
        quote=lookup(symbol)
        sum=0
        records=db.execute("SELECT * FROM shares where username=? and symbol=?",username,symbol)

        rows=db.execute("SELECT * FROM users where username=?",username)
        if len(rows)!=1 or not check_password_hash(rows[0]["hash"], password):
            return apology("Invalid Credentials.")


        try:
            shares=int(shares)
        except:
            return apology("Please enter a valid number of shares")
        if shares <= 0:
            return apology("Please enter a valid number of shares")
        elif not quote:
            return apology("Not a valid symbol.")
        elif not username or not password:
            return apology("Must verify Credentials..", 500)

        else:
            record=db.execute("SELECT cash from users where username=?",username)
            cash=int(record[0]["cash"])
            cost=int(quote["price"]*shares)
            cash=cash+cost
            record=db.execute("SELECT shares from shares where username=? and symbol=?",username,symbol)
            share_record=db.execute("SELECT * FROM shares where username=? and symbol=? and shares <= ?",username,symbol,int(record[0]['shares']))
            if len(share_record)==1:
                db.execute("UPDATE users set cash=? where username=?",cash,username)
                db.execute("UPDATE shares set cash=?, shares=shares-? and current_price=? where username=? and symbol=?",cash,shares,quote["price"],username,symbol)
                db.execute("UPDATE shares set cash=? where username=?",cash,username)
                db.execute("INSERT into transaction_details(username,type,symbol,quantity,Transaction_Date_time,price) values (?,'Sell',?,?,?,?)", username, symbol, shares, datetime.now(),cost)
                if len(db.execute("SELECT shares from shares where username=? and symbol=?",username,symbol)) == 0:
                    db.execute("delete from shares where username=? and symbol=?",username,symbol)
            else:
                return apology("You don't own these shares.")
            records=db.execute("SELECT * from shares where username=?",username)
            for record in records:
                sum+=float(record['cash'])
            return render_template("index.html",records=records,sum=sum)


