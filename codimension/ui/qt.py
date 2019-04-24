# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010-2016  Sergey Satskiy sergey.satskiy@gmail.com
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

"""All the imports from the QT libraries"""


from PyQt5.QtCore import (Qt, QFileInfo, QSize, QUrl, QTimer, pyqtSignal,
                          QEventLoop, QRect, QEvent, QPoint, QRectF,
                          QModelIndex, QAbstractItemModel, QItemSelectionModel,
                          QStringListModel, QDir, QRegExp, QPointF, QSizeF,
                          QSortFilterProxyModel, QObject, QFileSystemWatcher,
                          QThread, QMutex, QWaitCondition, QT_VERSION_STR,
                          QMimeData, QByteArray)
from PyQt5.QtGui import (QCursor, QFontMetrics, QDesktopServices, QFont, QIcon,
                         QPalette, QColor, QBrush, QKeySequence, QIntValidator,
                         QPainter, QTextCursor, QImage, QPixmap, QPen,
                         QDoubleValidator, QImageReader, QPainterPath,
                         QTransform, QTextOption, QTextDocument)
from PyQt5.QtWidgets import (QApplication, QToolBar, QMenuBar, QLabel,
                             QTabWidget, QActionGroup, QHBoxLayout, QWidget,
                             QAction, QMenu, QSizePolicy, QToolButton, QDialog,
                             QToolTip, QVBoxLayout, QSplitter, QTextBrowser,
                             QDialogButtonBox, QFrame, QGridLayout, QComboBox,
                             QAbstractItemView, QCompleter, QListView,
                             QDirModel, QMessageBox, QShortcut, QFileDialog,
                             QTabBar, QTreeView, QHeaderView, QProgressBar,
                             QCheckBox, QRadioButton, QGroupBox, QPushButton,
                             QTreeWidget, QTreeWidgetItem, QLineEdit, QStyle,
                             QListWidget, QStyleOptionFrame, QItemDelegate,
                             QStyleFactory, QStyledItemDelegate, QBoxLayout,
                             QStyleOptionViewItem, QPlainTextEdit, QTextEdit,
                             QMainWindow, QSpacerItem, QStackedWidget,
                             QSplashScreen, QFontComboBox, QScrollArea,
                             QGraphicsScene, QGraphicsSimpleTextItem,
                             QGraphicsRectItem, QGraphicsPathItem, QSpinBox,
                             QGraphicsItem, QStyleOptionGraphicsItem,
                             QGraphicsView, QGraphicsTextItem, QDockWidget,
                             QGraphicsPixmapItem, QColorDialog)
from PyQt5.QtNetwork import QTcpServer, QHostAddress, QAbstractSocket
from PyQt5.QtSvg import QSvgGenerator, QGraphicsSvgItem
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
from PyQt5.QtPrintSupport import QPrintDialog
