# Example file of what was used to import csv files into my database

import csv
import sys
from cs50 import SQL

# Open file for SQLite
db = SQL("sqlite:///students.db")

# Open CSV file
with open("clients.csv", "r") as characters:

    # Create DictReader
    reader =csv.DictReader(characters)

    # Iterate over CSV file
    for row in reader:

        client_id = row["client_id"]
        client_name = row["client_name"]
        director = row["investment_director"]
        institution = row["institution_type"]
        city = row["city"]
        state = row["state"]
        country = row["country"]
        region = row["region"]
        assets = row["assets"]
        security = row["security"]

        # Insert student information
        db.execute("INSERT INTO students (client_id, client_name, director, institution, city, state, country, region, assets, security) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", client_id, client_name, director, institution, city, state, country, region, assets, security)