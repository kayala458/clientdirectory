import os
import csv

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash


from helpers import apology, login_required, number

# Configure application
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

# Custom filter
app.jinja_env.filters["number"] = number

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///directory.db")




@app.route("/login", methods=["GET", "POST"])
def user_access():
    """Logs user in or registers new user"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # If a returning user logging in
        if request.form['action'] == 'Log In':

            # Ensure username was submitted
            if not request.form.get("username"):
                return apology("Must provide username", 403)

            # Ensure password was submitted
            elif not request.form.get("password"):
                return apology("Must provide password", 403)

            # Query directory.db for username
            rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

            # Ensure username exists and password is correct
            if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
                return apology("Invalid username and/or password", 400)

            # Remember which user has logged in
            session["user_id"] = rows[0]["id"]

            # Redirect user to home page
            return redirect("/")

        # If a new user registering for first time:
        elif request.form['action'] == 'Register':

            # Ensure First and Last name were submitted
            if not request.form.get("firstname") or not request.form.get("lastname"):
                return apology("Must provide both first and last name", 400)

            # Ensure email address was submitted
            if not request.form.get("email"):
                return apology("Must provide email address", 400)

            #Ensure email address is from @cambridgeassociates.com
            email = request.form.get("email")
            if email.split('@')[1] != "cambridgeassociates.com":
                return apology("Must use a Cambridge Associates email address - for guests, please use guest@cambridgeassociates.com", 400)

            # Ensure username was submitted
            if not request.form.get("username"):
                return apology("Must provide username", 400)

            # Ensure password was submitted
            elif not request.form.get("password"):
                return apology("Must provide password", 400)

            # Ensure password confirmation was submitted
            elif not request.form.get("confirmation"):
                return apology("Must provide password confirmation", 400)

            # Check whether passwords match
            elif request.form.get("password") != request.form.get("confirmation"):
                return apology("Passwords do not match", 400)

            # Check whether username is already in users table in directory.db
            username = request.form.get("username")
            rows = db.execute("SELECT * FROM users WHERE username=:username", username=username)

            # If username is taken, return apology
            if len(rows) == 1:
                return apology("Username already exists", 400)

            # If username is not taken, add hash password and add user to users table in directory.db
            elif len(rows) == 0:
                hash = generate_password_hash(request.form.get("password"))
                first_name = request.form.get("firstname")
                last_name = request.form.get("lastname")
                db.execute("""INSERT INTO users (username, hash, first_name, last_name)
                              VALUES (:username, :hash, :first_name, :last_name)""", username=username, hash=hash, first_name=first_name, last_name=last_name)

                # Log user in
                rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))
                session["user_id"] = rows[0]["id"]

                # Re-direct user to log-in page
                return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/", methods=["GET", "POST"])
@login_required
def search():
    """Show Search Form and allow users to search by client name or client ID"""

    # User reached route via GET (as by clicking a link)
    if request.method == "GET":

        # Obtain user's first name for welcome message
        user = db.execute("SELECT first_name FROM users WHERE id = :id", id=session["user_id"])
        first = user[0]["first_name"]

        # Obtain number of active Optica Research users for Dashboard
        research = db.execute("SELECT COUNT(*) FROM user_subscriptions WHERE ors_private ='yes' OR ors_public='yes'")
        ORSusers = research[0]["COUNT(*)"]

        # Obtain number of acitve Optica Benchmarks users for Dashboard
        benchmarks = db.execute("SELECT COUNT(*) FROM user_subscriptions WHERE obm = 'yes'")
        OBMusers = benchmarks[0]["COUNT(*)"]

        # Obtain number of acitve Optica Peers users for Dashboard
        peers = db.execute("SELECT COUNT(*) FROM user_subscriptions WHERE opd = 'yes'")
        OPDusers = peers[0]["COUNT(*)"]

        # isHome prompts welcome message on navbar to populate; simple_search prompts "Search" in navbar to be highlighted as the active page
        return render_template("home.html", first=first, isHome =True, ORSusers=ORSusers, OBMusers=OBMusers, OPDusers=OPDusers, simple_search=True)

    # User submits form on Search/home page
    if request.method == "POST":

        # Obtain client name and/or client ID entered in form
        client_name = request.form.get("client_name")
        client_id = request.form.get("client_id")

        # Return apology if neither name nor id were entered
        if not client_name and not client_id:
            return apology("Must provide either client name or client ID", 400)

        # If both client ID and name were entered, check clients table for item that matches both client name and ID
        if client_id and client_name:
            client = db.execute("SELECT * FROM clients WHERE client_id = :client_id AND client_name LIKE :client_name", client_id=client_id, client_name = '%' + client_name + '%')

            # Return apology if name doesn't match client id
            if not client:
                return apology("Client name and Client ID do not match that of an existing client", 400)

            # If client name matches client ID, get list of users belonging to client
            else:
                client_name = client[0]["client_name"]
                client_id = client[0]["client_id"]
                users = db.execute("""SELECT user_name, email, start_date, website, answers, insights, market, obm, opd, ors_private, ors_public, pios, mmos
                                      FROM client_users JOIN user_subscriptions ON client_users.user_id = user_subscriptions.user_id
                                      WHERE client_id = :client_id""", client_id=client_id)

                # Replace "yes" in application columns with check mark
                for row in range(len(users)):
                    for field in users[row]:
                        users[row][field] = users[row][field].replace("yes", u"\u2713")

                # Produce search results. simple_search prompts "Search" in navbar to be highlighted as the active page
                return render_template("searchresult.html", client=client, client_name=client_name, client_id=client_id, users=users, simple_search=True)

        # If only name was entered, check clients table for client name
        if client_name:
            client = db.execute("SELECT * FROM clients WHERE client_name LIKE :client_name", client_name = '%' + client_name + '%')

            # Return apology if name doesn't match any existing clients
            if not client:
                return apology("Client name couldn't be located", 400)

            # If client search returns multiple matches, produce list of matching clients for user to choose from
            if len(client) > 1:
                return render_template("client-links.html", client=client, simple_search=True)

            # If client returns only one match, obtain list of users that belong to client
            else:
                client_name = client[0]["client_name"]
                client_id = client[0]["client_id"]
                users = db.execute("""SELECT user_name, email, start_date, website, answers, insights, market, obm, opd, ors_private, ors_public, pios, mmos
                                      FROM client_users
                                      JOIN user_subscriptions ON client_users.user_id = user_subscriptions.user_id
                                      WHERE client_id = :client_id""", client_id=client_id)

                # Replace "yes" in application columns with check mark
                for row in range(len(users)):
                    for field in users[row]:
                        users[row][field] = users[row][field].replace("yes", u"\u2713")

                # Produce search results. simple_search prompts "Search" in navbar to be highlighted as the active page
                return render_template("searchresult.html", client=client, client_name=client_name, client_id=client_id, users=users, simple_search=True)

        # If only client ID was entered, check clients table for client ID
        if client_id:
            client = db.execute("SELECT * FROM clients WHERE client_id = :client_id", client_id=client_id)

            # Return apology if ID doesn't match existing clients
            if not client:
                return apology("Client ID couldn't be located", 400)

            # If client returns only one match, get list of users belonging to client
            else:
                client_name = client[0]["client_name"]
                client_id = client[0]["client_id"]
                users = db.execute("""SELECT user_name, email, start_date, website, answers, insights, market, obm, opd, ors_private, ors_public, pios, mmos
                                      FROM client_users JOIN user_subscriptions ON client_users.user_id = user_subscriptions.user_id
                                      WHERE client_id = :client_id""", client_id=client_id)

                # Replace "yes" in application columns with check mark
                for row in range(len(users)):
                    for field in users[row]:
                        users[row][field] = users[row][field].replace("yes", u"\u2713")

                # Produce search results. simple_search prompts "Search" in navbar to be highlighted as the active page
                return render_template("searchresult.html", client=client, client_name=client_name, client_id=client_id, simple_search=True, users=users)


@app.route("/advanced", methods=["GET", "POST"])
@login_required
def advanced_search():
    """Show Advanced Search Form and allow users to obtain list of clients or list of users matching description"""

    # User reached route via GET (as by clicking a link)
    if request.method == "GET":

        # Obtain list of all client institution types and regions so as to populate dropdowns on form
        institutions = db.execute("SELECT institution FROM clients GROUP BY institution")
        region = db.execute("SELECT region FROM clients GROUP BY region")

        # Display advanced search form. advanced propmts "Advanced Search" to be highlighted in navbar as the active page
        return render_template("advanced.html", institutions=institutions, region=region, advanced=True)

    # User selects "search" button
    if request.method == "POST":

        # If users clicks "Search Clients", search clients tables for rows matching description
        if request.form['action'] == 'Search Clients':

            # Obtain the search criteria user entered
            institution = request.form.get("institution")
            region = request.form.get("region")

            # Return apology if neither search field was entered
            if not institution and not region:
                return apology("Must select either institution or region", 400)

            # If both fields entered, search clients table for items matching both descriptions (reg and inst refer to region and institution. These are used in advancedresults.html template)
            if institution and region:
                clients = db.execute("SELECT * FROM clients WHERE region = :region AND institution = :institution", region=region, institution=institution)

                # advanced propmts "Advanced Search" to be highlighted in navbar as the active page
                return render_template("advancedresults.html", clients=clients, institution=institution, region=region, reg=True, inst=True, advanced=True)

            # If only institution type was entered, search for clients with that institution type
            if institution:
                clients = db.execute("SELECT * FROM clients WHERE institution = :institution", institution=institution)

                # advanced propmts "Advanced Search" to be highlighted in navbar as the active page
                return render_template("advancedresults.html", clients=clients, institution=institution, inst=True, advanced=True)

            # If only region was entered, search for clients with that region tag
            if region:
                clients = db.execute("SELECT * FROM clients WHERE region = :region", region=region)

                # advanced propmts "Advanced Search" to be highlighted in navbar as the active page
                return render_template("advancedresults.html", clients=clients, region=region, reg=True, advanced=True)

        # If user clicks "Search Users", search user and user_subscription tables for items matching description
        if request.form['action'] == 'Search Users':

            # Obtain the search criteria user entered
            institution = request.form.get("institution")
            region = request.form.get("region")

            # Return apology if neither search field was entered
            if not institution and not region:
                return apology("Must select either institution or region", 400)

            # If both fields were entered, search for users that belong to organizations with that region and institution type, obtain thier list of subscriptions
            if institution and region:
                users = db.execute("""SELECT user_name, email, start_date, website, answers, insights, market, obm, opd, ors_private, ors_public, pios, mmos
                                      FROM clients JOIN client_users ON clients.client_id = client_users.client_id
                                      JOIN user_subscriptions ON client_users.user_id = user_subscriptions.user_id
                                      WHERE institution = :institution AND region=:region ORDER BY user_name ASC""", institution=institution, region=region)

                # Replace "yes" in application columns with check mark
                for row in range(len(users)):
                    for field in users[row]:
                        users[row][field] = users[row][field].replace("yes", u"\u2713")

                # Produce search results. "inst" and "reg" prompt searchreult to populate with the appropriate text in header
                # advanced prompts "Advanced Search" in navbar to be highlighted as the active page
                return render_template("searchresult.html", region=region, users=users, reg=True, institution=institution, inst=True, advanced=True)

            # If only institution type was entered, search for users that belong to organizations with that institution type
            if institution:
                users = db.execute("""SELECT user_name, email, start_date, website, answers, insights, market, obm, opd, ors_private, ors_public, pios, mmos
                                      FROM clients JOIN client_users ON clients.client_id = client_users.client_id
                                      JOIN user_subscriptions ON client_users.user_id = user_subscriptions.user_id
                                      WHERE institution = :institution ORDER BY user_name ASC""", institution=institution)

                # Replace "yes" in application columns with check mark
                for row in range(len(users)):
                    for field in users[row]:
                        users[row][field] = users[row][field].replace("yes", u"\u2713")

                # Produce search results. advanced prompts "Advanced Search" in navbar to be highlighted as the active page
                return render_template("searchresult.html", institution=institution, users=users, inst=True, advanced=True)

            # If only region was entered, search for users that belong to organizations in that region
            if region:
                users = db.execute("""SELECT user_name, email, start_date, website, answers, insights, market, obm, opd, ors_private, ors_public, pios, mmos
                                      FROM clients JOIN client_users ON clients.client_id = client_users.client_id
                                      JOIN user_subscriptions ON client_users.user_id = user_subscriptions.user_id
                                      WHERE region = :region ORDER BY user_name ASC""", region=region)

                # Replace "yes" in application columns with check mark
                for row in range(len(users)):
                    for field in users[row]:
                        users[row][field] = users[row][field].replace("yes", u"\u2713")

                # Produce search results. advanced prompts "Advanced Search" in navbar to be highlighted as the active page
                return render_template("searchresult.html", region=region, users=users, reg=True, advanced=True)


@app.route("/clients")
@login_required
def clients():
    """Show list of all current client organizations"""

    # Obtain All client information
    clients = db.execute("SELECT * FROM clients")

    return render_template("clients.html", clients = clients)


@app.route("/searchresult")
@login_required
def linked_client():
    """Show list of users that have access that belong to client that user clicks on"""

    # User clicked on link where type corresponds to that client's Client ID. Obtain client ID
    client_id = request.args.get('type')

    # Obtain all client data for client matching that client ID
    client = db.execute("SELECT * FROM clients WHERE client_id = :client_id", client_id=client_id)
    client_name = client[0]["client_name"]

    # Get list of users that belong to that client and what applicaitons they have access to
    users = db.execute("""SELECT user_name, email, start_date, website, answers, insights, market, obm, opd, ors_private, ors_public, pios, mmos
                          FROM client_users JOIN user_subscriptions ON client_users.user_id = user_subscriptions.user_id
                          WHERE client_id = :client_id""", client_id=client_id)

    # Replace "yes" in application columns with check mark
    for row in range(len(users)):
        for field in users[row]:
            users[row][field] = users[row][field].replace("yes", u"\u2713")

    return render_template("searchresult.html", client=client, client_name=client_name, client_id=client_id, users=users, simple_search=True)


@app.route("/users")
@login_required
def users():
    """Show list of users that have access to one of three main applications"""

    # User clicked on link where type corresponds application. Get application name
    selected_application = request.args.get('type')

    # If user selected Optica Research, obtain list of all users with access to Optica Research
    if selected_application == "research":
        users = db.execute("""SELECT user_name, email, start_date, clients.client_id, client_name, institution, region
                              FROM user_subscriptions JOIN client_users ON user_subscriptions.user_id = client_users.user_id
                              JOIN clients ON client_users.client_id = clients.client_id
                              WHERE ors_private ='yes' OR ors_public='yes' ORDER BY client_name, user_name ASC""")
        application = "Optica Research"

    # If user selected Optica Benchmarks, obtain list of all users with access to Optica Benchmarks
    if selected_application == "obm":
        users = db.execute("""SELECT user_name, email, start_date, clients.client_id, client_name, institution, region
                              FROM user_subscriptions JOIN client_users ON user_subscriptions.user_id = client_users.user_id
                              JOIN clients ON client_users.client_id = clients.client_id
                              WHERE obm = 'yes' ORDER BY client_name, user_name ASC""")
        application = "Optica Benchmarks"

    # If user selected Optica Peers, obtain list of all users with access to Optica Peers
    if selected_application == "opd":
        users = db.execute("""SELECT user_name, email, start_date, clients.client_id, client_name, institution, region
                              FROM user_subscriptions JOIN client_users ON user_subscriptions.user_id = client_users.user_id
                              JOIN clients ON client_users.client_id = clients.client_id WHERE opd = 'yes'
                              ORDER BY client_name, user_name ASC""")
        application = "Optica Peers"

    return render_template("users.html", users=users, application=application)


@app.route("/legend")
@login_required
def legend():
    """Show list of applications and what they do"""

    return render_template("legend.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
