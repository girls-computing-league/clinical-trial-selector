import sqlite3 as sql

class Zipcode:
    
    def __init__(self):
        self.conn = sql.connect("zipcodes/zipcodes.db")
        self.db = self.conn.cursor()

    def zip2geo(self, code):
        self.db.execute("SELECT lat,long FROM zips WHERE zip=?", (code,))
        return self.db.fetchone()