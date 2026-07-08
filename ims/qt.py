"""Single import point for Qt so the app runs on PySide6 or PyQt6."""

try:
    from PySide6.QtCore import (Qt, QDate, QRegularExpression, QSortFilterProxyModel, Signal)
    from PySide6.QtGui import (QAction, QFont, QColor, QIcon, QStandardItem,
                               QStandardItemModel, QTextDocument, QPixmap,
                               QPainter, QPen)
    from PySide6.QtWidgets import (
        QApplication, QCheckBox, QComboBox, QDateEdit, QDialog, QDoubleSpinBox,
        QFileDialog, QFormLayout, QFrame, QGridLayout, QGroupBox, QHBoxLayout,
        QHeaderView, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton,
        QRadioButton, QSpinBox, QTabWidget, QTableWidget, QTableWidgetItem,
        QTextEdit, QVBoxLayout, QWidget, QAbstractItemView, QSizePolicy)
    from PySide6.QtPrintSupport import QPrinter, QPrintPreviewDialog
    QT_LIB = "PySide6"
except ImportError:                                       # pragma: no cover
    from PyQt6.QtCore import (Qt, QDate, QRegularExpression, QSortFilterProxyModel)
    from PyQt6.QtCore import pyqtSignal as Signal
    from PyQt6.QtGui import (QAction, QFont, QColor, QIcon, QStandardItem,
                             QStandardItemModel, QTextDocument, QPixmap,
                             QPainter, QPen)
    from PyQt6.QtWidgets import (
        QApplication, QCheckBox, QComboBox, QDateEdit, QDialog, QDoubleSpinBox,
        QFileDialog, QFormLayout, QFrame, QGridLayout, QGroupBox, QHBoxLayout,
        QHeaderView, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton,
        QRadioButton, QSpinBox, QTabWidget, QTableWidget, QTableWidgetItem,
        QTextEdit, QVBoxLayout, QWidget, QAbstractItemView, QSizePolicy)
    from PyQt6.QtPrintSupport import QPrinter, QPrintPreviewDialog
    QT_LIB = "PyQt6"
