from flask import Flask, render_template, request, jsonify, Response
import pyvisa
import pymeasure
from pymeasure.instruments.keithley import Keithley2400 as K2400
from pymeasure.instruments.keithley import Keithley2450 as K2450
import time
import random
from datetime import datetime
import sqlite3
import csv
import io
import os

app = Flask(__name__)

DATABASE = "database.db"

start_time = time.time()

#database helper functions
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = sqlite3.connect(DATABASE)
    cursor = db.cursor()
    db.execute("DROP TABLE IF EXISTS chart_data")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chart_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time FLOAT NOT NULL,
            current FLOAT NOT NULL
        )
    """)

    db.commit()
    db.close()

init_db()

#update this with measurement command for Keithley
def measure_value():
    # Example: return instrument.read()
    #keithley.write(":SENS:FUNC 'CURR'")
    #keithley.write(":READ?")
    value = random.uniform(0,1)
    return value

@app.route("/",  methods = ["GET", "POST"])
def index():
    rm = pyvisa.ResourceManager()
    list = rm.list_resources()
    if request.method == "POST":
        print(request.form.get("TCPIP"))
        TCPIP = int(request.form.get("TCPIP"))
        
        keithley = rm.open_resource(f"{TCPIP}")
        
        current = float(request.form.get("current"))/1000
        keithley.write("SOUR:FUNC CURR")
        keithley.write(f"SOUR:CURR {current}")
        return render_template("index.html", TCPIP = TCPIP, list = list)
    return render_template("index.html", TCPIP = 1, list = list)


@app.route("/data")
def data():
    current_time = time.time()-start_time
    current = measure_value()

    #update db
    db = get_db()
    db.execute("INSERT INTO chart_data (time, current) VALUES (?, ?)", (current_time, current,))
    db.commit()
    db.close()
    
    #update chart
    return jsonify({
        "time": current_time,
        "value": current
    })

@app.route("/save")
def save():
    conn = get_db()
    cursor = conn.cursor()
    
    # Fetch data from the table
    cursor.execute("SELECT * FROM chart_data")
    rows = cursor.fetchall()
    conn.close()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header row
    writer.writerow(rows[0].keys() if rows else ["time", "current"])

    # Write data rows
    for row in rows:
        writer.writerow([row["id"], row["time"], row["current"]])

    output.seek(0)

    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=chart_data.csv"}
    )

if __name__ == "__main__":
    app.run(debug=True)