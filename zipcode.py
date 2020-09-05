import sqlite3 as sql

class Zipcode:
    
    def __init__(self):
        self.conn = sql.connect("zipcodes/zipcodes.db")
        self.db = self.conn.cursor()

    def zip2geo(self, code):
        zip = code if len(code)<=5 else code[:5]
        self.db.execute("SELECT lat,long FROM zips WHERE zip=?", (zip,))
        return self.db.fetchone()