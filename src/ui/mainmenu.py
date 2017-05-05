# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2017  Sergey Satskiy <sergey.satskiy@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

"""Codimension main window menu"""


import os.path
from utils.pixmapcache import getIcon
from utils.config import CONFIG_DIR
from utils.skin import getThemesList
from utils.colorfont import getMonospaceFontList
from utils.globals import GlobalData
from utils.misc import getIDETemplateFile, getProjectTemplateFile
from .qt import QDir, QApplication, QMenu, QStyleFactory, QActionGroup
from .mainwindowtabwidgetbase import MainWindowTabWidgetBase


class MainWindowMenuMixin:

    """Main window menu mixin"""

    def __init__(self):
        pass

    def _initMainMenu(self):
        """Initializes the main menu bar"""
        # The Project menu
        prjMenu = QMenu("&Project", self)
        prjMenu.aboutToShow.connect(self.__prjAboutToShow)
        prjMenu.aboutToHide.connect(self.__prjAboutToHide)
        self.__newProjectAct = prjMenu.addAction(
            getIcon('createproject.png'), "&New project",
            self._createNewProject, 'Ctrl+Shift+N')
        self.__openProjectAct = prjMenu.addAction(
            getIcon('project.png'), '&Open project',
            self._openProject, 'Ctrl+Shift+O')
        self._unloadProjectAct = prjMenu.addAction(
            getIcon('unloadproject.png'), '&Unload project',
            self.projectViewer.unloadProject)
        self._projectPropsAct = prjMenu.addAction(
            getIcon('smalli.png'), '&Properties',
            self.projectViewer.projectProperties)
        prjMenu.addSeparator()
        self._prjTemplateMenu = QMenu("Project-specific &template", self)
        self.__createPrjTemplateAct = self._prjTemplateMenu.addAction(
            getIcon('generate.png'), '&Create')
        self.__createPrjTemplateAct.triggered.connect(
            self._onCreatePrjTemplate)
        self.__editPrjTemplateAct = self._prjTemplateMenu.addAction(
            getIcon('edit.png'), '&Edit')
        self.__editPrjTemplateAct.triggered.connect(self._onEditPrjTemplate)
        self._prjTemplateMenu.addSeparator()
        self.__delPrjTemplateAct = self._prjTemplateMenu.addAction(
            getIcon('trash.png'), '&Delete')
        self.__delPrjTemplateAct.triggered.connect(self._onDelPrjTemplate)
        prjMenu.addMenu(self._prjTemplateMenu)
        prjMenu.addSeparator()
        self.__recentPrjMenu = QMenu("&Recent projects", self)
        self.__recentPrjMenu.triggered.connect(self._onRecentPrj)
        prjMenu.addMenu(self.__recentPrjMenu)
        prjMenu.addSeparator()
        self.__quitAct = prjMenu.addAction(
            getIcon('exitmenu.png'), "E&xit codimension",
            QApplication.closeAllWindows, "Ctrl+Q")

        # The Tab menu
        tabMenu = QMenu("&Tab", self)
        tabMenu.aboutToShow.connect(self.__tabAboutToShow)
        tabMenu.aboutToHide.connect(self.__tabAboutToHide)
        self.__newTabAct = tabMenu.addAction(
            getIcon('filemenu.png'), "&New tab",
            self.em.newTabClicked, 'Ctrl+N')
        self.__openFileAct = tabMenu.addAction(
            getIcon('filemenu.png'), '&Open file', self._openFile, 'Ctrl+O')
        self.__cloneTabAct = tabMenu.addAction(
            getIcon('clonetabmenu.png'), '&Clone tab', self.em.onClone)
        self.__closeOtherTabsAct = tabMenu.addAction(
            getIcon(''), 'Close oth&er tabs', self.em.onCloseOther)
        self.__closeTabAct = tabMenu.addAction(
            getIcon('closetabmenu.png'), 'Close &tab', self.em.onCloseTab)
        tabMenu.addSeparator()
        self.__saveFileAct = tabMenu.addAction(
            getIcon('savemenu.png'), '&Save', self.em.onSave, 'Ctrl+S')
        self.__saveFileAsAct = tabMenu.addAction(
            getIcon('saveasmenu.png'),
            'Save &as...', self.em.onSaveAs, "Ctrl+Shift+S")
        self.__tabJumpToDefAct = tabMenu.addAction(
            getIcon('definition.png'), "&Jump to definition",
            self._onTabJumpToDef)
        self.__calltipAct = tabMenu.addAction(
            getIcon('calltip.png'), 'Show &calltip', self._onShowCalltip)
        self.__tabJumpToScopeBeginAct = tabMenu.addAction(
            getIcon('jumpupscopemenu.png'),
            'Jump to scope &begin', self._onTabJumpToScopeBegin)
        self.__tabOpenImportAct = tabMenu.addAction(
            getIcon('imports.png'), 'Open &import(s)', self._onTabOpenImport)
        self.__openAsFileAct = tabMenu.addAction(
            getIcon('filemenu.png'), 'O&pen as file', self._onOpenAsFile)
        self.__downloadAndShowAct = tabMenu.addAction(
            getIcon('filemenu.png'), 'Download and show',
            self._onDownloadAndShow)
        self.__openInBrowserAct = tabMenu.addAction(
            getIcon('homepagemenu.png'), 'Open in browser',
            self._onOpenInBrowser)
        tabMenu.addSeparator()
        self.__highlightInPrjAct = tabMenu.addAction(
            getIcon('highlightmenu.png'), 'Highlight in project browser',
            self.em.onHighlightInPrj)
        self.__highlightInFSAct = tabMenu.addAction(
            getIcon('highlightmenu.png'), 'Highlight in file system browser',
            self.em.onHighlightInFS)
        self.__highlightInOutlineAct = tabMenu.addAction(
            getIcon('highlightmenu.png'), 'Highlight in outline browser',
            self._onHighlightInOutline)
        tabMenu.addSeparator()
        self.__recentFilesMenu = QMenu("&Recent files", self)
        self.__recentFilesMenu.triggered.connect(self._onRecentFile)
        tabMenu.addMenu(self.__recentFilesMenu)

        # The Edit menu
        editMenu = QMenu("&Edit", self)
        editMenu.aboutToShow.connect(self.__editAboutToShow)
        editMenu.aboutToHide.connect(self.__editAboutToHide)
        self.__undoAct = editMenu.addAction(
            getIcon('undo.png'), '&Undo', self._onUndo)
        self.__redoAct = editMenu.addAction(
            getIcon('redo.png'), '&Redo', self._onRedo)
        editMenu.addSeparator()
        self.__cutAct = editMenu.addAction(
            getIcon('cutmenu.png'), 'Cu&t', self._onCut)
        self.__copyAct = editMenu.addAction(
            getIcon('copymenu.png'), '&Copy', self.em.onCopy)
        self.__pasteAct = editMenu.addAction(
            getIcon('pastemenu.png'), '&Paste', self._onPaste)
        self.__selectAllAct = editMenu.addAction(
            getIcon('selectallmenu.png'), 'Select &all', self._onSelectAll)
        editMenu.addSeparator()
        self.__commentAct = editMenu.addAction(
            getIcon('commentmenu.png'), 'C&omment/uncomment', self._onComment)
        self.__duplicateAct = editMenu.addAction(
            getIcon('duplicatemenu.png'), '&Duplicate line', self._onDuplicate)
        self.__autocompleteAct = editMenu.addAction(
            getIcon('autocompletemenu.png'), 'Autoco&mplete',
            self._onAutocomplete)
        self.__expandTabsAct = editMenu.addAction(
            getIcon('expandtabs.png'), 'Expand tabs (&4 spaces)',
            self._onExpandTabs)
        self.__trailingSpacesAct = editMenu.addAction(
            getIcon('trailingws.png'), 'Remove trailing &spaces',
            self._onRemoveTrailingSpaces)

        # The Search menu
        searchMenu = QMenu("&Search", self)
        searchMenu.aboutToShow.connect(self.__searchAboutToShow)
        searchMenu.aboutToHide.connect(self.__searchAboutToHide)
        self.__searchInFilesAct = searchMenu.addAction(
            getIcon('findindir.png'), "Find in file&s",
            self.findInFilesClicked, "Ctrl+Shift+F")
        searchMenu.addSeparator()
        self._findNameMenuAct = searchMenu.addAction(
            getIcon('findname.png'), 'Find &name in project',
            self.findNameClicked, 'Alt+Shift+S')
        self._fileProjectFileAct = searchMenu.addAction(
            getIcon('findfile.png'), 'Find &project file',
            self.findFileClicked, 'Alt+Shift+O')
        searchMenu.addSeparator()
        self.__findOccurencesAct = searchMenu.addAction(
            getIcon('findindir.png'), 'Find &occurrences',
            self._onFindOccurences)
        self.__findAct = searchMenu.addAction(
            getIcon('findindir.png'), '&Find...', self._onFind)
        self.__findNextAct = searchMenu.addAction(
            getIcon('1rightarrow.png'), "&Next highlight", self._onFindNext)
        self.__findPrevAct = searchMenu.addAction(
            getIcon('1leftarrow.png'), "Pre&vious highlight",
            self._onFindPrevious)
        self.__replaceAct = searchMenu.addAction(
            getIcon('replace.png'), '&Replace...', self._onReplace)
        self.__goToLineAct = searchMenu.addAction(
            getIcon('gotoline.png'), '&Go to line...', self._onGoToLine)

        # The Tools menu
        toolsMenu = QMenu("T&ools", self)
        toolsMenu.aboutToShow.connect(self.__toolsAboutToShow)
        self._prjLineCounterAct = toolsMenu.addAction(
            getIcon('linecounter.png'), "&Line counter for project",
            self.linecounterButtonClicked)
        self.__tabLineCounterAct = toolsMenu.addAction(
            getIcon('linecounter.png'), "L&ine counter for tab",
            self._onTabLineCounter)
        toolsMenu.addSeparator()
        self.__unusedClassesAct = toolsMenu.addAction(
            getIcon('notused.png'), 'Unused class analysis',
            self.onNotUsedClasses)
        self.__unusedFunctionsAct = toolsMenu.addAction(
            getIcon('notused.png'), 'Unused function analysis',
            self.onNotUsedFunctions)
        self.__unusedGlobalsAct = toolsMenu.addAction(
            getIcon('notused.png'), 'Unused global variable analysis',
            self.onNotUsedGlobals)

        # The Run menu
        self.__runMenu = QMenu("&Run", self)
        self.__runMenu.aboutToShow.connect(self.__runAboutToShow)
        self.__prjRunAct = self.__runMenu.addAction(
            getIcon('run.png'), 'Run &project main script',
            self._onRunProject)
        self.__prjRunDlgAct = self.__runMenu.addAction(
            getIcon('detailsdlg.png'), 'Run p&roject main script...',
            self._onRunProjectSettings)
        self._tabRunAct = self.__runMenu.addAction(
            getIcon('run.png'), 'Run &tab script', self.onRunTab)
        self._tabRunDlgAct = self.__runMenu.addAction(
            getIcon('detailsdlg.png'), 'Run t&ab script...', self.onRunTabDlg)
        self.__runMenu.addSeparator()
        self.__prjProfileAct = self.__runMenu.addAction(
            getIcon('profile.png'), 'Profile project main script',
            self._onProfileProject)
        self.__prjProfileDlgAct = self.__runMenu.addAction(
            getIcon('profile.png'), 'Profile project main script...',
            self._onProfileProjectSettings)
        self._tabProfileAct = self.__runMenu.addAction(
            getIcon('profile.png'), 'Profile tab script', self._onProfileTab)
        self._tabProfileDlgAct = self.__runMenu.addAction(
            getIcon('profile.png'), 'Profile tab script...',
            self._onProfileTabDlg)

        # The Debug menu
        dbgMenu = QMenu("Debu&g", self)
        dbgMenu.aboutToShow.connect(self.__debugAboutToShow)
        self._prjDebugAct = dbgMenu.addAction(
            getIcon('debugger.png'), 'Debug &project main script',
            self._onDebugProject, "Shift+F5")
        self._prjDebugDlgAct = dbgMenu.addAction(
            getIcon('detailsdlg.png'), 'Debug p&roject main script...',
            self._onDebugProjectSettings, "Ctrl+Shift+F5")
        self._tabDebugAct = dbgMenu.addAction(
            getIcon('debugger.png'), 'Debug &tab script',
            self._onDebugTab, "F5")
        self._tabDebugDlgAct = dbgMenu.addAction(
            getIcon('detailsdlg.png'), 'Debug t&ab script...',
            self._onDebugTabDlg, "Ctrl+F5")
        dbgMenu.addSeparator()
        self.__debugStopBrutalAct = dbgMenu.addAction(
            getIcon('dbgstopbrutal.png'), 'Stop session and kill console',
            self._onBrutalStopDbgSession, "Ctrl+F10")
        self.__debugStopBrutalAct.setEnabled(False)
        self.__debugStopAct = dbgMenu.addAction(
            getIcon('dbgstop.png'), 'Stop session and keep console if so',
            self._onStopDbgSession, "F10")
        self.__debugStopAct.setEnabled(False)
        self.__debugRestartAct = dbgMenu.addAction(
            getIcon('dbgrestart.png'), 'Restart session',
            self._onRestartDbgSession, "F4")
        self.__debugRestartAct.setEnabled(False)
        dbgMenu.addSeparator()
        self.__debugContinueAct = dbgMenu.addAction(
            getIcon('dbggo.png'), 'Continue', self._onDbgGo, "F6")
        self.__debugContinueAct.setEnabled(False)
        self.__debugStepInAct = dbgMenu.addAction(
            getIcon('dbgstepinto.png'), 'Step in', self._onDbgStepInto, "F7")
        self.__debugStepInAct.setEnabled(False)
        self.__debugStepOverAct = dbgMenu.addAction(
            getIcon('dbgnext.png'), 'Step over', self._onDbgNext, "F8")
        self.__debugStepOverAct.setEnabled(False)
        self.__debugStepOutAct = dbgMenu.addAction(
            getIcon('dbgreturn.png'), 'Step out', self._onDbgReturn, "F9")
        self.__debugStepOutAct.setEnabled(False)
        self.__debugRunToCursorAct = dbgMenu.addAction(
            getIcon('dbgruntoline.png'), 'Run to cursor',
            self._onDbgRunToLine, "Shift+F6")
        self.__debugRunToCursorAct.setEnabled(False)
        self.__debugJumpToCurrentAct = dbgMenu.addAction(
            getIcon('dbgtocurrent.png'), 'Show current line',
            self._onDbgJumpToCurrent, "Ctrl+W")
        self.__debugJumpToCurrentAct.setEnabled(False)
        dbgMenu.addSeparator()

        self.__dumpDbgSettingsMenu = QMenu("Dump debug settings", self)
        dbgMenu.addMenu(self.__dumpDbgSettingsMenu)
        self.__debugDumpSettingsAct = self.__dumpDbgSettingsMenu.addAction(
            getIcon('dbgsettings.png'), 'Debug session settings',
            self._onDumpDebugSettings)
        self.__debugDumpSettingsAct.setEnabled(False)
        self.__debugDumpSettingsEnvAct = self.__dumpDbgSettingsMenu.addAction(
            getIcon('detailsdlg.png'),
            'Session settings with complete environment',
            self._onDumpFullDebugSettings)
        self.__debugDumpSettingsEnvAct.setEnabled(False)
        self.__dumpDbgSettingsMenu.addSeparator()
        self.__debugDumpScriptSettingsAct = \
            self.__dumpDbgSettingsMenu.addAction(
                getIcon('dbgsettings.png'), 'Current script settings',
                self._onDumpScriptDebugSettings)
        self.__debugDumpScriptSettingsAct.setEnabled(False)
        self.__debugDumpScriptSettingsEnvAct = \
            self.__dumpDbgSettingsMenu.addAction(
                getIcon('detailsdlg.png'),
                'Current script settings with complete environment',
                self._onDumpScriptFullDebugSettings)
        self.__debugDumpScriptSettingsEnvAct.setEnabled(False)
        self.__dumpDbgSettingsMenu.addSeparator()
        self.__debugDumpProjectSettingsAct = \
            self.__dumpDbgSettingsMenu.addAction(
                getIcon('dbgsettings.png'), 'Project main script settings',
                self._onDumpProjectDebugSettings)
        self.__debugDumpProjectSettingsAct.setEnabled(False)
        self.__debugDumpProjectSettingsEnvAct = \
            self.__dumpDbgSettingsMenu.addAction(
                getIcon('detailsdlg.png'),
                'Project script settings with complete environment',
                self._onDumpProjectFullDebugSettings)
        self.__debugDumpProjectSettingsEnvAct.setEnabled(False)
        self.__dumpDbgSettingsMenu.aboutToShow.connect(
            self.__onDumpDbgSettingsAboutToShow)

        # The Diagrams menu
        diagramsMenu = QMenu("&Diagrams", self)
        diagramsMenu.aboutToShow.connect(self.__diagramsAboutToShow)
        self._prjImportDgmAct = diagramsMenu.addAction(
            getIcon('importsdiagram.png'), '&Project imports diagram',
            self._onImportDgm)
        self._prjImportsDgmDlgAct = diagramsMenu.addAction(
            getIcon('detailsdlg.png'), 'P&roject imports diagram...',
            self._onImportDgmTuned)
        self.__tabImportDgmAct = diagramsMenu.addAction(
            getIcon('importsdiagram.png'), '&Tab imports diagram',
            self._onTabImportDgm)
        self.__tabImportDgmDlgAct = diagramsMenu.addAction(
            getIcon('detailsdlg.png'), 'T&ab imports diagram...',
            self._onTabImportDgmTuned)

        # The View menu
        viewMenu = QMenu("&View", self)
        viewMenu.aboutToShow.connect(self.__viewAboutToShow)
        viewMenu.aboutToHide.connect(self.__viewAboutToHide)
        self.__shrinkBarsAct = viewMenu.addAction(
            getIcon('shrinkmenu.png'), "&Hide sidebars",
            self._onMaximizeEditor, 'F11')
        self.__leftSideBarMenu = QMenu("&Left sidebar", self)
        self.__leftSideBarMenu.triggered.connect(self._activateSideTab)
        self.__prjBarAct = self.__leftSideBarMenu.addAction(
            getIcon('project.png'), 'Activate &project tab')
        self.__prjBarAct.setData('project')
        self.__recentBarAct = self.__leftSideBarMenu.addAction(
            getIcon('project.png'), 'Activate &recent tab')
        self.__recentBarAct.setData('recent')
        self.__classesBarAct = self.__leftSideBarMenu.addAction(
            getIcon('class.png'), 'Activate &classes tab')
        self.__classesBarAct.setData('classes')
        self.__funcsBarAct = self.__leftSideBarMenu.addAction(
            getIcon('fx.png'), 'Activate &functions tab')
        self.__funcsBarAct.setData('functions')
        self.__globsBarAct = self.__leftSideBarMenu.addAction(
            getIcon('globalvar.png'), 'Activate &globals tab')
        self.__globsBarAct.setData('globals')
        self.__leftSideBarMenu.addSeparator()
        self.__hideLeftSideBarAct = self.__leftSideBarMenu.addAction(
            getIcon(""), '&Hide left sidebar', self._leftSideBar.shrink)
        viewMenu.addMenu(self.__leftSideBarMenu)

        self.__rightSideBarMenu = QMenu("&Right sidebar", self)
        self.__rightSideBarMenu.triggered.connect(self._activateSideTab)
        self.__outlineBarAct = self.__rightSideBarMenu.addAction(
            getIcon('filepython.png'), 'Activate &outline tab')
        self.__outlineBarAct.setData('fileoutline')
        self.__debugBarAct = self.__rightSideBarMenu.addAction(
            getIcon(''), 'Activate &debug tab')
        self.__debugBarAct.setData('debugger')
        self.__excptBarAct = self.__rightSideBarMenu.addAction(
            getIcon(''), 'Activate &exceptions tab')
        self.__excptBarAct.setData('excptions')
        self.__bpointBarAct = self.__rightSideBarMenu.addAction(
            getIcon(''), 'Activate &breakpoints tab')
        self.__bpointBarAct.setData('breakpoints')
        self.__rightSideBarMenu.addSeparator()
        self.__hideRightSideBarAct = self.__rightSideBarMenu.addAction(
            getIcon(""), '&Hide right sidebar', self._rightSideBar.shrink)
        viewMenu.addMenu(self.__rightSideBarMenu)

        self.__bottomSideBarMenu = QMenu("&Bottom sidebar", self)
        self.__bottomSideBarMenu.triggered.connect(self._activateSideTab)
        self.__logBarAct = self.__bottomSideBarMenu.addAction(
            getIcon('logviewer.png'), 'Activate &log tab')
        self.__logBarAct.setData('log')
        self.__searchBarAct = self.__bottomSideBarMenu.addAction(
            getIcon('findindir.png'), 'Activate &search tab')
        self.__searchBarAct.setData('search')
        self.__contextHelpBarAct = self.__bottomSideBarMenu.addAction(
            getIcon('helpviewer.png'), 'Activate context &help tab')
        self.__contextHelpBarAct.setData('contexthelp')
        self.__diffBarAct = self.__bottomSideBarMenu.addAction(
            getIcon('diffviewer.png'), 'Activate &diff tab')
        self.__diffBarAct.setData('diff')
        self.__bottomSideBarMenu.addSeparator()
        self.__hideBottomSideBarAct = self.__bottomSideBarMenu.addAction(
            getIcon(""), '&Hide bottom sidebar', self._bottomSideBar.shrink)
        viewMenu.addMenu(self.__bottomSideBarMenu)
        viewMenu.addSeparator()
        self.__zoomInAct = viewMenu.addAction(
            getIcon('zoomin.png'), 'Zoom &in', self._onZoomIn)
        self.__zoomOutAct = viewMenu.addAction(
            getIcon('zoomout.png'), 'Zoom &out', self._onZoomOut)
        self.__zoom11Act = viewMenu.addAction(
            getIcon('zoomreset.png'), 'Zoom r&eset', self._onZoomReset)

        # Options menu
        optionsMenu = QMenu("Optio&ns", self)
        optionsMenu.aboutToShow.connect(self.__optionsAboutToShow)

        self.__ideTemplateMenu = QMenu("IDE-wide &template", self)
        self.__ideCreateTemplateAct = self.__ideTemplateMenu.addAction(
            getIcon('generate.png'), '&Create')
        self.__ideCreateTemplateAct.triggered.connect(
            self._onCreateIDETemplate)
        self.__ideEditTemplateAct = self.__ideTemplateMenu.addAction(
            getIcon('edit.png'), '&Edit')
        self.__ideEditTemplateAct.triggered.connect(self._onEditIDETemplate)
        self.__ideTemplateMenu.addSeparator()
        self.__ideDelTemplateAct = self.__ideTemplateMenu.addAction(
            getIcon('trash.png'), '&Delete')
        self.__ideDelTemplateAct.triggered.connect(self._onDelIDETemplate)
        optionsMenu.addMenu(self.__ideTemplateMenu)

        optionsMenu.addSeparator()

        verticalEdgeAct = optionsMenu.addAction('Show vertical edge')
        verticalEdgeAct.setCheckable(True)
        verticalEdgeAct.setChecked(self.settings['verticalEdge'])
        verticalEdgeAct.changed.connect(self._verticalEdgeChanged)
        showSpacesAct = optionsMenu.addAction('Show whitespaces')
        showSpacesAct.setCheckable(True)
        showSpacesAct.setChecked(self.settings['showSpaces'])
        showSpacesAct.changed.connect(self._showSpacesChanged)
        lineWrapAct = optionsMenu.addAction('Wrap long lines')
        lineWrapAct.setCheckable(True)
        lineWrapAct.setChecked(self.settings['lineWrap'])
        lineWrapAct.changed.connect(self._lineWrapChanged)
        showEOLAct = optionsMenu.addAction('Show EOL')
        showEOLAct.setCheckable(True)
        showEOLAct.setChecked(self.settings['showEOL'])
        showEOLAct.changed.connect(self._showEOLChanged)
        showBraceMatchAct = optionsMenu.addAction('Show brace matching')
        showBraceMatchAct.setCheckable(True)
        showBraceMatchAct.setChecked(self.settings['showBraceMatch'])
        showBraceMatchAct.changed.connect(self._showBraceMatchChanged)
        autoIndentAct = optionsMenu.addAction('Auto indent')
        autoIndentAct.setCheckable(True)
        autoIndentAct.setChecked(self.settings['autoIndent'])
        autoIndentAct.changed.connect(self._autoIndentChanged)
        backspaceUnindentAct = optionsMenu.addAction('Backspace unindent')
        backspaceUnindentAct.setCheckable(True)
        backspaceUnindentAct.setChecked(self.settings['backspaceUnindent'])
        backspaceUnindentAct.changed.connect(self._backspaceUnindentChanged)
        tabIndentsAct = optionsMenu.addAction('TAB indents')
        tabIndentsAct.setCheckable(True)
        tabIndentsAct.setChecked(self.settings['tabIndents'])
        tabIndentsAct.changed.connect(self._tabIndentsChanged)
        indentationGuidesAct = optionsMenu.addAction('Show indentation guides')
        indentationGuidesAct.setCheckable(True)
        indentationGuidesAct.setChecked(self.settings['indentationGuides'])
        indentationGuidesAct.changed.connect(self._indentationGuidesChanged)
        currentLineVisibleAct = optionsMenu.addAction('Highlight current line')
        currentLineVisibleAct.setCheckable(True)
        currentLineVisibleAct.setChecked(self.settings['currentLineVisible'])
        currentLineVisibleAct.changed.connect(self._currentLineVisibleChanged)
        jumpToFirstNonSpaceAct = optionsMenu.addAction(
            'HOME to first non-space')
        jumpToFirstNonSpaceAct.setCheckable(True)
        jumpToFirstNonSpaceAct.setChecked(self.settings['jumpToFirstNonSpace'])
        jumpToFirstNonSpaceAct.changed.connect(
            self._homeToFirstNonSpaceChanged)
        removeTrailingOnSpaceAct = optionsMenu.addAction(
            'Auto remove trailing spaces on save')
        removeTrailingOnSpaceAct.setCheckable(True)
        removeTrailingOnSpaceAct.setChecked(
            self.settings['removeTrailingOnSave'])
        removeTrailingOnSpaceAct.changed.connect(self._removeTrailingChanged)
        editorCalltipsAct = optionsMenu.addAction('Editor calltips')
        editorCalltipsAct.setCheckable(True)
        editorCalltipsAct.setChecked(self.settings['editorCalltips'])
        editorCalltipsAct.changed.connect(self._editorCalltipsChanged)
        clearDebugIOAct = optionsMenu.addAction(
            'Clear debug IO console on new session')
        clearDebugIOAct.setCheckable(True)
        clearDebugIOAct.setChecked(self.settings['clearDebugIO'])
        clearDebugIOAct.changed.connect(self._clearDebugIOChanged)
        showNavBarAct = optionsMenu.addAction('Show navigation bar')
        showNavBarAct.setCheckable(True)
        showNavBarAct.setChecked(self.settings['showNavigationBar'])
        showNavBarAct.changed.connect(self._showNavBarChanged)
        showCFNavBarAct = optionsMenu.addAction(
            'Show control flow navigation bar')
        showCFNavBarAct.setCheckable(True)
        showCFNavBarAct.setChecked(self.settings['showCFNavigationBar'])
        showCFNavBarAct.changed.connect(self._showCFNavBarChanged)
        showMainToolBarAct = optionsMenu.addAction('Show main toolbar')
        showMainToolBarAct.setCheckable(True)
        showMainToolBarAct.setChecked(self.settings['showMainToolBar'])
        showMainToolBarAct.changed.connect(self._showMainToolbarChanged)
        optionsMenu.addSeparator()
        tooltipsMenu = optionsMenu.addMenu("Tooltips")
        projectTooltipsAct = tooltipsMenu.addAction("&Project tab")
        projectTooltipsAct.setCheckable(True)
        projectTooltipsAct.setChecked(self.settings['projectTooltips'])
        projectTooltipsAct.changed.connect(self._projectTooltipsChanged)
        recentTooltipsAct = tooltipsMenu.addAction("&Recent tab")
        recentTooltipsAct.setCheckable(True)
        recentTooltipsAct.setChecked(self.settings['recentTooltips'])
        recentTooltipsAct.changed.connect(self._recentTooltipsChanged)
        classesTooltipsAct = tooltipsMenu.addAction("&Classes tab")
        classesTooltipsAct.setCheckable(True)
        classesTooltipsAct.setChecked(self.settings['classesTooltips'])
        classesTooltipsAct.changed.connect(self._classesTooltipsChanged)
        functionsTooltipsAct = tooltipsMenu.addAction("&Functions tab")
        functionsTooltipsAct.setCheckable(True)
        functionsTooltipsAct.setChecked(self.settings['functionsTooltips'])
        functionsTooltipsAct.changed.connect(self._functionsTooltipsChanged)
        outlineTooltipsAct = tooltipsMenu.addAction("&Outline tab")
        outlineTooltipsAct.setCheckable(True)
        outlineTooltipsAct.setChecked(self.settings['outlineTooltips'])
        outlineTooltipsAct.changed.connect(self._outlineTooltipsChanged)
        findNameTooltipsAct = tooltipsMenu.addAction("Find &name dialog")
        findNameTooltipsAct.setCheckable(True)
        findNameTooltipsAct.setChecked(self.settings['findNameTooltips'])
        findNameTooltipsAct.changed.connect(self._findNameTooltipsChanged)
        findFileTooltipsAct = tooltipsMenu.addAction("Find fi&le dialog")
        findFileTooltipsAct.setCheckable(True)
        findFileTooltipsAct.setChecked(self.settings['findFileTooltips'])
        findFileTooltipsAct.changed.connect(self._findFileTooltipsChanged)
        editorTooltipsAct = tooltipsMenu.addAction("&Editor tabs")
        editorTooltipsAct.setCheckable(True)
        editorTooltipsAct.setChecked(self.settings['editorTooltips'])
        editorTooltipsAct.changed.connect(self._editorTooltipsChanged)

        openTabsMenu = optionsMenu.addMenu("Open tabs button")
        self.__navigationSortGroup = QActionGroup(self)
        self.__alphasort = openTabsMenu.addAction("Sort alphabetically")
        self.__alphasort.setCheckable(True)
        self.__alphasort.setData(-1)
        self.__alphasort.setActionGroup(self.__navigationSortGroup)
        self.__tabsort = openTabsMenu.addAction("Tab order sort")
        self.__tabsort.setCheckable(True)
        self.__tabsort.setData(-2)
        self.__tabsort.setActionGroup(self.__navigationSortGroup)
        if self.settings['tablistsortalpha']:
            self.__alphasort.setChecked(True)
        else:
            self.__tabsort.setChecked(True)
        openTabsMenu.addSeparator()
        tabOrderPreservedAct = openTabsMenu.addAction(
            "Tab order preserved on selection")
        tabOrderPreservedAct.setCheckable(True)
        tabOrderPreservedAct.setData(0)
        tabOrderPreservedAct.setChecked(self.settings['taborderpreserved'])
        tabOrderPreservedAct.changed.connect(self._tabOrderPreservedChanged)
        openTabsMenu.triggered.connect(self._openTabsMenuTriggered)

        optionsMenu.addSeparator()
        themesMenu = optionsMenu.addMenu("Themes")
        availableThemes = self.__buildThemesList()
        for theme in availableThemes:
            themeAct = themesMenu.addAction(theme[1])
            themeAct.setData(theme[0])
            if theme[0] == self.settings['skin']:
                font = themeAct.font()
                font.setBold(True)
                themeAct.setFont(font)
        themesMenu.triggered.connect(self._onTheme)

        styleMenu = optionsMenu.addMenu("Styles")
        availableStyles = QStyleFactory.keys()
        self.__styles = []
        for style in availableStyles:
            styleAct = styleMenu.addAction(style)
            styleAct.setData(style)
            self.__styles.append((str(style), styleAct))
        styleMenu.triggered.connect(self._onStyle)
        styleMenu.aboutToShow.connect(self.__styleAboutToShow)

        fontFaceMenu = optionsMenu.addMenu("Mono font family")
        self.__fontFaceGroup = QActionGroup(self)
        skin = GlobalData().skin
        currentFont = skin['monoFont'].family()
        self.__fonts = []
        for fontFace in getMonospaceFontList():
            faceAct = fontFaceMenu.addAction(fontFace)
            faceAct.setData(fontFace)
            faceAct.setCheckable(True)
            faceAct.setActionGroup(self.__fontFaceGroup)
            faceAct.setChecked(currentFont == fontFace)
            self.__fonts.append((fontFace, faceAct))
        fontFaceMenu.triggered.connect(self._onMonoFont)
        fontFaceMenu.aboutToShow.connect(self.__fontAboutToShow)

        # The plugins menu
        self.__pluginsMenu = QMenu("P&lugins", self)
        self._recomposePluginMenu()

        # The Help menu
        helpMenu = QMenu("&Help", self)
        helpMenu.aboutToShow.connect(self.__helpAboutToShow)
        helpMenu.aboutToHide.connect(self.__helpAboutToHide)
        self.__shortcutsAct = helpMenu.addAction(
            getIcon('shortcutsmenu.png'),
            '&Major shortcuts', self.em.onHelp, 'F1')
        self.__contextHelpAct = helpMenu.addAction(
            getIcon('helpviewer.png'),
            'Current &word help', self._onContextHelp)
        self.__callHelpAct = helpMenu.addAction(
            getIcon('helpviewer.png'),
            '&Current call help', self._onCallHelp)
        helpMenu.addSeparator()
        self.__allShotcutsAct = helpMenu.addAction(
            getIcon('allshortcutsmenu.png'),
            '&All shortcuts (web page)', self._onAllShortcurs)
        self.__homePageAct = helpMenu.addAction(
            getIcon('homepagemenu.png'),
            'Codimension &home page', self._onHomePage)
        helpMenu.addSeparator()
        self.__aboutAct = helpMenu.addAction(
            getIcon("logo.png"), "A&bout codimension", self._onAbout)

        menuBar = self.menuBar()
        menuBar.addMenu(prjMenu)
        menuBar.addMenu(tabMenu)
        menuBar.addMenu(editMenu)
        menuBar.addMenu(searchMenu)
        menuBar.addMenu(self.__runMenu)
        menuBar.addMenu(dbgMenu)
        menuBar.addMenu(toolsMenu)
        menuBar.addMenu(diagramsMenu)
        menuBar.addMenu(viewMenu)
        menuBar.addMenu(optionsMenu)
        menuBar.addMenu(self.__pluginsMenu)
        menuBar.addMenu(helpMenu)

    def __prjAboutToShow(self):
        """Triggered when project menu is about to show"""
        self.__newProjectAct.setEnabled(not self.debugMode)
        self.__openProjectAct.setEnabled(not self.debugMode)
        self._unloadProjectAct.setEnabled(not self.debugMode)

        # Recent projects part
        self.__recentPrjMenu.clear()
        addedCount = 0
        currentPrj = GlobalData().project.fileName
        for item in self.settings['recentProjects']:
            if item != currentPrj:
                addedCount += 1
                act = self.__recentPrjMenu.addAction(
                    self.__getAccelerator(addedCount) +
                    os.path.basename(item).replace(".cdm3", ""))
                act.setData(item)
                act.setEnabled(not self.debugMode and os.path.exists(item))

        self.__recentPrjMenu.setEnabled(addedCount > 0)

        if GlobalData().project.isLoaded():
            # Template part
            exists = os.path.exists(getProjectTemplateFile())
            self._prjTemplateMenu.setEnabled(True)
            self.__createPrjTemplateAct.setEnabled(not exists)
            self.__editPrjTemplateAct.setEnabled(exists)
            self.__delPrjTemplateAct.setEnabled(exists)
        else:
            self._prjTemplateMenu.setEnabled(False)

    def __prjAboutToHide(self):
        """Triggered when project menu is about to hide"""
        self.__newProjectAct.setEnabled(True)
        self.__openProjectAct.setEnabled(True)

    def __tabAboutToShow(self):
        """Triggered when tab menu is about to show"""
        plainTextBuffer = self.__isPlainTextBuffer()
        isPythonBuffer = self._isPythonBuffer()
        isGeneratedDiagram = self.__isGeneratedDiagram()
        isProfileViewer = self.__isProfileViewer()

        self.__cloneTabAct.setEnabled(plainTextBuffer)
        self.__closeOtherTabsAct.setEnabled(self.em.closeOtherAvailable())
        self.__saveFileAct.setEnabled(
            plainTextBuffer or isGeneratedDiagram or isProfileViewer)
        self.__saveFileAsAct.setEnabled(
            plainTextBuffer or isGeneratedDiagram or isProfileViewer)
        self.__closeTabAct.setEnabled(self.em.isTabClosable())
        self.__tabJumpToDefAct.setEnabled(isPythonBuffer)
        self.__calltipAct.setEnabled(isPythonBuffer)
        self.__tabJumpToScopeBeginAct.setEnabled(isPythonBuffer)
        self.__tabOpenImportAct.setEnabled(isPythonBuffer)
        if plainTextBuffer:
            widget = self.em.currentWidget()
            editor = widget.getEditor()
            self.__openAsFileAct.setEnabled(editor.openAsFileAvailable())
            self.__downloadAndShowAct.setEnabled(
                editor.downloadAndShowAvailable())
            self.__openInBrowserAct.setEnabled(
                editor.downloadAndShowAvailable())
        else:
            self.__openAsFileAct.setEnabled(False)
            self.__downloadAndShowAct.setEnabled(False)
            self.__openInBrowserAct.setEnabled(False)

        self.__highlightInPrjAct.setEnabled(
            self.em.isHighlightInPrjAvailable())
        self.__highlightInFSAct.setEnabled(
            self.em.isHighlightInFSAvailable())
        self.__highlightInOutlineAct.setEnabled(isPythonBuffer)

        self.__closeTabAct.setShortcut("Ctrl+F4")
        self.__tabJumpToDefAct.setShortcut("Ctrl+\\")
        self.__calltipAct.setShortcut("Ctrl+/")
        self.__tabJumpToScopeBeginAct.setShortcut("Alt+U")
        self.__tabOpenImportAct.setShortcut("Ctrl+I")
        self.__highlightInOutlineAct.setShortcut("Ctrl+B")

        self.__recentFilesMenu.clear()
        addedCount = 0

        for item in GlobalData().project.recentFiles:
            addedCount += 1
            act = self.__recentFilesMenu.addAction(
                self.__getAccelerator(addedCount) + item)
            act.setData(item)
            act.setEnabled(os.path.exists(item))

        self.__recentFilesMenu.setEnabled(addedCount > 0)

    def __searchAboutToShow(self):
        """Triggered when search menu is about to show"""
        isPlainTextBuffer = self.__isPlainTextBuffer()
        isPythonBuffer = self._isPythonBuffer()
        currentWidget = self.em.currentWidget()

        self.__findOccurencesAct.setEnabled(
            isPythonBuffer and os.path.isabs(currentWidget.getFileName()))
        self.__goToLineAct.setEnabled(isPlainTextBuffer)
        self.__findAct.setEnabled(isPlainTextBuffer)
        self.__replaceAct.setEnabled(
            isPlainTextBuffer and
            currentWidget.getType() !=
            MainWindowTabWidgetBase.VCSAnnotateViewer)
        self.__findNextAct.setEnabled(isPlainTextBuffer)
        self.__findPrevAct.setEnabled(isPlainTextBuffer)

        self.__findOccurencesAct.setShortcut("Ctrl+]")
        self.__goToLineAct.setShortcut("Ctrl+G")
        self.__findAct.setShortcut("Ctrl+F")
        self.__replaceAct.setShortcut("Ctrl+R")
        self.__findNextAct.setShortcut("Ctrl+.")
        self.__findPrevAct.setShortcut("Ctrl+,")

    def __diagramsAboutToShow(self):
        """Triggered when the diagrams menu is about to show"""
        isPythonBuffer = self._isPythonBuffer()
        currentWidget = self.em.currentWidget()

        enabled = isPythonBuffer and \
            currentWidget.getType() != \
            MainWindowTabWidgetBase.VCSAnnotateViewer
        self.__tabImportDgmAct.setEnabled(enabled)
        self.__tabImportDgmDlgAct.setEnabled(enabled)

    def __runAboutToShow(self):
        """Triggered when the run menu is about to show"""
        projectLoaded = GlobalData().project.isLoaded()
        prjScriptValid = GlobalData().isProjectScriptValid()

        enabled = projectLoaded and prjScriptValid and not self.debugMode
        self.__prjRunAct.setEnabled(enabled)
        self.__prjRunDlgAct.setEnabled(enabled)

        self.__prjProfileAct.setEnabled(enabled)
        self.__prjProfileDlgAct.setEnabled(enabled)

    def __debugAboutToShow(self):
        """Triggered when the debug menu is about to show"""
        projectLoaded = GlobalData().project.isLoaded()
        prjScriptValid = GlobalData().isProjectScriptValid()

        enabled = projectLoaded and prjScriptValid and not self.debugMode
        self._prjDebugAct.setEnabled(enabled)
        self._prjDebugDlgAct.setEnabled(enabled)

    def __toolsAboutToShow(self):
        """Triggered when tools menu is about to show"""
        self.__tabLineCounterAct.setEnabled(self._isPythonBuffer())

        if GlobalData().project.isLoaded():
            self.__unusedClassesAct.setEnabled(
                self.classesViewer.getItemCount() > 0)
            self.__unusedFunctionsAct.setEnabled(
                self.functionsViewer.getItemCount() > 0)
            self.__unusedGlobalsAct.setEnabled(
                self.globalsViewer.getItemCount() > 0)
        else:
            self.__unusedClassesAct.setEnabled(False)
            self.__unusedFunctionsAct.setEnabled(False)
            self.__unusedGlobalsAct.setEnabled(False)

    def __viewAboutToShow(self):
        """Triggered when view menu is about to show"""
        isPlainTextBuffer = self.__isPlainTextBuffer()
        isGraphicsBuffer = self.__isGraphicsBuffer()
        isGeneratedDiagram = self.__isGeneratedDiagram()
        isProfileViewer = self.__isProfileViewer()
        isDiffViewer = self.__isDiffViewer()
        zoomEnabled = isPlainTextBuffer or isGraphicsBuffer or \
                      isGeneratedDiagram or isDiffViewer
        if not zoomEnabled and isProfileViewer:
            currentWidget = self.em.currentWidget()
            zoomEnabled = currentWidget.isZoomApplicable()
        self.__zoomInAct.setEnabled(zoomEnabled)
        self.__zoomOutAct.setEnabled(zoomEnabled)
        self.__zoom11Act.setEnabled(zoomEnabled)

        self.__zoomInAct.setShortcut("Ctrl+=")
        self.__zoomOutAct.setShortcut("Ctrl+-")
        self.__zoom11Act.setShortcut("Ctrl+0")

        self.__debugBarAct.setEnabled(self.debugMode)

    def __optionsAboutToShow(self):
        """Triggered when the options menu is about to show"""
        exists = os.path.exists(getIDETemplateFile())
        self.__ideCreateTemplateAct.setEnabled(not exists)
        self.__ideEditTemplateAct.setEnabled(exists)
        self.__ideDelTemplateAct.setEnabled(exists)

    def __helpAboutToShow(self):
        """Triggered when help menu is about to show"""
        isPythonBuffer = self._isPythonBuffer()
        self.__contextHelpAct.setEnabled(isPythonBuffer)
        self.__callHelpAct.setEnabled(isPythonBuffer)

        self.__contextHelpAct.setShortcut("Ctrl+F1")
        self.__callHelpAct.setShortcut("Ctrl+Shift+F1")

    def __editAboutToHide(self):
        """Triggered when edit menu is about to hide"""
        self.__undoAct.setShortcut("")
        self.__redoAct.setShortcut("")
        self.__cutAct.setShortcut("")
        self.__copyAct.setShortcut("")
        self.__pasteAct.setShortcut("")
        self.__selectAllAct.setShortcut("")
        self.__commentAct.setShortcut("")
        self.__duplicateAct.setShortcut("")
        self.__autocompleteAct.setShortcut("")

    def __tabAboutToHide(self):
        """Triggered when tab menu is about to hide"""
        self.__closeTabAct.setShortcut("")
        self.__tabJumpToDefAct.setShortcut("")
        self.__calltipAct.setShortcut("")
        self.__tabJumpToScopeBeginAct.setShortcut("")
        self.__tabOpenImportAct.setShortcut("")
        self.__highlightInOutlineAct.setShortcut("")

        self.__saveFileAct.setEnabled(True)
        self.__saveFileAsAct.setEnabled(True)

    def __searchAboutToHide(self):
        """Triggered when search menu is about to hide"""
        self.__findOccurencesAct.setShortcut("")
        self.__goToLineAct.setShortcut("")
        self.__findAct.setShortcut("")
        self.__replaceAct.setShortcut("")
        self.__findNextAct.setShortcut("")
        self.__findPrevAct.setShortcut("")

    def __viewAboutToHide(self):
        """Triggered when view menu is about to hide"""
        self.__zoomInAct.setShortcut("")
        self.__zoomOutAct.setShortcut("")
        self.__zoom11Act.setShortcut("")

    def __helpAboutToHide(self):
        """Triggered when help menu is about to hide"""
        self.__contextHelpAct.setShortcut("")
        self.__callHelpAct.setShortcut("")

    def __editAboutToShow(self):
        """Triggered when edit menu is about to show"""
        isPlainBuffer = self.__isPlainTextBuffer()
        isPythonBuffer = self._isPythonBuffer()
        currentWidget = self.em.currentWidget()
        if isPlainBuffer:
            editor = currentWidget.getEditor()

        self.__undoAct.setShortcut("Ctrl+Z")
        self.__undoAct.setEnabled(isPlainBuffer and
                                  editor.document().isUndoAvailable())
        self.__redoAct.setShortcut("Ctrl+Y")
        self.__redoAct.setEnabled(isPlainBuffer and
                                  editor.document().isRedoAvailable())
        self.__cutAct.setShortcut("Ctrl+X")
        self.__cutAct.setEnabled(isPlainBuffer and not editor.isReadOnly())
        self.__copyAct.setShortcut("Ctrl+C")
        self.__copyAct.setEnabled(self.em.isCopyAvailable())
        self.__pasteAct.setShortcut("Ctrl+V")
        self.__pasteAct.setEnabled(isPlainBuffer and
                                   QApplication.clipboard().text() != "" and
                                   not editor.isReadOnly())
        self.__selectAllAct.setShortcut("Ctrl+A")
        self.__selectAllAct.setEnabled(isPlainBuffer)
        self.__commentAct.setShortcut("Ctrl+M")
        self.__commentAct.setEnabled(isPythonBuffer and
                                     not editor.isReadOnly())
        self.__duplicateAct.setShortcut("Ctrl+D")
        self.__duplicateAct.setEnabled(isPlainBuffer and
                                       not editor.isReadOnly())
        self.__autocompleteAct.setShortcut("Ctrl+Space")
        self.__autocompleteAct.setEnabled(isPlainBuffer and
                                          not editor.isReadOnly())
        self.__expandTabsAct.setEnabled(isPlainBuffer and
                                        not editor.isReadOnly())
        self.__trailingSpacesAct.setEnabled(isPlainBuffer and
                                            not editor.isReadOnly())

    def __onDumpDbgSettingsAboutToShow(self):
        """Dump debug settings is about to show"""
        scriptAvailable = self._dumpScriptDbgSettingsAvailable()
        self.__debugDumpScriptSettingsAct.setEnabled(scriptAvailable)
        self.__debugDumpScriptSettingsEnvAct.setEnabled(scriptAvailable)

        projectAvailable = self.__dumpProjectDbgSettingsAvailable()
        self.__debugDumpProjectSettingsAct.setEnabled(projectAvailable)
        self.__debugDumpProjectSettingsEnvAct.setEnabled(projectAvailable)

    def __styleAboutToShow(self):
        """Style menu is about to show"""
        currentStyle = self.settings['style'].lower()
        for item in self.__styles:
            font = item[1].font()
            font.setBold(item[0].lower() == currentStyle)
            item[1].setFont(font)

    def __fontAboutToShow(self):
        """Font menu is about to show"""
        skin = GlobalData().skin
        currentFont = skin['monoFont'].family().lower()
        for item in self.__fonts:
            item[1].setChecked(item[0].lower() == currentFont)

    @staticmethod
    def __buildThemesList():
        """Builds a list of themes - system wide and the user local"""
        localSkinsDir = os.path.normpath(str(QDir.homePath())) + \
                        os.path.sep + CONFIG_DIR + os.path.sep + "skins" + \
                        os.path.sep
        return getThemesList(localSkinsDir)

    def _recomposePluginMenu(self):
        """Recomposes the plugin menu"""
        self.__pluginsMenu.clear()
        self.__pluginsMenu.addAction(getIcon('pluginmanagermenu.png'),
                                     'Plugin &manager', self._onPluginManager)
        if self._pluginMenus:
            self.__pluginsMenu.addSeparator()
        for path in self._pluginMenus:
            self.__pluginsMenu.addMenu(self._pluginMenus[path])

    @staticmethod
    def __getAccelerator(count):
        """Provides an accelerator text for a menu item"""
        if count < 10:
            return "&" + str(count) + ".  "
        return "&" + chr(count - 10 + ord('a')) + ".  "

    def __isPlainTextBuffer(self):
        """Provides if saving is enabled"""
        currentWidget = self.em.currentWidget()
        if currentWidget is None:
            return False
        return currentWidget.getType() in \
            [MainWindowTabWidgetBase.PlainTextEditor,
             MainWindowTabWidgetBase.VCSAnnotateViewer]

    def __isGraphicsBuffer(self):
        """True if is pictures viewer"""
        currentWidget = self.em.currentWidget()
        if currentWidget is None:
            return False
        return currentWidget.getType() == MainWindowTabWidgetBase.PictureViewer

    def __isGeneratedDiagram(self):
        """True if this is a generated diagram"""
        currentWidget = self.em.currentWidget()
        if currentWidget is None:
            return False
        if currentWidget.getType() == MainWindowTabWidgetBase.GeneratedDiagram:
            return True
        if currentWidget.getType() == MainWindowTabWidgetBase.ProfileViewer:
            if currentWidget.isDiagramActive():
                return True
        return False

    def __isProfileViewer(self):
        """True if this is a profile viewer"""
        currentWidget = self.em.currentWidget()
        if currentWidget is None:
            return False
        return currentWidget.getType() == MainWindowTabWidgetBase.ProfileViewer

    def __isDiffViewer(self):
        """True if this is a diff viewer"""
        currentWidget = self.em.currentWidget()
        if currentWidget is None:
            return False
        return currentWidget.getType() == MainWindowTabWidgetBase.DiffViewer
