#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010  Sergey Satskiy sergey.satskiy@gmail.com
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

""" About dialog implementation """

from PyQt4.QtGui import ( QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget,
                          QTextBrowser, QDialogButtonBox, QSizePolicy )
from PyQt4.QtCore import Qt
from utils.pixmapcache import PixmapCache
from utils.globals import GlobalData
from utils.versions import getComponentInfo


class AboutDialog( QDialog ):
    " Codimension about dialog "

    def __init__( self, parent = None ):
        QDialog.__init__( self, parent )
        self.__createLayout()
        self.setWindowTitle( "About Codimension" )
        return

    def __createLayout( self ):
        " Creates the dialog layout "
        self.resize( 640, 480 )
        self.setSizeGripEnabled( True )

        vboxLayout = QVBoxLayout( self )
        hboxLayout = QHBoxLayout()
        iconLabel = QLabel()
        iconLabel.setPixmap( PixmapCache().getPixmap( "logo-48x48.png" ) )
        iconLabel.setScaledContents( False )
        hboxLayout.addWidget( iconLabel )
        versionLabel = QLabel( "<b>Codimension IDE version " +
                               str( GlobalData().version ) +
                               "</b><p>Copyright (c) Sergey Satskiy 2010-2015</p>" )
        versionLabel.setSizePolicy( QSizePolicy.Expanding,
                                    QSizePolicy.Expanding )
        versionLabel.setFixedHeight( versionLabel.minimumSizeHint().height() )
        versionLabel.setAlignment( Qt.AlignCenter )
        hboxLayout.addWidget( versionLabel )
        vboxLayout.addLayout( hboxLayout )

        tabWidget = QTabWidget( self )
        tabWidget.setFocusPolicy( Qt.NoFocus )

        description = self.__createDescription()
        tabWidget.addTab( description, "About" )
        versioning = self.__createVersioning()
        tabWidget.addTab( versioning, "Versions and licenses" )
        authors = self.__createAuthors()
        tabWidget.addTab( authors, "Contributors" )
        vboxLayout.addWidget( tabWidget )

        # Button at the bottom
        buttonBox = QDialogButtonBox( self )
        buttonBox.setOrientation( Qt.Horizontal )
        buttonBox.setStandardButtons( QDialogButtonBox.Ok )
        buttonBox.accepted.connect( self.close )
        buttonBox.rejected.connect( self.close )
        vboxLayout.addWidget( buttonBox )
        return

    def __createDescription( self ):
        " Creates the description browser "
        browser = QTextBrowser()
        browser.setHtml( """
<p align="justify">
Codimension is a free experimental Python IDE.
</p>
<p align="justify">
Codimension aims to provide an integrated system for:
<ul>
<li>traditional text-based code editing, and</li>
<li>diagram-based code analysis (e.g. imports and classes diagrams,
    profiling results etc).</li>
</ul>
</p>

<p align="justify">
Many Python developers will find codimension useful as-is, even though not all
of its features have been implemented yet.
</p>
<p align="justify">
More information could be found on <a href='http://satsky.spb.ru/codimension/'>
Codimension home page</a>.<br> Happy coding with Codimension!
</p>
""" )
        browser.setOpenExternalLinks( True )
        return browser

    def __createVersioning( self ):
        " Creates the versioning section "
        components = getComponentInfo()
        text = "<p>The major Codimension components are listed below:</p>" \
               "<ul>"
        for (prettyName, version, homeURL,
             patched, license, licenseLink) in components:
            text += "<li><a href='" + homeURL + "'>" + prettyName + "</a><br>" \
                    "Version: "
            if version is not None and version[ 0 ].isdigit():
                text += version
            elif version is not None and version.lower() == "not installed":
                text += version.lower()
            elif version is None:
                text += "n/a"
            else:
                text += str( version )
            if patched:
                text += " (patched for codimension)"
            text += "<br>"
            text += "License: "
            if licenseLink.startswith( "http" ):
                text += "<a href='" + licenseLink + "'>" + license + "</a>"
            else:
                text += license + " (" + licenseLink + ")"
            text += "<br></li>"
        text += "</ul>"
        browser = QTextBrowser()
        browser.setHtml( text )
        browser.setOpenExternalLinks( True )
        return browser

    def __createAuthors( self ):
        " Creates the authors section "
        addr1 = "<a href='mailto:sergey.satskiy@gmail.com'>sergey.satskiy@gmail.com</a>"
        addr2 = "<a href='mailto:isloginov@gmail.com'>isloginov@gmail.com</a>"
        addr3 = "<a href='mailto:him@revl.org'>him@revl.org</a>"
        addr4 = "<a href='mailto:david@dm9606.com'>david@dm9606.com</a>"
        text = "<p>Author: Sergey Satskiy &lt;" + addr1 + "&gt;</p>" \
               "<p>Packaging: Ilya Loginov &lt;" + addr2 + "&gt;</p>" \
               "<p>Discussions, ideas, testing: David McElhany &lt;" + addr4 + "&gt;</p>" \
               "<p>Initial packaging and logo: Dmitry Kazimirov &lt;" + addr3 + "&gt;</p>" \
               "<p align='justify'>Special thanks: Detlev Offenbach - the author of the Eric Python IDE." \
               " Codimension borrows some code and some ideas from Eric 4.</p>"
        browser = QTextBrowser()
        browser.setHtml( text )
        browser.setOpenExternalLinks( True )
        return browser
