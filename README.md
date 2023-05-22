# pytest-tally

### A Pytest plugin that displays test run progress in-console, in-app or in-browser.

## Using Rich:
![2023-04-14 18 34 48](https://user-images.githubusercontent.com/4308435/232174467-752c5d13-15e3-4c23-9430-1087050af0a4.gif)

## Using Tkinter:
![2023-05-21 23 33 27](https://github.com/jeffwright13/pytest-tally/assets/4308435/7bb98b54-f796-4249-81d0-f2c283a7c6a3)

## Using Flask:
![2023-05-17 15 15 02](https://github.com/jeffwright13/pytest-tally/assets/4308435/a35151e2-64fe-40e2-bd2e-9a59033edcd3)


## Why?
I run a lot of long-duration test campaigns that generate copious amounts of console output. I usually monitor their progress by periodically checking the terminal to see if anything has failed so far. This usually means scrolling back in the console, looking for that telltale FAILED indication. It can be a bit of a pain hunting for that information!

This plugin writes up-to-date summary statistics for each test, as it executes, to a JSON file on disk. That file is then continually read by a small client that prints results to terminal or in-browser. That way I can split my screen and monitor both the raw console output from Pytest, and the client's summary output, at the same time. Mmmm. Life suddenly just became a little easier and brighter. :-)

## Also - why??

Because I'm a geek and I like learning new stuff about Python. This project made me learn about realtime file syncing, different ways of presenting data, how to get ChatGpt to write stuff for you, and a lot more!

## Install
For most users: `pip install pytest-tally`
For users who like to 'roll their own': `pip install -r requirements/requirements.txt && pip install pytest-tally`
For power users who want the dev dependencies: `pip install -r requirements/requirements-dev.txt && pip install pytest-tally`

## Usage

There are three clients included in this repo:
- Rich text-based client that runs in the terminal
- HTML client that runs in the browser (via a Flask web-app)
- TkInter GUI

Each of these has known issues (see below), but are functional. You are welcome to improve upon any of these, or write your own and submit a PR if you like.

To use text-based Rich client to display test results in-console as the tests run, open another terminal session, activate your venv, and type in `tally` to start the text-based client. Press the "q" key to quit the text-based client.

To use web-app Flask/HTML client to display test results in-browser as the tests run, open another terminal session, activate your venv, and type in `python pytest_tally/clients/app.py [-h] [--port PORT] JSON_FILE_PATH` to start the Flask web-app.

Now, simply run Pytest like you normally would, but specify the `--tally` option: `pytest --tally`. This starts the Pytest run and populates the tally-data.json file with the information needed by the client to show the updateded test status as it occurs.


### Pytest Plugin:
The pytest plugin adds the option `--tally`, and when invoked in that fashion, it generates a JSON file to disk that contains the updated test stats that are then used by one of the clients to display progress. The file is called "tally-data.json", and will be written to the current running directory.

    pytest tally:
    --tally                   Enable the pytest-tally plugin. Writes live summary results
                              data to a JSON file for consumption by a dashboard client.

### Rich (text-based) Client:

    usage: tally-rich [-h] [-v] [-l] [-x MAX_ROWS] [-f FILE_PATH] [filename]

    options:
    -h, --help            show this help message and exit
    -v, --version         show program's version number and exit
    -l, --lines           draw separation [l]ines in between each table row (default: False)
    -x MAX_ROWS, --max_rows MAX_ROWS
                            ma[x] number of rows to display (default: 0 [no limit])

_Limitations_
- Non-default JSON file support not working.

### Flask (web-app) Client:

    usage: tally-flask [-h] [--port PORT] [--debug] [--log-level LOG_LEVEL] [--fetch-rate FETCH_RATE] [JSON_FILE]

    positional arguments:
    JSON_FILE             path to the JSON file (default: /Users/jwr003/coding/pytest-tally/tally-data.json)

    options:
    -h, --help            show this help message and exit
    --port PORT           listening port for the app
    --debug               enable debug mode
    --log-level LOG_LEVEL
                            log level for Werkzeug
    --fetch-rate FETCH_RATE
                            fetch rate (in ms) - effectively the update rate of the web app

_Limitations_
- Non-default JSON file support not working.

### TkInter (GUI) Client:

    usage: tally-tk


_Limitations_
- Non-default JSON file support not working.
- No command line options. The intent is to provide all configuration through the app itself, but so far none are implemented.
