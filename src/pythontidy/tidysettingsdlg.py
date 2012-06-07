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

from PyQt4.QtCore                import Qt, SIGNAL
from PyQt4.QtGui                 import QDialog, QDialogButtonBox, \
                                        QVBoxLayout, QLabel, \
                                        QLineEdit, QHBoxLayout, \
                                        QGridLayout, QTextEdit, QCheckBox, \
                                        QGroupBox, QSizePolicy, QRadioButton


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

        self.resize( 600, 300 )
        self.setSizeGripEnabled( True )

        layout = QVBoxLayout( self )
        gridLayout = QGridLayout()

        # Columns
        colsLabel = QLabel( "Columns" )
        self.__colsEdit = QLineEdit()
        self.__colsEdit.setText( str( self.__settings.settings[ "COL_LIMIT" ] ) )
        self.__colsEdit.setToolTip( self.__settings.getDescription( "COL_LIMIT" ) )
        self.connect( self.__colsEdit,
                      SIGNAL( "textChanged(const QString &)" ),
                      self.__validate )
        gridLayout.addWidget( colsLabel, 0, 0, 1, 1 )
        gridLayout.addWidget( self.__colsEdit, 0, 1, 1, 1 )
        font = self.__colsEdit.font()
        font.setFamily( "Monospace" )
        self.__colsEdit.setFont( font )

        # Assignment
        assignmentLabel = QLabel( "Assignment" )
        self.__assignmentEdit = QLineEdit()
        self.__assignmentEdit.setText( self.__settings.settings[ "ASSIGNMENT" ] )
        self.__assignmentEdit.setToolTip( self.__settings.getDescription( "ASSIGNMENT" ) )
        self.connect( self.__assignmentEdit,
                      SIGNAL( "textChanged(const QString &)" ),
                      self.__validate )
        gridLayout.addWidget( assignmentLabel, 1, 0, 1, 1 )
        gridLayout.addWidget( self.__assignmentEdit, 1, 1, 1, 1 )
        self.__assignmentEdit.setFont( font )

        # Function parameters assignment
        funcAssignLabel = QLabel( "Function params assignment" )
        self.__funcAssignEdit = QLineEdit()
        self.__funcAssignEdit.setText( self.__settings.settings[ "FUNCTION_PARAM_ASSIGNMENT" ] )
        self.__funcAssignEdit.setToolTip( self.__settings.getDescription( "FUNCTION_PARAM_ASSIGNMENT" ) )
        self.connect( self.__funcAssignEdit,
                      SIGNAL( "textChanged(const QString &)" ),
                      self.__validate )
        gridLayout.addWidget( funcAssignLabel, 2, 0, 1, 1 )
        gridLayout.addWidget( self.__funcAssignEdit, 2, 1, 1, 1 )
        self.__funcAssignEdit.setFont( font )

        # Dictionary separator
        dictSepLabel = QLabel( "Dictionary separator" )
        self.__dictSepEdit = QLineEdit()
        self.__dictSepEdit.setText( self.__settings.settings[ "DICT_COLON" ] )
        self.__dictSepEdit.setToolTip( self.__settings.getDescription( "DICT_COLON" ) )
        self.connect( self.__dictSepEdit,
                      SIGNAL( "textChanged(const QString &)" ),
                      self.__validate )
        gridLayout.addWidget( dictSepLabel, 3, 0, 1, 1 )
        gridLayout.addWidget( self.__dictSepEdit, 3, 1, 1, 1 )
        self.__dictSepEdit.setFont( font )

        # Slice separator
        sliceSepLabel = QLabel( "Slice separator" )
        self.__sliceSepEdit = QLineEdit()
        self.__sliceSepEdit.setText( self.__settings.settings[ "SLICE_COLON" ] )
        self.__sliceSepEdit.setToolTip( self.__settings.getDescription( "SLICE_COLON" ) )
        self.connect( self.__sliceSepEdit,
                      SIGNAL( "textChanged(const QString &)" ),
                      self.__validate )
        gridLayout.addWidget( sliceSepLabel, 4, 0, 1, 1 )
        gridLayout.addWidget( self.__sliceSepEdit, 4, 1, 1, 1 )
        self.__sliceSepEdit.setFont( font )

        # Interpreter
        inLabel = QLabel( "Interpreter" )
        self.__inEdit = QLineEdit()
        self.__inEdit.setText( self.__settings.settings[ "SHEBANG" ] )
        self.__inEdit.setToolTip( self.__settings.getDescription( "SHEBANG" ) )
        self.connect( self.__inEdit,
                      SIGNAL( "textChanged(const QString &)" ),
                      self.__validate )
        gridLayout.addWidget( inLabel, 5, 0, 1, 1 )
        gridLayout.addWidget( self.__inEdit, 5, 1, 1, 1 )
        self.__inEdit.setFont( font )

        # Coding spec
        codingLabel = QLabel( "Output encoding" )
        self.__outCodingEdit = QLineEdit()
        self.__outCodingEdit.setText( self.__settings.settings[ "CODING" ] )
        self.__outCodingEdit.setToolTip( self.__settings.getDescription( "CODING" ) )
        self.connect( self.__outCodingEdit,
                      SIGNAL( "textChanged(const QString &)" ),
                      self.__validate )
        gridLayout.addWidget( codingLabel, 6, 0, 1, 1 )
        gridLayout.addWidget( self.__outCodingEdit, 6, 1, 1, 1 )
        self.__outCodingEdit.setFont( font )

        # Src coding comment
        srcCodingLabel = QLabel( "File encoding comment" )
        self.__srcCodingEdit = QLineEdit()
        self.__srcCodingEdit.setText( self.__settings.settings[ "CODING_SPEC" ] )
        self.__srcCodingEdit.setToolTip( self.__settings.getDescription( "CODING_SPEC" ) )
        self.connect( self.__srcCodingEdit,
                      SIGNAL( "textChanged(const QString &)" ),
                      self.__validate )
        gridLayout.addWidget( srcCodingLabel, 7, 0, 1, 1 )
        gridLayout.addWidget( self.__srcCodingEdit, 7, 1, 1, 1 )
        self.__srcCodingEdit.setFont( font )

        # Boilerplate
        boilLabel = QLabel( "Boilerplate" )
        self.__boilEdit = QTextEdit()
        self.__boilEdit.setPlainText( self.__settings.settings[ "BOILERPLATE" ] )
        self.__boilEdit.setToolTip( self.__settings.getDescription( "BOILERPLATE" ) )
        self.__boilEdit.setTabChangesFocus( True )
        self.__boilEdit.setAcceptRichText( False )
        self.connect( self.__boilEdit,
                      SIGNAL( "textChanged()" ),
                      self.__validate )
        gridLayout.addWidget( boilLabel, 8, 0, 1, 1 )
        gridLayout.addWidget( self.__boilEdit, 8, 1, 1, 1 )
        self.__boilEdit.setFont( font )

        layout.addLayout( gridLayout )


        # Now check boxes and radio buttons
        self.__keepBlanks = QCheckBox( "Keep blank lines" )
        self.__keepBlanks.setChecked( self.__settings.settings[ "KEEP_BLANK_LINES" ] )
        self.__keepBlanks.setToolTip( self.__settings.getDescription( "KEEP_BLANK_LINES" ) )
        layout.addWidget( self.__keepBlanks )

        self.__addBlanks = QCheckBox( "Add blank lines around comments" )
        self.__addBlanks.setChecked( self.__settings.settings[ "ADD_BLANK_LINES_AROUND_COMMENTS" ] )
        self.__addBlanks.setToolTip( self.__settings.getDescription( "ADD_BLANK_LINES_AROUND_COMMENTS" ) )
        layout.addWidget( self.__addBlanks )

        self.__justifyDoc = QCheckBox( "Left justify doc strings" )
        self.__justifyDoc.setChecked( self.__settings.settings[ "LEFTJUST_DOC_STRINGS" ] )
        self.__justifyDoc.setToolTip( self.__settings.getDescription( "LEFTJUST_DOC_STRINGS" ) )
        layout.addWidget( self.__justifyDoc )

        self.__wrapDoc = QCheckBox( "Wrap long doc strings" )
        self.__wrapDoc.setChecked( self.__settings.settings[ "WRAP_DOC_STRINGS" ] )
        self.__wrapDoc.setToolTip( self.__settings.getDescription( "WRAP_DOC_STRINGS" ) )
        layout.addWidget( self.__wrapDoc )

        self.__recodeStrings = QCheckBox( "Try to decode strings" )
        self.__recodeStrings.setChecked( self.__settings.settings[ "RECODE_STRINGS" ] )
        self.__recodeStrings.setToolTip( self.__settings.getDescription( "RECODE_STRINGS" ) )
        layout.addWidget( self.__recodeStrings )

        self.__splitStrings = QCheckBox( "Split long strings" )
        self.__splitStrings.setChecked( self.__settings.settings[ "CAN_SPLIT_STRINGS" ] )
        self.__splitStrings.setToolTip( self.__settings.getDescription( "CAN_SPLIT_STRINGS" ) )
        layout.addWidget( self.__splitStrings )

        self.__keepUnassignedConst = QCheckBox( "Keep unassigned constants" )
        self.__keepUnassignedConst.setChecked( self.__settings.settings[ "KEEP_UNASSIGNED_CONSTANTS" ] )
        self.__keepUnassignedConst.setToolTip( self.__settings.getDescription( "KEEP_UNASSIGNED_CONSTANTS" ) )
        layout.addWidget( self.__keepUnassignedConst )

        self.__parenTuple = QCheckBox( "Parenthesize tuple display" )
        self.__parenTuple.setChecked( self.__settings.settings[ "PARENTHESIZE_TUPLE_DISPLAY" ] )
        self.__parenTuple.setToolTip( self.__settings.getDescription( "PARENTHESIZE_TUPLE_DISPLAY" ) )
        layout.addWidget( self.__parenTuple )

        self.__javaListDedent = QCheckBox( "Java style list dedent" )
        self.__javaListDedent.setChecked( self.__settings.settings[ "JAVA_STYLE_LIST_DEDENT" ] )
        self.__javaListDedent.setToolTip( self.__settings.getDescription( "JAVA_STYLE_LIST_DEDENT" ) )
        layout.addWidget( self.__javaListDedent )


        # Quotas radio buttons
        quotasGroupbox = QGroupBox( "Quotas" )
        sizePolicy = QSizePolicy( QSizePolicy.Expanding, QSizePolicy.Preferred )
        sizePolicy.setHorizontalStretch( 0 )
        sizePolicy.setVerticalStretch( 0 )
        sizePolicy.setHeightForWidth( \
                        quotasGroupbox.sizePolicy().hasHeightForWidth() )
        quotasGroupbox.setSizePolicy( sizePolicy )

        layoutQG = QVBoxLayout( quotasGroupbox )
        self.__use1RButton = QRadioButton( "Use apostrophes instead of quotes for string literals",
                                           quotasGroupbox )
        layoutQG.addWidget( self.__use1RButton )
        self.__use2RButton = QRadioButton( "Use quotes instead of apostrophes for string literals",
                                           quotasGroupbox )
        layoutQG.addWidget( self.__use2RButton )
        self.__useAsIsRButton = QRadioButton( "Do not make changes",
                                              quotasGroupbox )
        layoutQG.addWidget( self.__useAsIsRButton )
        use1 = self.__settings.settings[ "SINGLE_QUOTED_STRINGS" ]
        use2 = self.__settings.settings[ "DOUBLE_QUOTED_STRINGS" ]
        if use1:
            self.__use1RButton.setChecked( True )
        elif use2:
            self.__use2RButton.setChecked( True )
        else:
            self.__useAsIsRButton.setChecked( True )
        layout.addWidget( quotasGroupbox )


        # Buttons at the bottom
        buttonBox = QDialogButtonBox( self )
        buttonBox.setOrientation( Qt.Horizontal )
        buttonBox.setStandardButtons( QDialogButtonBox.Cancel )
        self.__resetButton = buttonBox.addButton( "Reset to Default",
                                                  QDialogButtonBox.ActionRole )
        self.connect( self.__resetButton, SIGNAL( 'clicked()' ), self.__reset )
        self.__tidyButton = buttonBox.addButton( "Tidy",
                                                 QDialogButtonBox.ActionRole )
        self.__tidyButton.setDefault( True )
        self.connect( self.__tidyButton, SIGNAL( 'clicked()' ),
                      self.__saveAndAccept )
        layout.addWidget( buttonBox )

        self.connect( buttonBox, SIGNAL( "rejected()" ), self.close )
        return

    def __reset( self ):
        " Resets the values to default "
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
            field.setStyleSheet( typeName + "{ background: ffa07a; }" )
        return

    def __saveAndAccept( self ):
        " Saves the changes and accepts the values "
        self.accept()
        return

    def __validate( self, text = None ):
        " Validates input "
        return


