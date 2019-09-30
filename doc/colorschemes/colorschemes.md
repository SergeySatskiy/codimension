Codimension Color Schemes
=========================

Introduction
------------
Codimension uses skins to define how certain elements of the user interface
will look like. A skin is a set of files which reside in a designated directory.
The files are:
- app.css: application style sheet
- skin.json: general settings
- cflow.json: control flow diagram settings

The app.css follows the
[QT library application css spec](https://doc.qt.io/qt-5/stylesheet.html).

The skin.json and cflow.json files use the JSON format. Basically these are
dictionaries to store various settings. The keys in dictionaries are case
sensitive strings.

When Codimension starts it looks for the available skins in the
```
~/.codimension3/skins/
```
Codimension expects that for each skin there will be a directory with the
mentioned above files. At least one directory must exist and Codimension
takes care of the one called `default`.

At the first start Codimension creates the `~/.codimension3/skins/default`
directory and populates the necessary files. If at some point an error
is found in the default skin then the files will be overwritten automatically
with the values Codimension can work with.

Creating New Skin
-----------------
One of the options is to follow these steps:
- create a new directory for the new skin, e.g. `~/.codimension3/skins/myskin`
- copy skin.json, cflow.json and app.css from
  `~/.codimension3/skins/default` to `~/.codimension3/skins/myskin`
- open `~/.codimension3/skins/myskin/skin.json` and update the "name" value to
  the appropriate one, e.g. "My new skin". Next time Codimension starts the
  main menu will have `Options -> Themes -> My new skin` option. If the option
  is selected Codimension will use the settings from the newly created directory.

Now the values in the skin files can be safely changed. When the changes are made
the IDE needs to be restarted because the files are read at the start only.

Color and Font Formats
----------------------
The skin.json and cflow.json let to configure fonts and colors for many items.
The color format is a string with four comma separated values. Each value is from
0 to 255 and describes red, green, blue and alpha components of the color.
Here is an example: "208,208,208,255"

The font format is a string which QT library provides as the
[QFont.toString()](https://doc.qt.io/qt-5/qfont.html#toString) return value.
Here is an example: "Iosevka Term SS01,12,-1,5,50,0,0,0,0,0"


skin.json
---------
Here is a description of the settings stored in skin.json

| Name                          | Value |
|:------------------------------|:------|
| name                          | The name of the skin as it appears in UI |
| marginPaper                   | The line number margin background color in editing mode |
| marginPaperDebug              | The line number margin background color in debug mode |
| marginColor                   | The line number margin foreground color in editing mode |
| marginColorDebug              | The line number margin foreground color in debug mode |
| flakesMarginPaper             | The pyflakes margin background color |
| flakesMarginPaperDebug        | The pyflakes margin foreground color |
| bpointsMarginPaper            | The breakpoints margin background color |
| findNoMatchPaper              | The find term edit box background color when there are no matches |
| findMatchPaper                | The find term edit box background color when there are matches |
| findInvalidPaper              | The find term edit box background color when the search regexp is invalid |
| lineNumFont                   | The line number margin font for zoom level 0 |
| searchMarkColor               | The foreground color of the search matches in the text editor |
| searchMarkPaper               | The background color of the search matches in the text editor |
| matchMarkColor                | The foreground color of the current search match in the text editor |
| matchMarkPaper                | The background color of the current search match in the text editor |
| nolexerPaper                  | The text editor background color |
| nolexerColor                  | The text editor foreground color |
| monoFont                      | The font used in the text editor for zoom level 0 |
| currentLinePaper              | The text editor current line background color |
| edgeColor                     | The text editor vertical edge color |
| matchedBracePaper             | The text editor matched brace background color |
| matchedBraceColor             | The text editor matched brace foreground color |
| unmatchedBracePaper           | The text editor not matched brace background color |
| unmatchedBraceColor           | The text editor not matched brace foreground color |
| indentGuidePaper              | The text editor indent guide background color |
| indentGuideColor              | The text editor indent guide foreground color |
| debugCurrentLineMarkerPaper   | The text editor current debug line background color |
| debugCurrentLineMarkerColor   | The text editor current debug line foreground color |
| debugExcptLineMarkerPaper     | The text editor exception line background color |
| debugExcptLineMarkerColor     | The text editor exception line foreground color |
| calltipPaper                  | The text editor calltip background color |
| calltipColor                  | The text editor calltip foreground color |
| calltipHighColor              | The text editor current calltip parameter foreground color |
| outdatedOutlineColor          | The file outline window header background color if the file is syntactically incorrect |
| ioconsolePaper                | The I/O console background color |
| ioconsoleColor                | The I/O console foreground color |
| ioconsoleMarginStdoutColor    | The I/O console margin background color for the lines on the standard output |
| ioconsoleMarginStdinColor     | The I/O console margin background color for the lines on the standard input |
| ioconsoleMarginStderrColor    | The I/O console margin background color for the lines on the standard error |
| ioconsoleMarginIDEMsgColor    | The I/O console margin background color for the lines with the IDE messages |
| invalidInputPaper             | The background color of the input fields if the current input is invalid |




cflow.json
----------
Here is a description of the settings stored in cflow.json

| Name                          | Value |
|:--------------------------|:------|
| cfMonoFont                | The primitive's text font for zoom level 0 |
| badgeFont                 | The badge font for zoom level 0 |
| hCellPadding              | The horizontal cell padding (between primitives) |
| vCellPadding              | The vertical cell padding (between primitives) |
| hTextPadding              | The primitive's text horizontal text padding |
| vTextPadding              | The primitive's text vertical text padding |
| vHiddenTextPadding        | The scope side hidden comment primitive vertical text padding |
| hHiddenTextPadding        | The scope side hidden comment primitive horizontal text padding |
| hHeaderPadding            | The scope primitive header horizontal padding |
| vHeaderPadding            | The scope primitive header vertical padding |
| vSpacer                   | The height of the vertical spacer |
| rectRadius                | The scope primitive rounded rectangle radius |
| returnRectRadius          | The return primitive rounded rectangle radius |
| minWidth                  | The minimum width of a primitive |
| ifWidth                   | The if primitive width of the side corner |
| commentCorner             | The comment primitive upper right corner folding width/height |
| lineWidth                 | The connector primitive line width |
| lineColor                 | The connector primitive line color |
| selectColor               | The selected primitive outline color |
| selectPenWidth            | The selected primitive outline width |
| boxBGColor                | The code block primitive background color |
| boxFGColor                | The code block primitive foreground color |
| badgeBGColor              | The scope badge primitive background color |
| badgeFGColor              | The scope badge primitive foreground color |
| badgeLineWidth            | The scope badge primitive line width |
| badgeLineColor            | The scope badge primitive line color |
| commentBGColor            | The comment primitive background color |
| commentFGColor            | The comment primitive foreground color |
| commentLineColor          | The comment primitive line color |
| commentLineWidth          | The comment primitive line width |
| mainLine                  | The main execution vertical line shift from the left edge |
| fileScopeBGColor          | The module (file) scope primitive background color |
| funcScopeBGColor          | The function scope primitive background color |
| decorScopeBGColor         | The decorator scope primitive background color |
| classScopeBGColor         | The class scope primitive background color |
| forScopeBGColor           | The for scope primitive background color |
| whileScopeBGColor         | The while scope primitive background color |
| elseScopeBGColor          | The else scope primitive background color |
| withScopeBGColor          | The with scope primitive background color |
| tryScopeBGColor           | The try scope primitive background color |
| exceptScopeBGColor        | The except scope primitive background color |
| finallyScopeBGColor       | The finally scope primitive background color |
| breakBGColor              | The break primitive background color |
| continueBGColor           | The continue primitive background color |
| ifBGColor                 | The if primitive background color |
| hiddenCommentText         | The text to be displayed when the comment primitives are suppressed |
| hiddenExceptText          | The text to be displayed when the exception primitives are suppressed |
| collapsedOutlineWidth     | The collapsed group primitive distance between the inner and outer rectangles |
| openGroupVSpacer          | The open group primitive vertical spacer |
| openGroupHSpacer          | The open group primitive horizontal spacer |
| groupBGColor              | The group primitive background color |
| groupFGColor              | The group primitive foreground color |
| groupBorderColor          | The group primitive border color |
| groupControlBGColor       | The collapsed group primitive control box background color |
| groupControlBorderColor   | The collapsed group primitive control box border color |
| rubberBandBorderColor     | The rubber band border color |
| rubberBandFGColor         | The rubber band rectangle color |
| hDocLinkPadding           | The documentation primitive horizontal padding |
| vDocLinkPadding           | The documentation primitive vertical padding |
| docLinkBGColor            | The documentation primitive background color |
| docLinkFGColor            | The documentation primitive foreground color |
| docLinkLineColor          | The documentation primitive line color |
| docLinkLineWidth          | The documentation primitive line width |


app.css
-------
The file contains adjustments to the standard QT library widgets like QToolTip,
QLineEdit etc. The documentation what and how can be adjusted is available
[here](https://doc.qt.io/qt-5/stylesheet.html).


Include New Skin Into the Package
---------------------------------
If a skin needs to be included into a distribution package so that all the users
may benefit of it then the following steps need to be taken:
- the skin directory needs to be included into the project
  `codimension/skins/` directory
- platform specific needs to be considered
- the project setup.py needs to be adjusted

Sometimes the settings need to be platform specific. For example, two platforms
may have a different monospace fonts available. To cover this case Codimension
uses platform specific suffixes for the file names. The suffix is formed as:

```
<file name> + '.' + sys.platform.lower()
```

When Codimension starts and copies the package provided skins into the user
home directory it first looks for a platform specific file. If found then
it is copied with stripped suffix.

