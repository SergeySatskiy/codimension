Name: codimension
Version: 2.1.1
Release: 2
License: GPLv3+
Group: Development/Tools/IDE
Summary: Python IDE with emphasis on graphical representation
BuildArch: noarch

Source0: %{name}-%{version}.tar.gz
Source1: %{name}.xpm
Source2: %{name}.sharedmimeinfo
Source3: %{name}.desktop
ource4: %{name}.png

Requires: python
Requires: codimension-parser >= 1.6
Requires: PyQt4 qscintilla-python
Requires: pylint python-pygments python-chardet graphviz

BuildRequires: desktop-file-utils

%description
Codimension is an experimental Python IDE based on QT, QScintilla,
and a custom Python parser.

Features:

* Hierarchical file/class/function/global variable browsers
* Docstrings as item tooltips in browsers
* Filtering in browsers
* Jump to a module import/symbol definition using a hot key
* See the list of symbol references
* Navigation history within a file and between files
* Syntax highlighting in the source code editor
* Pixmap viewer
* Skin support
* Diagram of imports for a file, directory, or the whole project
* Search in files
* Incremental search/replace in a file
* Search for a file/class/function/global variable in the project
* One-click intgration of external tools (pylint, pymetrics)
* Simple line counter
* McCabe cyclomatic complexity for a file or many files
* New file templates
* Pyflakes integration
* Python debugger

%prep
%setup -q -n %{name}-%{version}

%build

%install
mkdir -p $RPM_BUILD_ROOT/%{_datadir}
cp -pr src $RPM_BUILD_ROOT%{_datadir}/%{name}
cp -pr thirdparty $RPM_BUILD_ROOT%{_datadir}/%{name}/
cp -pr plugins $RPM_BUILD_ROOT%{_datadir}/%{name}-plugins
mkdir -p $RPM_BUILD_ROOT/%{_bindir}
ln -s ../share/codimension/codimension.py $RPM_BUILD_ROOT/%{_bindir}/%{name}
mkdir -p $RPM_BUILD_ROOT%{_datadir}/pixmaps
cp -p %{SOURCE1} $RPM_BUILD_ROOT%{_datadir}/pixmaps/%{name}.xpm
cp -p %{SOURCE4} $RPM_BUILD_ROOT%{_datadir}/pixmaps/%{name}.png
mkdir -p $RPM_BUILD_ROOT%{_datadir}/mime/packages
cp -p %{SOURCE2} $RPM_BUILD_ROOT%{_datadir}/mime/packages/%{name}.xml
desktop-file-install --dir $RPM_BUILD_ROOT%{_datadir}/applications %{SOURCE3}

%post
update-mime-database %{_datadir}/mime
update-desktop-database -q

%postun
update-mime-database %{_datadir}/mime
update-desktop-database -q

