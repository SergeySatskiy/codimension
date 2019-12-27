Codimension Color Schemes
=========================

Introduction
------------
Codimension uses skins to define how certain elements of the user interface
will look like. A skin is a set of files which reside in a designated directory.
The files are:
- app.css: the application style sheet
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
mentioned above files.

At the start Codimension creates the `~/.codimension3/skins/sample`
directory and populates the necessary files. The default skin values are
used to populate the files. The sole purpose of the sample directory is to
give a good start point to create a custom skin. The sample directory is not
analysed when a list of available skins is built.

Creating New Skin
-----------------
One of the options is to follow these steps:
- create a new directory for the new skin, e.g. `~/.codimension3/skins/myskin`
- copy skin.json, cflow.json and app.css from
  `~/.codimension3/skins/sample` to `~/.codimension3/skins/myskin`
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
Here is a description of some settings (may be incomplete) stored in skin.json

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
The file contains the settings for the control flow - colors for the individual
graphics items, fonts, paddings etc. All the efforts were made to have the key
names intuitively understood so there is no description for them. At any rate,
experiment and see how the graphics representation is affected.


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
- platform specific needs to be considered (e.g. fonts availability)
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


Overwriting Individual Skin Values
----------------------------------

Individual skin values can be overwritten. To do so put a json file called
override.json with a dictionary in it to the skin directory which values you
want to overwrite. The values from this file will update the skin dictionary.

Also, the skin directory can have pixmaps (png and svg) which will take priority
when Codimension loads a pixmap.

