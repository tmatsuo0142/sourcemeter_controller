from flask import Flask, render_template, request, jsonify, Response
import pyvisa
from pyvisa.errors import VisaIOError
import time
from datetime import datetime
import sqlite3
import csv
import io
import random
import os
import json

app = Flask(__name__)

DATABASE = "database.db"

start_time = time.time()

keithley = None


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

#measurement functions
def measure_value():
    # Example: return instrument.read()
    if keithley == None:
        return 0
    else:
        keithley.write(":SENS:FUNC 'CURR'")
        keithley.write(":READ?")
        value = keithley.query(':MEAS:CURR?')
        return value
    

@app.route("/",  methods = ["GET", "POST"])
def index():
    try:
        rm = pyvisa.ResourceManager()
        list = rm.list_resources()
        if request.method == "POST":
            print(request.form.get("TCPIP"))
            TCPIP = request.form.get("TCPIP")
        
            keithley = rm.open_resource(f"{TCPIP}")
        
            current = float(request.form.get("current"))/1000
            keithley.write("SOUR:FUNC CURR")
            keithley.write(f"SOUR:CURR {current}")
            return render_template("index.html", TCPIP = TCPIP, list = list)
    
    
        return render_template("index.html", TCPIP = 0, list = "list should appear here after entering TCPIP")
    except VisaIOError:
        return render_template("index.html", TCPIP = 0, list = "Communication error")



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
        "current": current
    })

@app.route('/history')
def history():
    db = get_db()
    rows = db.execute("SELECT time, current FROM chart_data").fetchall()
    db.close()

    return jsonify([{"time": r["time"], "current": r["current"]} for r in rows])

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