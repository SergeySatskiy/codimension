Essential links:
  * [Project home page](http://satsky.spb.ru/codimension/codimensionEng.php)
  * [Installation instructions](http://satsky.spb.ru/codimension/installationEng.php)
  * [Packages for downloading](http://satsky.spb.ru/codimension/downloadEng.php)
  * [Hot keys cheat sheet (pdf)](http://satsky.spb.ru/codimension/other/CodimensionShortcuts.pdf)

---


**Codimension** is yet another free experimental Python IDE licensed under GPL v3.

Codimension aims to provide an integrated system for:
  * traditional text-based code editing, and
  * diagram-based code analysis.

Many Python developers will find codimension useful as-is, even though not all of its features have been implemented yet.

The finished codimension will include several graphics-based features. Diagrams will be generated for imports and classes. The results from some tools, such as a profiler, will be represented graphically. Graphical features will be interactive and if you double click on a class box in a diagram, for example, the corresponding source code file will be opened and the cursor will jump to the appropriate line. A major objective is to provide an editor which is capable of working simultaneously with textual and graphical representations of the code. With this feature in place, changing the text will automatically update the graphics and vice versa. Finally, the editor will support the grouping and traversal of code blocks, which should greatly simplify the analysis of unfamiliar code.

![http://satsky.spb.ru/codimension/screenshots/01-commonView.png](http://satsky.spb.ru/codimension/screenshots/01-commonView.png)


## Features ##

### Implemented features (major only, no certain order): ###

  * Ability to work with standalone files and with projects
  * Remembering the list of opened files (and the cursor position in each file) separately for each project
  * Editing history support within / between files
  * Ability to hide / show tab bars
  * Recently edited files list support for each project separately
  * Recent projects list support
  * Automatic watching of the project dirs for deleted / created files
  * Template supports for new python files for each project separately
  * Editor syntax highlight
  * Imports diagram for a file, a directory (recursively) or for a whole project with jumps to the code
  * Simple line counter
  * Hierarchical python files content browser with quick jumps to the code
  * Hierarchical classes / functions / globals browsers with filtering and quick jump to the code
  * Object browsers support showing docstrings as items tooltips
  * File outline tab
  * Running pylint with one click and quick jumps to the code from the produced output
  * Running pymetrics with one click and quick jumps to the code from the produced output where possible
  * Ability to run pylint / pymetrics for a file, a directory (recursively) or for a whole project
  * Table sortable representation of the McCabe cyclomatic complexity for a file or many files
  * Ability to have pylint settings file for each project separately
  * Opening file imports using a hot key; jumping to a definition of a certain imported item
  * Incremental search in a file
  * Incremental replace in a file
  * Search in files
  * Search for a name (class, function, global variable) in the project
  * Search for a file in the project
  * Jumping to a line in a file
  * Pixmaps viewer
  * Editor skins support
  * Detecting files changed outside of codimension
  * Code completers (TAB or Ctrl+Space)
  * Context help for a python file (Ctrl+F1)
  * Jump to the current tag definition (Ctrl+backslash)
  * Find occurrences (Ctrl+])
  * Main menu, editor and tab context menus
  * PythonTidy (python code beautifier) script integration and diff viewer
  * Search for unused global variables, functions, classes
  * Disassembler for classes and functions via object browsers context menu
  * Table representation of profiling results (individual scripts/project)
  * Graphics representation of profiling results (individual scripts/project)
  * Extending running/profiling parameters to close terminal upon successful completion
  * Pyflakes integration
  * Debugger
  * Calltips
  * Plugin infrastructure including Version Control System plugin support
  * SVN plugin
  * Ran and debugged script may have IO redirected to IDE
  * Main editor navigation bar


### Planned features (not in priority order): ###

  * Classes diagram with jumps to the code
  * TODO tab
  * Bookmarks
  * Refactoring support
  * Print / print preview for various windows
  * Ability to tear off / merge editor windows
  * Sphinx integration
  * Graphics representation and editing the program control flow
  * Code coverage