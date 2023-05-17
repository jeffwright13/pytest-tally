import json
import time

from flask import Flask, jsonify, render_template

app = Flask(__name__)

# Global variables
json_file_path = "/Users/jwr003/coding/pytest-tally/tally-data.json"
results = None


def read_json_file():
    global results
    with open(json_file_path) as file:
        results = json.load(file)


@app.route("/")
def index():
    read_json_file()
    return render_template("index.html", results=results)


@app.route("/results")
def get_results():
    read_json_file()
    return jsonify(results)


if __name__ == "__main__":
    app.run(debug=True, port=8080)
