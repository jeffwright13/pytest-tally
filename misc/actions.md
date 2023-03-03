## Actions (or, what I did to get this thing off the ground) ##

## PDM ##
- pdm plugin add pdm-vscode
- pdm init

## Design Requirements ##
- a text-based widget/dashboard/tui that can sit in the console while Pytest is running and display the running tally of tests in this suite
- the widget should be able to be used in a terminal (multiple, see Terminal support below); in a VSCode terminal; in a PyCharm terminal
- the widget should (as a POC) be able to show the folling dynamically:
  - P / F / Skip / XFail / XPass / Rerun / Error / Warning

### Terminal Support ###
- iTerm2
- Terminal.app
- Windows Terminal
- kitty
- alacritty
- xterm
- TeraTerm
- PuTTy
