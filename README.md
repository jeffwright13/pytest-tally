# pytest-tally

### A Pytest plugin that displays test run progress in-console. ###

![2023-03-10 14 16 57](https://user-images.githubusercontent.com/4308435/224430560-04f9de9e-2446-4a78-afb6-5f5f4bbfb05c.gif)


## Why?
I run a lot of long-duration test campaigns that generate copious amounts of console output. I usually monitor their progress by periodically checking the terminal to see if anything has failed so far. This usually means scrolling back in the console, looking for that telltale FAILED indication. It can be a bit of a pain hunting for that information!

This plugin writes up-to-date summary statistics for each test, as it executes, to a file on disk. That file is then continually read by a small client that prints its results to terminal. That way I can split my screen and monitor both the raw console output from Pytest and the client's summary output. And suddenly life becaomes just a little bit brighter. :-)

## Install ##
    pip install pytest-tally

## Use ##
- Run Pytest like you normally would, but specify the `--tally` option: `pytest --tally`
- Open another terminal session, activate your venv, and type in `tally` to start the client.
    - Ctrl-C exits the client (for now - improvements coming)
    - '-h' flag generates help
    - '-n' flag disables deletion of previous data when starting client
    - '-r' flag sets max number of rows to display on terminal