%files
%defattr(-,root,root,-)
%{_bindir}/*
%{_datadir}/%{name}
%{_datadir}/applications/*.desktop
%{_datadir}/mime/packages/*.xml
%{_datadir}/pixmaps/*.xpm

%changelog
* Wed Aug 23 2013 Ilya Loginov <isloginov@gmail.com> - 2.1.1-2
- Version 2.1.1
- Fix: completion did not offer anything for relative imports. Issue #402.

* Wed Aug 14 2013 Ilya Loginov <isloginov@gmail.com> - 2.1.0-2
- Release 2.1.0
- Better calltips for PyQt objects.
- About dialog added.
- Ctrl+Shift+F1 added for the current call help.
- Better handling of the outline window redrawing - no redraw if syntax is broken.
- Better jumps from the outline window. Last good and the current parsed
  info are taken into account.
- Better undo of the automatically trimmed empty opened lines.
- Search indicators are now configurable (per skin).
- Make Ctrl+PgUp going to the previous tab while Ctrl+PgDwn to the next one.
- New feature: ui configurable monospaced font.
- Fix: opening another user (read only) project now works.
- New feature: plugin interface.
- New feature: garbage collector plugin.
- Bug fix: pyflakes analysis crashed if there was an invalid escape character
  or null characters in the buffer (Issue #399)
- Bug fix: pylint fails to run on files in projects which have no import dirs.
- Updating pyflakes to 0.7.3

* Sun Jun 30 2013 Ilya Loginov <isloginov@gmail.com> - 2.0.2-2
- Release 2.0.2
- New feature: editor calltips (Ctrl+/) and auto calltips (switchable via the
  Options menu) when '(' is entered.
- Fix: crash on Ubuntu 12.04 (possibly on other platforms too) in case of some
  styles. Issue #388.
- Fix: extra commas in the 'author' field when a new project is created on
  Ubuntu. Issue #387.
- Fix: extra long signatures in a context help do not limit min window width.
  Issue #386.
- Better completion for numpy and scipy names
- Including scipy for better rope help

* Tue Jun 18 2013 Ilya Loginov <isloginov@gmail.com> - 2.0.1-1
- Upstream changes for release 2.0.1:
- Replacing the 'file' utilities calls with magic module included in thirdparty
  directory.

* Tue Jun 05 2013 Ilya Loginov <isloginov@gmail.com> - 2.0-1
- Upstream changes for release 2.0:
- Initial implementation of the debugger.
- Project viewer restores the previous session expanded directories at the
  start automatically.
- More bound scintilla lexers
- Unhandled exceptions hook now saves the trace back and the log window
  content in a file.
- Some autocomplete improvements
- Allow explicit reloading even if a buffer is not modified.
- File outside modification detection now includes a file size.
- Files deleted via IDE UI are removed from the recent files list as well.
- Bug fix: respect multibyte chars when search incrementally
- Bug fix: autocomplition for non-ascii text did not work.
- Main menu and the text editor context menu now have 'open in browser'
  item.
- Main menu and the text editor context menu now have 'downdload and show'
  item.
- Main menu 'tab' now has 'highlight in...' items.
- Bug fix: 'highlight in file system browser' did not work if it was not a
  project file.
- Basic pyflakes support.
- Python .cgi support in outline browser.
- Bash/sh file type recognition added.
- Pylint and other tools support for python .cgi files.
- Bug fix: improper tooltips and text in similarities pylint sections
  if contained html.
- Bug fix: double slashes in full file names when opened via Ctrl+I.
- New feature: access to the project rope settings file via the Project menu.
- Better dialogs for the cases when both the disk version and the buffer
  content were modified and the user closes the tab or saves the tab content.
- New feature: tab context menu and current path label context menu on the
  status bar are extended with copying directory path and copying file name
  options.
- Minor bug fixes and improvements.

* Sun Jan 20 2013 Sergey Satskiy <sergey.satskiy@gmail.com> - 1.8-1
- Upstream changes for release 1.8:
- Bug fix: running python tidy with settings led to an exception.
- Improvement: focus is moved to the current editor widget automatically when
  it is received by the editor tab widget. Issue #350.
- Improvement: 'highilight in project' and 'highlight in filesystem'
  editor tab context menu added. Issue #258.
- Improvement: better handling the fact that an editing buffer is changed by
  the find-in-files result window. Issue #318.
- New feature: IDE-wide pylintrc support. Issue #344.
- Performance improvement and bug fixes in the file content trees, e.g
  file outline browser, project files browser etc.
- Bug fix: files with national characters with not-recognized type could
  lead to unpredicted behaviour (up to core dumps). Issue #348
- Bug fix: tab expanding (replace all) did not replace everything.
- Bug fix: main menu -> tools -> pylint for project led to an exception.
  Issue #346.
- Sometimes pylint reports absolute paths so it is respected now.
- When completion is called and a temporary rope project is created,
  exclude all the subdirectories where there are no __init__.py[3] files.
  This mitigate a setup with a network home dir (or network file location)
  in a directory where there are lots of subdirectories
- Add a shortcut in the 'Open file' dialog to the directory where the
  current tab file (if so) is.
- Add file to the recent files list at the time of closing a tab as well
  (not only at the time of opening). Otherwise a file is not there when it
  was loaded from a command line and then its tab is closed.
- Do not lose the current editor position when there was an incremental
  search on a tab and then another tab is closed.
- Prevent losing selection in case switching between history positions
  if nothing has been changed in the required buffer.
- Have the find-in-files dialog interruptible at the stage of building
  the list of files to search in.


* Sun Oct 14 2012 Dmitry Kazimirov <dk@revl.org> - 1.7-1
- Python dependency: python2 -> python
- Upstream bugfix release:
- Early logging on Windows-based X Server could lead to crashes.
- Shift+Tab is intercepted properly in the editor window on Windows.
- The default encoding is now set to 'utf-8' for Codimension itself.
- Explicitly pass focus to the current editor when Codimension is
  activated.

 -- Dmitry Kazimirov <dk@revl.org>  Sun, 14 Oct 2012 01:35:37 -0400

* Mon Sep 17 2012 Dmitry Kazimirov <dk@revl.org> - 1.6-1
- Upstream changes for release 1.5:
- New feature: PythonTidy integration and diff viewers.
- New feature: copying a diagram to the clipboard (main menu and Ctrl+C)
- New feature: support for the new file templates when no new
  project is loaded; UI to create, edit, and delete new file
  templates.
- New feature: unused class, function, and global
  variable analysis.
- New feature: find occurences in class, function, and
  global variable viewers.
- Bug fix for incorrect file icons in the editing history.
- Bug fix for incorrect file name in the editing history
  after "Save As".
- Bug fix: it is now possible to save unchanged files that were
  deleted from the disk.
- "New Project" button is removed from the main toolbar.
- Editor settings are moved from the main toolbar to the
  new main menu item 'Options'.
- New feature: total number of matches is now shown
  in the search result header.
- New feature: disassember for functions and classes
  in the function and class viewers.
- New feature: profiling support (with both graphical and
  tabular result representation).
- New feature: export of the profiler and module dependency
  diagrams to PNG images.
- Visual and performance improvements of import diagrams.
- Ctrl+' replaces Ctrl+N to highlight the current word. Issue #323
- Ctrl+N replaces Ctrl+T to create a new file. Issue #323
- Ctrl+T is not used for anything now. Issue #323
- Bug fix for exception while building a completion list. Issue #321
- Bug fix to update the FS view after file/dir removal via the
  context menu.  Issue #325
- Bug fix to make it possible to create a nested project directory
- Bug fix: do not show the 'reload' menu item for deleted files
- Bug fix for Save As when the target file is open in another tab.
  Issue #317
- Bug fix for updating the project properties when the script
  name is empty.
- Python built-in functions are now highlighted as keywords.
- File encoding is displayed and can be changed via a context menu.
  Issue #69
- New feature: the editor context menu.
- New feature: Alt+U to jump to the first line of the current
  function or class. Issue #316
- New feature: line counter for the buffer. Issue #107
- Open project via the OS file selection dialog (Ctrl+Shift+O)
- New feature: the main menu.

* Thu Jan 26 2012 Dmitry Kazimirov <dk@revl.org> - 1.4-1
- Dependency from the rope refactoring library is introduced.
- A stable upstream version that brings many improvements,
  new features, and some bugfixes:
- Improvement: no unnecessary scrolling the line to jump to is
  already visible.
- New feature: Ctrl+] searches for occurrences of the word
  under the cursor.
- New feature: Ctrl+F3 initiates the search for the word under
  the cursor without bringing up the find dialog.
- Ctrl+F and Ctrl+R keep the 'match case' and 'whole word' flags
  intact between searches.
- New feature: run the project or the current script in a new
  terminal. Script environment and parameters are remembered
  between runs.
- New feature: go to definition (Ctrl+backslash)
- New feature: docstring for the identifier under the cursor
  when Ctrl+F1 is pressed.
- Removed the ability to have multiple project roots.
- New feature: project specific paths to resolve imports.
- New feature: code completion (Tab, Ctrl+Space).
- Fixed buffer change notifications in the search result window.
- Bug fix: copy/paste buffer content was overwritten when an
  item in a completion list was selected. Issue #310.
- Bug fix: exception while creating a new project.
- Bug fix: update tab history properly when jumping within
  the same file.
- Fixed cursor positioning after automatic trailing whitespace
  removal.

* Thu Dec 15 2011 Dmitry Kazimirov <dk@revl.org> - 1.3-1
- New upstream version with lots of bug fixes and new features:
- Bug fix: correct tooltips for search results in the HTML
  files. Issue #188.
- Bug fix: prevent NUL characters from appearing in the text
  editor.  Issue #203.
- New feature: automatically trim empty lines when the cursor
  moves.  Issue #294.
- New feature: Ctrl+N iterates over highlighted words if the
  current word matches the one previously highlighted. Ctrl+, or
  Ctrl+. iterates over the highlighted words regardless of what
  word the cursor is on. Issue #303.
- New feature: double click on the status bar path label copies
  the file pathname to the clipboard.
- New feature: detection of files changes outside of
  Codimension.
- Bug fix: loading a project from the file system browser checks
  if all currently open files have no modifications. Issue #295.
- Some fixes in the replace implementation.
- Bug fix: incorrect interpretation of the search pattern in
  'Find in files'.  Issue #301.
- Ctrl+C/Ctrl+Insert to copy the current line if there is no
  selection.  Issue #304.
- New editor setting: automatic removal of trailing spaces on
  saving.  Issue #300.
- New configuration setting: whether HOME should move the cursor
  to the first column or to the first non space character.
  Issue #302.
- The 'find' and 'replace' search histories are shared now.
  Issue #298.
- Incremental find/replace now makes the match a text selection.
  Issue #297.
- Bug fix in the replace implementation: adding separate button
  'replace and move'. Issue #277.
- Ctrl+F and Ctrl+R select the text to search even if the
  widget has already been displayed. Issue #291.
- Ctrl+X is now a synonym to Shift+Del. Issue #290.
- Bug fix: F3 and Shift+F3 now work for the find/replace search
  string depending of what dialog was shown last. Issue #289.
- The help and welcome screens have been updated. Issue #281,
  Issue #279.
- Shift+Home/Shift+End now select to the beginning/end of the
  current line.  Issue #286.
- Support for Alt+Shift+Left/Right - select a part of a
  "CamelCased" word.  Issue #287.
- Alt+Shift+Up/Down now select to the beginning/end of a
  paragraph. Issue #288.
- Support for Shift+Del - copy to the buffer and delete a
  selection (if there's any) or the current line otherwise.
  Issue #285.
- HOME and END now jump to the beginning/end of the visible
  line. Issue #284.
- Support for the Alt+Up and Alt+Down hot keys.
- The history hot keys have been changed to Alt+PgDown
  and Alt+PgUp.
- Support for Alt+Left and Alt+Right hot keys (jump over a part
  of a "CamelCased" word).
- Bug fix: check that all the modified files are saved before
  letting a new project to be created. Issue #273.
- Move the focus to the text editor if the focus was not in the
  editor and the currently active tab is clicked. Issue #264.

* Wed Oct 19 2011 Dmitry Kazimirov <dk@revl.org> - 1.2-1
- New upstream version with a significant bug fix:
  exception during checking for a newer version
  is properly handled.
- Minor bug fix: 'remove recent project' toolbar
  button is enabled properly now.
- Brace highlighting can now be switched on and off.
- New feature: block/line commenting/uncommenting
  with Ctrl-M.
- Better file modification indicator.
- Autoindent is switched on by default now.

* Tue Sep 13 2011 Dmitry Kazimirov <dk@revl.org> - 1.1-1
- New upstream version, which provides a hint message for
  pymetrics failures.
- Syntax error exception in the file browser is now
  correctly handled.

* Mon Sep 05 2011 Dmitry Kazimirov <dk@revl.org> - 1.0-1
- Initial release.
