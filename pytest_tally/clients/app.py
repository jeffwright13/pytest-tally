import argparse
import json
import logging
import os

from flask import Flask, jsonify, render_template

app = Flask(__name__)

# Global variables
results = None
fetch_rate = 10  # Default fetch rate in seconds


def read_json_file(file_path):
    global results
    with open(file_path) as file:
        results = json.load(file)


@app.route("/")
def index():
    read_json_file(app.config["JSON_FILE_PATH"])
    return render_template("index.html", results=results, fetch_rate=fetch_rate)


@app.route("/results")
def get_results():
    read_json_file(app.config["JSON_FILE_PATH"])
    return jsonify(results)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Flask app with customizable JSON file path and debug mode."
    )
    parser.add_argument(
        "json_file", metavar="JSON_FILE", type=str, help="path to the JSON file"
    )
    parser.add_argument(
        "--port",
        metavar="PORT",
        type=int,
        default=8080,
        help="listening port for the app",
    )
    parser.add_argument("--debug", action="store_true", help="enable debug mode")
    parser.add_argument(
        "--log-level",
        metavar="LOG_LEVEL",
        type=str,
        default="ERROR",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="log level for Werkzeug",
    )
    parser.add_argument(
        "--fetch-rate",
        metavar="FETCH_RATE",
        type=int,
        default=2000,
        help="fetch rate (in ms) - effectively the update rate of the web app",
    )
    return parser.parse_args()


def configure_logging(log_level):
    log = logging.getLogger("werkzeug")
    log.setLevel(getattr(logging, log_level))


def main():
    default_json_file = os.path.join(os.getcwd(), "tally-data.json")

    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Flask app with customizable JSON file path and debug mode."
    )
    parser.add_argument(
        "json_file",
        metavar="JSON_FILE",
        type=str,
        nargs="?",
        default=default_json_file,
        help="path to the JSON file (default: %(default)s)",
    )
    parser.add_argument(
        "--port",
        metavar="PORT",
        type=int,
        default=8080,
        help="listening port for the app",
    )
    parser.add_argument("--debug", action="store_true", help="enable debug mode")
    parser.add_argument(
        "--log-level",
        metavar="LOG_LEVEL",
        type=str,
        default="ERROR",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="log level for Werkzeug",
    )
    parser.add_argument(
        "--fetch-rate",
        metavar="FETCH_RATE",
        type=int,
        default=2000,
        help="fetch rate (in ms) - effectively the update rate of the web app",
    )
    args = parser.parse_args()

    # Configure and run the Flask app
    app.config["JSON_FILE_PATH"] = args.json_file
    fetch_rate = args.fetch_rate
    print(fetch_rate)  # Keeping Flake8 happy for now
    configure_logging(args.log_level)
    print(f"Starting flask app with parameters: {args}")
    app.run(debug=args.debug, port=args.port)


if __name__ == "__main__":
    main()
