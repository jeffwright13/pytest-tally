# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project tries to adhere to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 1.2.0 - 2023-05-20
- Added web app support via Flask
- Fixed broekn'ds Rich app

## [1.1.1] 2023-04-14
- Implemented file-lock on shared JSON file to fix client stuttering issue.
- Added support for CLI option '-l' (lines -separators).
- Added threading to support new client runtime-keypress ("q" for Quit).

## [1.1.0] 2023-04-10
- New Rich client option "-f" for fixed-width output.
- Argprse for Rich client.
- User can now specify name/location of JSON file.

## [1.0.0] 2023-03-12
- Complete rewrite of outcome processing logic to definitively determine the outcome of a test.
- Added support for CLI option '-n' (do not delete existing data file).
- Added support for CLI option '-r' (max num rows to display on terminal).

## [0.1.2] 2023-03-07
- Added spinner to last test in dashboard table.

## [0.1.1] 2023-03-06
- Fixed Rich dashboard issue with not properly showing final outcome.
- Fixed Rich dashboard issue with not updating total timer for caption.
- Cleaned up plugin Rich dashboard code.

## [0.1.0] 2023-03-05
- Initial release with support for Rich dashboard.
