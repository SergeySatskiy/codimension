#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010  Sergey Satskiy <sergey.satskiy@gmail.com>
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
# $Id$
#


""" PythonTidy settings dialog """

import logging
from PyQt4.QtCore import Qt
from PyQt4.QtGui import ( QDialog, QDialogButtonBox, QVBoxLayout, QLabel,
                          QFontMetrics, QLineEdit, QHBoxLayout, QGridLayout,
                          QTextEdit, QCheckBox, QGroupBox, QSizePolicy,
                          QRadioButton )
from utils.globals import GlobalData


class TidySettingsDialog( QDialog ):
    " PythonTidy.py script settings dialog "

    def __init__( self, settings, path, parent = None ):
        QDialog.__init__( self, parent )

        self.__settings = settings
        self.__path = path

        self.__createLayout()
        self.setWindowTitle( "PythonTidy settings" )
        return

    def __createLayout( self ):
        """ Creates the dialog layout """

        self.resize( 700, 300 )
        self.setSizeGripEnabled( True )

        layout = QVBoxLayout( self )
        gridLayout = QGridLayout()

        # Columns
        colsLabel = QLabel( "Columns" )
        self.__colsEdit = QLineEdit()
        self.__colsEdit.setText( str( self.__settings.settings[ "COL_LIMIT" ] ) )
        self.__colsEdit.setToolTip( self.__settings.getDescription( "COL_LIMIT" ) )
        self.__colsEdit.textChanged.connect( self.__validate )
        gridLayout.addWidget( colsLabel, 0, 0, 1, 1 )
        gridLayout.addWidget( self.__colsEdit, 0, 1, 1, 1 )
        font = self.__colsEdit.font()
        font.setFamily( GlobalData().skin.baseMonoFontFace )
        self.__colsEdit.setFont( font )

        # Assignment
        assignmentLabel = QLabel( "Assignment" )
        self.__assignmentEdit = QLineEdit()
        self.__assignmentEdit.setText( self.__settings.settings[ "ASSIGNMENT" ] )
        self.__assignmentEdit.setToolTip( self.__settings.getDescription( "ASSIGNMENT" ) )
        self.__assignmentEdit.textChanged.connect( self.__validate )
        gridLayout.addWidget( assignmentLabel, 0, 3, 1, 1 )
        gridLayout.addWidget( self.__assignmentEdit, 0, 4, 1, 1 )
        self.__assignmentEdit.setFont( font )

        # Function parameters assignment
        funcAssignLabel = QLabel( "Function params\nassignment" )
        self.__funcAssignEdit = QLineEdit()
        self.__funcAssignEdit.setText( self.__settings.settings[ "FUNCTION_PARAM_ASSIGNMENT" ] )
        self.__funcAssignEdit.setToolTip( self.__settings.getDescription( "FUNCTION_PARAM_ASSIGNMENT" ) )
        self.__funcAssignEdit.textChanged.connect( self.__validate )
        gridLayout.addWidget( funcAssignLabel, 1, 0, 1, 1 )
        gridLayout.addWidget( self.__funcAssignEdit, 1, 1, 1, 1 )
        self.__funcAssignEdit.setFont( font )

        # Dictionary separator
        dictSepLabel = QLabel( "Dictionary separator" )
        self.__dictSepEdit = QLineEdit()
        self.__dictSepEdit.setText( self.__settings.settings[ "DICT_COLON" ] )
        self.__dictSepEdit.setToolTip( self.__settings.getDescription( "DICT_COLON" ) )
        self.__dictSepEdit.textChanged.connect( self.__validate )
        gridLayout.addWidget( dictSepLabel, 1, 3, 1, 1 )
        gridLayout.addWidget( self.__dictSepEdit, 1, 4, 1, 1 )
        self.__dictSepEdit.setFont( font )

        # Slice separator
        sliceSepLabel = QLabel( "Slice separator" )
        self.__sliceSepEdit = QLineEdit()
        self.__sliceSepEdit.setText( self.__settings.settings[ "SLICE_COLON" ] )
        self.__sliceSepEdit.setToolTip( self.__settings.getDescription( "SLICE_COLON" ) )
        self.__sliceSepEdit.textChanged.connect( self.__validate )
        gridLayout.addWidget( sliceSepLabel, 2, 0, 1, 1 )
        gridLayout.addWidget( self.__sliceSepEdit, 2, 1, 1, 1 )
        self.__sliceSepEdit.setFont( font )

        # Interpreter
        inLabel = QLabel( "Interpreter" )
        self.__inEdit = QLineEdit()
        self.__inEdit.setText( self.__settings.settings[ "SHEBANG" ] )
        self.__inEdit.setToolTip( self.__settings.getDescription( "SHEBANG" ) )
        self.__inEdit.textChanged.connect( self.__validate )
        gridLayout.addWidget( inLabel, 2, 3, 1, 1 )
        gridLayout.addWidget( self.__inEdit, 2, 4, 1, 1 )
        self.__inEdit.setFont( font )

        # Coding spec
        codingLabel = QLabel( "Output encoding" )
        self.__outCodingEdit = QLineEdit()
        self.__outCodingEdit.setText( self.__settings.settings[ "CODING" ] )
        self.__outCodingEdit.setToolTip( self.__settings.getDescription( "CODING" ) )
        self.__outCodingEdit.textChanged.connect( self.__validate )
        gridLayout.addWidget( codingLabel, 3, 0, 1, 1 )
        gridLayout.addWidget( self.__outCodingEdit, 3, 1, 1, 1 )
        self.__outCodingEdit.setFont( font )

        # Src coding comment
        srcCodingLabel = QLabel( "File encoding\ncomment" )
        self.__srcCodingEdit = QLineEdit()
        self.__srcCodingEdit.setText( self.__settings.settings[ "CODING_SPEC" ] )
        self.__srcCodingEdit.setToolTip( self.__settings.getDescription( "CODING_SPEC" ) )
        self.__srcCodingEdit.textChanged.connect( self.__validate )
        gridLayout.addWidget( srcCodingLabel, 3, 3, 1, 1 )
        gridLayout.addWidget( self.__srcCodingEdit, 3, 4, 1, 1 )
        self.__srcCodingEdit.setFont( font )

        layout.addLayout( gridLayout )


        # Boilerplate
        boilLabel = QLabel( "Boilerplate  " )
        boilLabel.setAlignment( Qt.AlignTop )
        self.__boilEdit = QTextEdit()
        self.__boilEdit.setPlainText( self.__settings.settings[ "BOILERPLATE" ] )
        self.__boilEdit.setToolTip( self.__settings.getDescription( "BOILERPLATE" ) )
        self.__boilEdit.setTabChangesFocus( True )
        self.__boilEdit.setAcceptRichText( False )
        self.__boilEdit.setFont( font )
        self.__boilEdit.textChanged.connect( self.__validate )
        boilLayout = QHBoxLayout()
        boilLayout.addWidget( boilLabel )
        boilLayout.addWidget( self.__boilEdit )
        layout.addLayout( boilLayout )



        # Now check boxes and radio buttons
        cbGridLayout = QGridLayout()
        self.__keepBlanks = QCheckBox( "Keep blank lines" )
        self.__keepBlanks.setChecked( self.__settings.settings[ "KEEP_BLANK_LINES" ] )
        self.__keepBlanks.setToolTip( self.__settings.getDescription( "KEEP_BLANK_LINES" ) )
        cbGridLayout.addWidget( self.__keepBlanks, 0, 0, 1, 1 )

        self.__addBlanks = QCheckBox( "Add blank lines around comments" )
        self.__addBlanks.setChecked( self.__settings.settings[ "ADD_BLANK_LINES_AROUND_COMMENTS" ] )
        self.__addBlanks.setToolTip( self.__settings.getDescription( "ADD_BLANK_LINES_AROUND_COMMENTS" ) )
        cbGridLayout.addWidget( self.__addBlanks, 0, 2, 1, 1 )

        self.__justifyDoc = QCheckBox( "Left justify doc strings" )
        self.__justifyDoc.setChecked( self.__settings.settings[ "LEFTJUST_DOC_STRINGS" ] )
        self.__justifyDoc.setToolTip( self.__settings.getDescription( "LEFTJUST_DOC_STRINGS" ) )
        cbGridLayout.addWidget( self.__justifyDoc, 1, 0, 1, 1 )

        self.__wrapDoc = QCheckBox( "Wrap long doc strings" )
        self.__wrapDoc.setChecked( self.__settings.settings[ "WRAP_DOC_STRINGS" ] )
        self.__wrapDoc.setToolTip( self.__settings.getDescription( "WRAP_DOC_STRINGS" ) )
        cbGridLayout.addWidget( self.__wrapDoc, 1, 2, 1, 1 )

        self.__recodeStrings = QCheckBox( "Try to decode strings" )
        self.__recodeStrings.setChecked( self.__settings.settings[ "RECODE_STRINGS" ] )
        self.__recodeStrings.setToolTip( self.__settings.getDescription( "RECODE_STRINGS" ) )
        cbGridLayout.addWidget( self.__recodeStrings, 2, 0, 1, 1 )

        self.__splitStrings = QCheckBox( "Split long strings" )
        self.__splitStrings.setChecked( self.__settings.settings[ "CAN_SPLIT_STRINGS" ] )
        self.__splitStrings.setToolTip( self.__settings.getDescription( "CAN_SPLIT_STRINGS" ) )
        cbGridLayout.addWidget( self.__splitStrings, 2, 2, 1, 1 )

        self.__keepUnassignedConst = QCheckBox( "Keep unassigned constants" )
        self.__keepUnassignedConst.setChecked( self.__settings.settings[ "KEEP_UNASSIGNED_CONSTANTS" ] )
        self.__keepUnassignedConst.setToolTip( self.__settings.getDescription( "KEEP_UNASSIGNED_CONSTANTS" ) )
        cbGridLayout.addWidget( self.__keepUnassignedConst, 3, 0, 1, 1 )

        self.__parenTuple = QCheckBox( "Parenthesize tuple display" )
        self.__parenTuple.setChecked( self.__settings.settings[ "PARENTHESIZE_TUPLE_DISPLAY" ] )
        self.__parenTuple.setToolTip( self.__settings.getDescription( "PARENTHESIZE_TUPLE_DISPLAY" ) )
        cbGridLayout.addWidget( self.__parenTuple, 3, 2, 1, 1 )

        self.__javaListDedent = QCheckBox( "Java style list dedent" )
        self.__javaListDedent.setChecked( self.__settings.settings[ "JAVA_STYLE_LIST_DEDENT" ] )
        self.__javaListDedent.setToolTip( self.__settings.getDescription( "JAVA_STYLE_LIST_DEDENT" ) )
        cbGridLayout.addWidget( self.__javaListDedent, 4, 0, 1, 1 )

        layout.addLayout( cbGridLayout )


        # Quotes radio buttons
        quotesGroupbox = QGroupBox( "Quotes" )
        sizePolicy = QSizePolicy( QSizePolicy.Expanding, QSizePolicy.Preferred )
        sizePolicy.setHorizontalStretch( 0 )
        sizePolicy.setVerticalStretch( 0 )
        sizePolicy.setHeightForWidth( \
                        quotesGroupbox.sizePolicy().hasHeightForWidth() )
        quotesGroupbox.setSizePolicy( sizePolicy )

        layoutQG = QVBoxLayout( quotesGroupbox )
        self.__use1RButton = QRadioButton( "Use apostrophes instead of quotes for string literals",
                                           quotesGroupbox )
        layoutQG.addWidget( self.__use1RButton )
        self.__use2RButton = QRadioButton( "Use quotes instead of apostrophes for string literals",
                                           quotesGroupbox )
        layoutQG.addWidget( self.__use2RButton )
        self.__useAsIsRButton = QRadioButton( "Do not make changes",
                                              quotesGroupbox )
        layoutQG.addWidget( self.__useAsIsRButton )
        use1 = self.__settings.settings[ "SINGLE_QUOTED_STRINGS" ]
        use2 = self.__settings.settings[ "DOUBLE_QUOTED_STRINGS" ]
        if use1:
            self.__use1RButton.setChecked( True )
        elif use2:
            self.__use2RButton.setChecked( True )
        else:
            self.__useAsIsRButton.setChecked( True )
        layout.addWidget( quotesGroupbox )

        fontMetrics = QFontMetrics( font )
        editWidth = fontMetrics.width( "iso8859-10  " ) + 20
        self.__colsEdit.setFixedWidth( editWidth )
        self.__funcAssignEdit.setFixedWidth( editWidth )
        self.__sliceSepEdit.setFixedWidth( editWidth )
        self.__outCodingEdit.setFixedWidth( editWidth )

        # Buttons at the bottom
        buttonBox = QDialogButtonBox( self )
        buttonBox.setOrientation( Qt.Horizontal )
        buttonBox.setStandardButtons( QDialogButtonBox.Cancel )
        self.__resetButton = buttonBox.addButton( "Reset to Default",
                                                  QDialogButtonBox.ActionRole )
        self.__resetButton.setToolTip( "Mostly as recommended by PEP 8 / PEP 308" )
        self.__resetButton.clicked.connect( self.__reset )
        self.__tidyButton = buttonBox.addButton( "Tidy",
                                                 QDialogButtonBox.ActionRole )
        self.__tidyButton.setToolTip( "Save settings and run PythonTidy" )
        self.__tidyButton.setDefault( True )
        self.__tidyButton.clicked.connect( self.__saveAndAccept )
        layout.addWidget( buttonBox )

        buttonBox.rejected.connect( self.close )
        return

    def __reset( self ):
        " Resets the values to default "

        self.__colsEdit.setText( str( self.__settings.getDefaultValue( "COL_LIMIT" ) ) )
        self.__assignmentEdit.setText( self.__settings.getDefaultValue( "ASSIGNMENT" ) )
        self.__funcAssignEdit.setText( self.__settings.getDefaultValue( "FUNCTION_PARAM_ASSIGNMENT" ) )
        self.__dictSepEdit.setText( self.__settings.getDefaultValue( "DICT_COLON" ) )
        self.__sliceSepEdit.setText( self.__settings.getDefaultValue( "SLICE_COLON" ) )
        self.__inEdit.setText( self.__settings.getDefaultValue( "SHEBANG" ) )
        self.__outCodingEdit.setText( self.__settings.getDefaultValue( "CODING" ) )
        self.__srcCodingEdit.setText( self.__settings.getDefaultValue( "CODING_SPEC" ) )
        self.__boilEdit.setPlainText( self.__settings.getDefaultValue( "BOILERPLATE" ) )
        self.__keepBlanks.setChecked( self.__settings.getDefaultValue( "KEEP_BLANK_LINES" ) )
        self.__addBlanks.setChecked( self.__settings.getDefaultValue( "ADD_BLANK_LINES_AROUND_COMMENTS" ) )
        self.__justifyDoc.setChecked( self.__settings.getDefaultValue( "LEFTJUST_DOC_STRINGS" ) )
        self.__wrapDoc.setChecked( self.__settings.getDefaultValue( "WRAP_DOC_STRINGS" ) )
        self.__recodeStrings.setChecked( self.__settings.getDefaultValue( "RECODE_STRINGS" ) )
        self.__splitStrings.setChecked( self.__settings.getDefaultValue( "CAN_SPLIT_STRINGS" ) )
        self.__keepUnassignedConst.setChecked( self.__settings.getDefaultValue( "KEEP_UNASSIGNED_CONSTANTS" ) )
        self.__parenTuple.setChecked( self.__settings.getDefaultValue( "PARENTHESIZE_TUPLE_DISPLAY" ) )
        self.__javaListDedent.setChecked( self.__settings.getDefaultValue( "JAVA_STYLE_LIST_DEDENT" ) )

        use1 = self.__settings.getDefaultValue( "SINGLE_QUOTED_STRINGS" )
        use2 = self.__settings.getDefaultValue( "DOUBLE_QUOTED_STRINGS" )
        if use1:
            self.__use1RButton.setChecked( True )
            self.__use2RButton.setChecked( False )
            self.__useAsIsRButton.setChecked( False )
        elif use2:
            self.__use1RButton.setChecked( False )
            self.__use2RButton.setChecked( True )
            self.__useAsIsRButton.setChecked( False )
        else:
            self.__use1RButton.setChecked( False )
            self.__use2RButton.setChecked( False )
            self.__useAsIsRButton.setChecked( True )

        self.__validate()
        return

    @staticmethod
    def __setValid( field, value ):
        " Changes the field background depending on the validity "
        if value:
            field.setStyleSheet( "" )
        else:
            if isinstance( field, QLineEdit ):
                typeName = "QLineEdit"
            else:
                typeName = "QTextEdit"
            field.setStyleSheet( typeName + "{ background: #ffa07a; }" )
        return

    def __saveAndAccept( self ):
        " Saves the changes and accepts the values "
        self.__validate()
        if self.__tidyButton.isEnabled() == False:
            return

        self.__settings.settings[ "COL_LIMIT" ] = int( self.__colsEdit.text() )
        self.__settings.settings[ "ASSIGNMENT" ] = str( self.__assignmentEdit.text() )
        self.__settings.settings[ "FUNCTION_PARAM_ASSIGNMENT" ] = str( self.__funcAssignEdit.text() )
        self.__settings.settings[ "DICT_COLON" ] = str( self.__dictSepEdit.text() )
        self.__settings.settings[ "SLICE_COLON" ] = str( self.__sliceSepEdit.text() )
        self.__settings.settings[ "SHEBANG" ] = str( self.__inEdit.text() )
        self.__settings.settings[ "CODING" ] = str( self.__outCodingEdit.text() )
        self.__settings.settings[ "CODING_SPEC" ] = str( self.__srcCodingEdit.text() )
        self.__settings.settings[ "BOILERPLATE" ] = str( self.__boilEdit.toPlainText() )
        self.__settings.settings[ "KEEP_BLANK_LINES" ] = bool( self.__keepBlanks.isChecked() )
        self.__settings.settings[ "ADD_BLANK_LINES_AROUND_COMMENTS" ] = bool( self.__addBlanks.isChecked() )
        self.__settings.settings[ "LEFTJUST_DOC_STRINGS" ] = bool( self.__justifyDoc.isChecked() )
        self.__settings.settings[ "WRAP_DOC_STRINGS" ] = bool( self.__wrapDoc.isChecked() )
        self.__settings.settings[ "RECODE_STRINGS" ] = bool( self.__recodeStrings.isChecked() )
        self.__settings.settings[ "CAN_SPLIT_STRINGS" ] = bool( self.__splitStrings.isChecked() )
        self.__settings.settings[ "KEEP_UNASSIGNED_CONSTANTS" ] = bool( self.__keepUnassignedConst.isChecked() )
        self.__settings.settings[ "PARENTHESIZE_TUPLE_DISPLAY" ] = bool( self.__parenTuple.isChecked() )
        self.__settings.settings[ "JAVA_STYLE_LIST_DEDENT" ] = bool( self.__javaListDedent.isChecked() )

        if self.__use1RButton.isChecked():
            self.__settings.settings[ "SINGLE_QUOTED_STRINGS" ] = True
            self.__settings.settings[ "DOUBLE_QUOTED_STRINGS" ] = False
        elif self.__use2RButton.isChecked():
            self.__settings.settings[ "SINGLE_QUOTED_STRINGS" ] = False
            self.__settings.settings[ "DOUBLE_QUOTED_STRINGS" ] = True
        else:
            self.__settings.settings[ "SINGLE_QUOTED_STRINGS" ] = False
            self.__settings.settings[ "DOUBLE_QUOTED_STRINGS" ] = False

        try:
            self.__settings.saveToFile( self.__path )
        except:
            logging.error( "Error saving PythonTidy settings into " + \
                           self.__path + ". Ignor and continue." )
        self.accept()
        return

    def __validate( self, text = None ):
        " Validates input "
        allValid = True
        val = str( self.__colsEdit.text() )
        try:
            intVal = int( val )
            if intVal <= 0:
                allValid = False
                self.__setValid( self.__colsEdit, False )
            else:
                self.__setValid( self.__colsEdit, True )
        except:
            allValid = False
            self.__setValid( self.__colsEdit, False )

        if '=' not in self.__assignmentEdit.text():
            allValid = False
            self.__setValid( self.__assignmentEdit, False )
        else:
            self.__setValid( self.__assignmentEdit, True )

        if '=' not in self.__funcAssignEdit.text():
            allValid = False
            self.__setValid( self.__funcAssignEdit, False )
        else:
            self.__setValid( self.__funcAssignEdit, True )

        if ':' not in self.__dictSepEdit.text():
            allValid = False
            self.__setValid( self.__dictSepEdit, False )
        else:
            self.__setValid( self.__dictSepEdit, True )

        if ':' not in self.__sliceSepEdit.text():
            allValid = False
            self.__setValid( self.__sliceSepEdit, False )
        else:
            self.__setValid( self.__sliceSepEdit, True )

        val = str( self.__inEdit.text() )
        if val.strip() != "" and not val.strip().startswith( '#!' ):
            allValid = False
            self.__setValid( self.__inEdit, False )
        else:
            self.__setValid( self.__inEdit, True )

        val = str( self.__srcCodingEdit.text() )
        if val.strip() != "" and not val.strip().startswith( '#' ):
            allValid = False
            self.__setValid( self.__srcCodingEdit, False )
        else:
            self.__setValid( self.__srcCodingEdit, True )


        self.__tidyButton.setEnabled( allValid )
        return


