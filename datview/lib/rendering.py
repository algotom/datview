"""
Rendering module for DatView.
Contains all UI window classes and custom widgets.
"""

import os
import platform
import re
from pathlib import Path
import numpy as np
import h5py
import pyqtgraph as pg
from PySide6.QtCore import (Qt, QTimer, Signal, QAbstractTableModel,
                            QModelIndex, QSortFilterProxyModel, QRect, QFile,
                            QIODevice, QTextStream, QSize)

from PySide6.QtGui import (QFont, QColor, QTextCursor, QTextOption, QIcon,
                           QTextDocument, QPainter, QFontMetrics,
                           QSyntaxHighlighter, QTextCharFormat, QFontDatabase,
                           QCursor)

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QGridLayout, QLabel, QPushButton,
                               QTreeWidget, QTreeWidgetItem, QListWidget,
                               QComboBox, QSlider, QTextEdit, QMessageBox,
                               QFileDialog, QFrame, QGroupBox, QSplitter,
                               QTableWidget, QTableWidgetItem, QHeaderView,
                               QAbstractItemView, QPlainTextEdit, QSizePolicy,
                               QRadioButton, QStatusBar, QTableView, QLineEdit,
                               QCheckBox, QMenu)

import datview.lib.utilities as util

# Configure pyqtgraph
pg.setConfigOptions(antialias=True, imageAxisOrder='row-major', background='w',
                    foreground='k')

THEME_QSS = f"""
    QWidget {{
        font-size: {util.FONT_SIZE}px;
    }}
    QGroupBox {{
        border: 1px solid rgba(128, 128, 128, 60);
        border-radius: 6px;
        margin-top: 10px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 6px;
    }}
    QFrame {{
        border-radius: 6px;
    }}
    QPushButton {{
        background-color: #ffffff;
        border: 1px solid #d0d0d0;
        border-radius: 6px;
        padding: 6px 14px;
    }}
    QPushButton:hover {{
        background-color: #f5f8ff;
        border: 1px solid #3d84ff;
    }}
    QPushButton:pressed {{
        background-color: #eaf1ff;
    }}
    QPushButton:disabled {{
        background-color: #f5f5f5;
        border: 1px solid #dddddd;
        color: #9a9a9a;
    }}
    QPushButton:disabled {{
        opacity: 0.5;
    }}
    QComboBox, QListWidget, QTreeWidget, QTextEdit, QPlainTextEdit, QLineEdit {{
        border: 1px solid rgba(128, 128, 128, 60);
        border-radius: 6px;
        padding: 6px;
    }}
    QStatusBar {{
        border-top: 1px solid rgba(128,128,128,60);
        padding: 10px 10px;
    }}
    QStatusBar::item {{
        border: none;
    }}
    QLabel#StatusPill {{
        border: none;
        padding: 0px 5px 8px 5px;
        margin-left: 5px;
    }}
    QSplitter::handle {{
        background: rgba(128, 128, 128, 40);
    }}
"""


def select_ui_font(point_size: int = 13, weight: int = QFont.Normal) -> QFont:
    """
    Choose a UI font based on OS, using a priority list.
    """
    sysname = platform.system()
    families = set(QFontDatabase.families())

    if sysname == "Linux":
        priority = [
            "Liberation Sans",
            "Cantarell",
            "Ubuntu",
            "Noto Sans",
            "DejaVu Sans",
        ]
    elif sysname == "Windows":
        priority = [
            "Segoe UI",
            "Calibri",
            "Arial",
            "Tahoma",
        ]
    elif sysname == "Darwin":
        priority = [
            ".SF NS Text",
            "Helvetica Neue",
            "Helvetica",
            "Arial",
        ]
    else:
        priority = [
            "Noto Sans",
            "DejaVu Sans",
            "Arial",
        ]

    chosen = None
    for name in priority:
        if name in families:
            chosen = name
            break

    font = QFont(chosen) if chosen else QFont()
    font.setPointSize(point_size)
    return font


def calculate_geometry(ratio=0.8):
    """Calculate window size and position centered on screen"""
    screen = QApplication.primaryScreen().availableGeometry()
    width = int(screen.width() * ratio)
    height = int(screen.height() * ratio)
    max_ratio = 1.65
    if width > height:
        current_ratio = width / height
        if current_ratio > max_ratio:
            width = int(max_ratio * height)
    else:
        current_ratio = height / width
        if current_ratio > max_ratio:
            height = int(max_ratio * width)
    x = screen.center().x() - width // 2
    y = screen.center().y() - height // 2
    return QRect(x, y, width, height)


def apply_app_theme(app: QApplication):
    app.setStyle("Fusion")
    pal = app.style().standardPalette()
    app.setPalette(pal)
    app.setStyleSheet(THEME_QSS)


class BaseWindow(QWidget):
    """Base helper for windows to set common properties"""
    closed = Signal(object)

    def __init__(self, parent=None, title="Window", ratio=0.8):
        qt_parent = parent if isinstance(parent, QWidget) else None
        super().__init__(qt_parent)
        self.setWindowFlags(Qt.Window)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle(title)
        self.setGeometry(calculate_geometry(ratio))

    def closeEvent(self, event):
        self.closed.emit(self)
        super().closeEvent(event)


class HDFViewerWindow(BaseWindow):
    """Display HDF file hierarchy and dataset info"""
    sig_item_double_clicked = Signal(str, str)

    def __init__(self, parent=None, file_path="", ratio=util.TEXT_WIN_RATIO):
        super().__init__(parent, f"HDF Viewer: {file_path}", ratio)
        self.file_path = file_path
        # --- Outer layout
        main = QVBoxLayout(self)
        m_val = 4
        main.setContentsMargins(m_val, m_val, m_val, m_val)
        main.setSpacing(2)
        # --- Splitter
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(0)
        # ===== Left Pane: Tree (inside a padded frame) =====
        left_frame = QFrame()
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(m_val, m_val, m_val, m_val)
        left_layout.setSpacing(0)

        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabel("HDF File Hierarchy")
        self.tree_widget.setIndentation(10)
        self.tree_widget.setUniformRowHeights(True)
        self.tree_widget.itemSelectionChanged.connect(self.on_selection_changed)
        self.tree_widget.itemDoubleClicked.connect(self.on_item_double_clicked)

        left_layout.addWidget(self.tree_widget)
        self.splitter.addWidget(left_frame)

        # ===== Right Pane: Info (inside a padded frame) =====
        right_frame = QFrame()
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(m_val, m_val, m_val, m_val)
        right_layout.setSpacing(0)

        title = QLabel("Brief Information")
        f = QFont(QApplication.font())
        title.setFont(f)

        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)

        right_layout.addWidget(title, 0)
        right_layout.addWidget(self.info_text, 1)

        self.splitter.addWidget(right_frame)

        # Split ratio
        self.splitter.setStretchFactor(0, 9)
        self.splitter.setStretchFactor(1, 8)

        main.addWidget(self.splitter, 1)
        try:
            self.hdf_file = h5py.File(file_path, "r")
            self.populate_tree()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open HDF file: {e}")

    def populate_tree(self):
        def add_node(parent_item, name, obj):
            item = QTreeWidgetItem(parent_item)
            item.setText(0, name.split("/")[-1] if "/" in name else name)
            item.setData(0, Qt.UserRole, name)
            if isinstance(obj, h5py.Group):
                for subname, subobj in obj.items():
                    add_node(item, f"{name}/{subname}".strip("/"), subobj)

        for item_name, item in self.hdf_file.items():
            add_node(self.tree_widget, item_name, item)
        self.tree_widget.expandAll()

    def on_selection_changed(self):
        selected = self.tree_widget.selectedItems()
        if not selected:
            return
        hdf_path = selected[0].data(0, Qt.UserRole)

        data_type, value = util.get_hdf_data(self.file_path, hdf_path)

        info = f"HDF Path: {hdf_path}\n"
        info += f"Data Type: {data_type}\n"
        if data_type == "array":
            info += f"Shape: {value}"
        else:
            info += f"Value: {value}"

        self.info_text.setPlainText(info)

    def on_item_double_clicked(self, item: QTreeWidgetItem, _col: int):
        hdf_path = item.data(0, Qt.UserRole)
        if not hdf_path:
            return
        self.sig_item_double_clicked.emit(self.file_path, str(hdf_path))

    def closeEvent(self, event):
        if hasattr(self, 'hdf_file'):
            self.hdf_file.close()
        super().closeEvent(event)


class PlotWindow1D(BaseWindow):
    """Window for 1D plots using pyqtgraph"""
    def __init__(self, parent=None, title="", data_x=None, data_y=None,
                 plot_type="plot", help_text="", ratio=util.PLT_WIN_1D_RATIO):
        super().__init__(parent, title, ratio)
        layout = QVBoxLayout(self)

        self.plot_widget = pg.PlotWidget(title=help_text)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.2)
        layout.addWidget(self.plot_widget)
        gui_font = QApplication.font()

        plot_font = QFont(gui_font)
        plot_font.setPointSize(max(8, gui_font.pointSize() - 3))

        for axis_name in ("bottom", "left"):
            axis = self.plot_widget.getAxis(axis_name)
            axis.setTickFont(plot_font)
            axis.label.setFont(plot_font)

        self.plot_widget.getPlotItem().titleLabel.setFont(plot_font)

        if plot_type == "plot":
            if data_x is not None:
                self.plot_widget.plot(data_x, data_y, pen='b')
            else:
                self.plot_widget.plot(data_y, pen='b')

        elif plot_type == "histogram":
            flat_data = data_y.ravel()
            try:
                p_min = np.percentile(flat_data, util.HIST_P_MIN)
                p_max = np.percentile(flat_data, util.HIST_P_MAX)
                if p_min == p_max:
                    p_min = flat_data.min() - 0.5
                    p_max = flat_data.max() + 0.5
                hist_range = (p_min, p_max)
            except IndexError:
                hist_range = None

            hist, bin_edges = np.histogram(flat_data, bins=util.HIST_NUM_BINS,
                                           range=hist_range)
            bargraph = pg.BarGraphItem(x=bin_edges[:-1], height=hist,
                                       width=np.diff(bin_edges), brush='b')
            self.plot_widget.addItem(bargraph)
            self.plot_widget.setLabel('bottom', "Grayscale")
            self.plot_widget.setLabel('left', "Frequency (Count)")

        elif plot_type == "percentile":
            self.plot_widget.plot(data_x, data_y, pen='b', symbol='o',
                                  symbolSize=5)
            self.plot_widget.setLabel('bottom', "Percentile")
            self.plot_widget.setXRange(0, 100)
            self.plot_widget.setLabel('left', "Normalized density")
            self.plot_widget.showGrid(x=True, y=True, alpha=0.6)


def _fmt(color, bold=False, italic=False):
    f = QTextCharFormat()
    f.setForeground(QColor(color))
    if bold:
        f.setFontWeight(QFont.Bold)
    if italic:
        f.setFontItalic(True)
    return f


class MiniHighlighter(QSyntaxHighlighter):
    """
    Modes: 'python', 'json', 'yaml', 'log'
    - Python supports triple-quote multiline strings
    - YAML highlights keys, strings, numbers, booleans, comments
    - Log highlights ERROR/WARNING/INFO tokens (and common variants)
    """

    PY_TRIPLE_SINGLE = 1
    PY_TRIPLE_DOUBLE = 2

    def __init__(self, document, mode: str):
        super().__init__(document)
        self.mode = mode.lower()
        self.f_comment = _fmt("#888888", italic=True)
        self.f_string = _fmt("#008000")
        self.f_number = _fmt("#AA00AA")
        self.f_kw = _fmt("#0033CC", bold=True)
        self.f_key = _fmt("#0033CC", bold=True)  # yaml/json keys
        self.f_bool = _fmt("#AA5500", bold=True)

        self.f_err = _fmt("#CC0000", bold=True)
        self.f_warn = _fmt("#CC7A00", bold=True)
        self.f_info = _fmt("#0066CC", bold=True)

        self._re_num = re.compile(r"\b\d+(\.\d+)?([eE][+-]?\d+)?\b")

        if self.mode == "python":
            kws = (
                "and as assert break class continue def del elif else except "
                "False finally for from global if import in is lambda None "
                "nonlocal not or pass raise  return True try while with yield"
            ).split()
            self._py_kw = [re.compile(rf"\b{k}\b") for k in kws]
            self._py_comment = re.compile(r"#.*")
            self._py_sq = re.compile(r"'([^'\\]|\\.)*'")
            self._py_dq = re.compile(r'"([^"\\]|\\.)*"')
        elif self.mode in ("json", "yaml"):
            # YAML: key before ":" ; JSON: "key":
            self._re_yaml_key = re.compile(r"^\s*([A-Za-z0-9_\-\.]+)\s*:", re.M)
            self._re_json_key = re.compile(r'"([^"\\]|\\.)*"\s*:')
            self._re_str = re.compile(r'"([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\'')
            self._re_bool = re.compile(
                r"\b(true|false|null|True|False|None|yes|no|on|off)\b")
            self._re_comment = re.compile(r"#.*")
        elif self.mode == "log":
            self._re_err = re.compile(r"\b(ERROR|ERR|FATAL|CRITICAL)\b")
            self._re_warn = re.compile(r"\b(WARNING|WARN)\b")
            self._re_info = re.compile(r"\b(INFO)\b")

    def highlightBlock(self, text: str):
        if self.mode == "python":
            self._highlight_python(text)
        elif self.mode == "json":
            self._highlight_json(text)
        elif self.mode == "yaml":
            self._highlight_yaml(text)
        elif self.mode == "log":
            self._highlight_log(text)

    # ---- Python----
    def _highlight_python(self, text: str):
        m = self._py_comment.search(text)
        comment_start = m.start() if m else None
        if m:
            self.setFormat(m.start(), len(text) - m.start(), self.f_comment)
        for pat in (self._py_sq, self._py_dq):
            for mm in pat.finditer(text):
                if comment_start is not None and mm.start() >= comment_start:
                    continue
                self.setFormat(mm.start(), mm.end() - mm.start(), self.f_string)
        limit = comment_start if comment_start is not None else len(text)
        for mm in self._re_num.finditer(text[:limit]):
            self.setFormat(mm.start(), mm.end() - mm.start(), self.f_number)
        for kw in self._py_kw:
            for mm in kw.finditer(text[:limit]):
                self.setFormat(mm.start(), mm.end() - mm.start(), self.f_kw)
        self.setCurrentBlockState(0)
        self._apply_triple_quotes(text, "'''", self.PY_TRIPLE_SINGLE)
        self._apply_triple_quotes(text, '"""', self.PY_TRIPLE_DOUBLE)

    def _apply_triple_quotes(self, text: str, token: str, state_id: int):
        in_state = (self.previousBlockState() == state_id)
        start = 0

        if in_state:
            end = text.find(token, 0)
            if end == -1:
                self.setFormat(0, len(text), self.f_string)
                self.setCurrentBlockState(state_id)
                return
            else:
                end += len(token)
                self.setFormat(0, end, self.f_string)
                start = end
        while True:
            i = text.find(token, start)
            if i == -1:
                break
            j = text.find(token, i + len(token))
            if j == -1:
                self.setFormat(i, len(text) - i, self.f_string)
                self.setCurrentBlockState(state_id)
                return
            else:
                j += len(token)
                self.setFormat(i, j - i, self.f_string)
                start = j

    # ---- JSON / YAML ----
    def _highlight_json(self, text: str):
        for mm in self._re_comment.finditer(text):
            self.setFormat(mm.start(), mm.end() - mm.start(), self.f_comment)
        # keys: "key":
        for mm in self._re_json_key.finditer(text):
            q1 = text.rfind('"', 0, mm.end())
            q0 = text.rfind('"', 0, q1)
            if q0 != -1 and q1 != -1 and q1 > q0:
                self.setFormat(q0, q1 - q0 + 1, self.f_key)
        # strings
        for mm in self._re_str.finditer(text):
            self.setFormat(mm.start(), mm.end() - mm.start(), self.f_string)
        # numbers
        for mm in self._re_num.finditer(text):
            self.setFormat(mm.start(), mm.end() - mm.start(), self.f_number)
        # booleans / null
        for mm in self._re_bool.finditer(text):
            self.setFormat(mm.start(), mm.end() - mm.start(), self.f_bool)

    def _highlight_yaml(self, text: str):
        # comments
        for mm in self._re_comment.finditer(text):
            self.setFormat(mm.start(), mm.end() - mm.start(), self.f_comment)
        # keys (simple): key:
        for mm in self._re_yaml_key.finditer(text):
            self.setFormat(mm.start(1), mm.end(1) - mm.start(1), self.f_key)
        # strings
        for mm in self._re_str.finditer(text):
            self.setFormat(mm.start(), mm.end() - mm.start(), self.f_string)
        # numbers
        for mm in self._re_num.finditer(text):
            self.setFormat(mm.start(), mm.end() - mm.start(), self.f_number)
        # booleans
        for mm in self._re_bool.finditer(text):
            self.setFormat(mm.start(), mm.end() - mm.start(), self.f_bool)

    # ---- Logs ----
    def _highlight_log(self, text: str):
        for mm in self._re_err.finditer(text):
            self.setFormat(mm.start(), mm.end() - mm.start(), self.f_err)
        for mm in self._re_warn.finditer(text):
            self.setFormat(mm.start(), mm.end() - mm.start(), self.f_warn)
        for mm in self._re_info.finditer(text):
            self.setFormat(mm.start(), mm.end() - mm.start(), self.f_info)


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self._editor = editor
        self.setMouseTracking(True)

    def sizeHint(self):
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self._editor.line_number_area_paint_event(event)


class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        # monospace font
        f = QFont("DejaVu Sans Mono")
        f.setPointSize(max(9, QApplication.font().pointSize()))
        self.setFont(f)
        # line number area
        self._ln_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self._on_cursor_moved)
        self.update_line_number_area_width(0)
        # nice defaults
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setWordWrapMode(QTextOption.NoWrap)
        self.setTabStopDistance(
            4 * QFontMetrics(self.font()).averageCharWidth())

    def line_number_area_width(self):
        digits = max(3, len(str(max(1, self.blockCount()))))
        space = 8 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self._ln_area.scroll(0, dy)
        else:
            self._ln_area.update(0, rect.y(), self._ln_area.width(),
                                 rect.height())

        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        cr = self.contentsRect()
        self._ln_area.setGeometry(QRect(cr.left(), cr.top(),
                                        self.line_number_area_width(),
                                        cr.height()))

    def line_number_area_paint_event(self, event):
        painter = QPainter(self._ln_area)
        painter.fillRect(event.rect(),
                         self.palette().color(self.backgroundRole()))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(
            self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        fm = self.fontMetrics()
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(self.palette().color(self.foregroundRole()))
                painter.drawText(0, top, self._ln_area.width() - 4,
                                 fm.height(), Qt.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def _on_cursor_moved(self):
        if hasattr(self.parent(), "on_editor_cursor_moved"):
            self.parent().on_editor_cursor_moved()


class TextViewerWindow(BaseWindow):
    def __init__(self, parent=None, title="", file_path=None, content=None,
                 ratio=util.TEXT_WIN_RATIO):
        super().__init__(parent, title or "Text Viewer", ratio=ratio)
        self.file_path = file_path

        m_val = 4
        layout = QVBoxLayout(self)
        layout.setContentsMargins(m_val, m_val, m_val, m_val)
        layout.setSpacing(4)
        # toolbar: find + wrap toggle + open
        tb = QWidget()
        tb_l = QHBoxLayout(tb)
        tb_l.setContentsMargins(m_val, m_val, m_val, m_val)
        tb_l.setSpacing(4)

        self.find_edit = QLineEdit()
        self.find_edit.setPlaceholderText("Find...")
        self.btn_find_next = QPushButton("Find ▶")
        self.btn_find_prev = QPushButton("◀ Prev")
        self.wrap_cb = QCheckBox("Wrap")
        self.btn_open = QPushButton("Open...")

        tb_l.addWidget(self.find_edit, 1)
        tb_l.addWidget(self.btn_find_prev)
        tb_l.addWidget(self.btn_find_next)
        tb_l.addWidget(self.wrap_cb)
        tb_l.addWidget(self.btn_open, 0)
        layout.addWidget(tb, 0)

        # editor
        self.editor = CodeEditor(self)
        self.editor.setReadOnly(True)
        layout.addWidget(self.editor, 1)

        # status row
        status = QWidget()
        s_l = QHBoxLayout(status)
        s_l.setContentsMargins(0, 0, 0, 0)
        s_l.setSpacing(4)
        self.lbl_msg = QLabel(file_path or "")
        self.lbl_pos = QLabel("Ln 1, Col 1")
        self.lbl_size = QLabel("0 KB")
        s_l.addWidget(self.lbl_msg, 1)
        s_l.addWidget(self.lbl_pos, 0)
        s_l.addWidget(self.lbl_size, 0)
        layout.addWidget(status, 0)

        # connect
        self.btn_find_next.clicked.connect(lambda: self._find(step=1))
        self.btn_find_prev.clicked.connect(lambda: self._find(step=-1))
        self.find_edit.returnPressed.connect(lambda: self._find(step=1))
        self.wrap_cb.toggled.connect(self._set_wrap)
        self.btn_open.clicked.connect(self._open_file)
        self.editor.cursorPositionChanged.connect(self._update_cursor_pos)

        if content is not None:
            self.editor.setPlainText(content)
            self.lbl_msg.setText(file_path or "")
            self.editor.moveCursor(QTextCursor.Start)
            self.highlighter = MiniHighlighter(self.editor.document(), "json")
            self._update_cursor_pos()
        elif file_path:
            self.load_file(file_path)

    def _update_cursor_pos(self):
        cur = self.editor.textCursor()
        line = cur.blockNumber() + 1
        col = cur.columnNumber() + 1
        self.lbl_pos.setText(f"Ln {line}, Col {col}")

    def on_editor_cursor_moved(self):
        # called from CodeEditor for the status
        self._update_cursor_pos()

    def _set_wrap(self, enabled: bool):
        if enabled:
            self.editor.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        else:
            self.editor.setLineWrapMode(QPlainTextEdit.NoWrap)

    def _find(self, step=1):
        txt = self.find_edit.text()
        if not txt:
            return
        flags = QTextDocument.FindFlags()
        if step < 0:
            flags |= QTextDocument.FindBackward
        cursor = self.editor.textCursor()
        if step > 0:
            start = cursor.selectionEnd()
        else:
            start = cursor.selectionStart()
        found = self.editor.find(txt, flags)
        if not found:
            if step > 0:
                self.editor.moveCursor(QTextCursor.Start)
            else:
                self.editor.moveCursor(QTextCursor.End)
            self.editor.find(txt, flags)
        self._update_cursor_pos()

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open file",
                                              self.file_path or os.getcwd())
        if path:
            self.load_file(path)

    def load_file(self, path):
        try:
            f = QFile(path)
            if not f.open(QIODevice.ReadOnly | QIODevice.Text):
                raise RuntimeError("Can't open file")
            size = f.size()
            kb = max(1, int(size // 1024))
            self.lbl_size.setText(f"{kb} KB")
            self.lbl_msg.setText(path)
            if size < util.TEXT_LOAD_WHOLE_MAX_BYTES:
                txt = bytes(f.readAll()).decode('utf-8', errors='replace')
                self.editor.setPlainText(txt)
            else:
                self.editor.setPlainText("")
                stream = QTextStream(f)
                stream.setCodec('UTF-8')
                self.editor.setUpdatesEnabled(False)
                chunk = []
                while not stream.atEnd():
                    chunk.append(stream.read(util.TEXT_STREAM_CHUNK))
                self.editor.setPlainText("".join(chunk))
                self.editor.setUpdatesEnabled(True)

            ext = os.path.splitext(path)[1].lower()
            mode = None
            if ext == ".py":
                mode = "python"
            elif ext == ".json":
                mode = "json"
            elif ext in (".yml", ".yaml"):
                mode = "yaml"
            elif ext in (".log", ".out", ".err"):
                mode = "log"

            self.highlighter = MiniHighlighter(self.editor.document(),
                                               mode) if mode else None
            f.close()
            self.editor.moveCursor(QTextCursor.Start)
            self._update_cursor_pos()
        except Exception as e:
            QMessageBox.critical(self, "Open failed", str(e))


class NumpyTableModel(QAbstractTableModel):
    def __init__(self, data: np.ndarray, parent=None):
        super().__init__(parent)
        self._data = np.asarray(data)
        if self._data.ndim == 1:
            self._data = self._data.reshape(-1, 1)

    def rowCount(self, parent=QModelIndex()):
        return int(self._data.shape[0])

    def columnCount(self, parent=QModelIndex()):
        return int(self._data.shape[1])

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            v = self._data[index.row(), index.column()]
            if isinstance(v, (float, np.floating)):
                return f"{float(v):.6g}"
            return str(v)
        if role == Qt.TextAlignmentRole:
            return Qt.AlignRight | Qt.AlignVCenter
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return f"Col {section}"
        return f"Row {section}"


class TableViewerWindow(BaseWindow):
    """Table viewer for 1D/2D arrays"""
    def __init__(self, parent=None, title="", data=None,
                 ratio=util.TEXT_WIN_RATIO):
        super().__init__(parent, title, ratio)
        m_val = 4
        line_hei = 30
        layout = QVBoxLayout(self)
        layout.setContentsMargins(m_val, m_val, m_val, m_val)
        layout.setSpacing(4)

        # Toolbar row
        bar = QWidget()
        bar.setContentsMargins(0, 0, 0, 0)
        row = QHBoxLayout(bar)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)

        self.edt_find = QLineEdit()
        self.edt_find.setPlaceholderText("Find…")
        self.edt_find.setFixedHeight(line_hei)

        self.btn_copy = QPushButton("Copy selection")
        self.btn_copy.setFixedHeight(line_hei)

        self.btn_save = QPushButton("Save CSV")
        self.btn_save.setFixedHeight(line_hei)

        self.lbl_info = QLabel("")
        self.lbl_info.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        row.addWidget(self.edt_find, 1)
        row.addWidget(self.btn_copy, 0)
        row.addWidget(self.btn_save, 0)
        row.addWidget(self.lbl_info, 0)

        layout.addWidget(bar, 0)

        # Table view (virtualized)
        self.view = QTableView()
        self.view.setAlternatingRowColors(True)
        self.view.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.view.setSortingEnabled(True)
        self.view.setWordWrap(False)
        self.view.setCornerButtonEnabled(False)
        self.view.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.view.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

        # Headers
        hh = self.view.horizontalHeader()
        hh.setStretchLastSection(False)
        hh.setSectionResizeMode(QHeaderView.Interactive)
        hh.setDefaultAlignment(Qt.AlignCenter)

        vh = self.view.verticalHeader()
        vh.setSectionResizeMode(QHeaderView.Fixed)
        vh.setDefaultSectionSize(22)

        layout.addWidget(self.view, 1)

        # Model + proxy (sorting)
        arr = np.asarray(data)
        self.model = NumpyTableModel(arr, self)
        self.proxy = QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.view.setModel(self.proxy)

        # Info + actions
        r, c = self.model.rowCount(), self.model.columnCount()
        self.lbl_info.setText(f"{r} × {c}")

        self.edt_find.textChanged.connect(self._on_find_changed)
        self.btn_copy.clicked.connect(self._copy_selection_to_clipboard)
        self.btn_save.clicked.connect(self._save_csv)

        # Make it readable without huge columns
        self.view.resizeColumnsToContents()
        self.view.resizeRowsToContents()

    def _on_find_changed(self, txt: str):
        self.proxy.setFilterFixedString(txt)

    def _copy_selection_to_clipboard(self):
        sel = self.view.selectionModel().selectedIndexes()
        if not sel:
            return
        sel = sorted(sel, key=lambda i: (i.row(), i.column()))
        rows = {}
        for idx in sel:
            rows.setdefault(idx.row(), {})[idx.column()] = idx.data()

        # rectangular output with tabs/newlines (Excel-friendly)
        min_r, max_r = min(rows.keys()), max(rows.keys())
        min_c = min(min(cols.keys()) for cols in rows.values())
        max_c = max(max(cols.keys()) for cols in rows.values())

        lines = []
        for r in range(min_r, max_r + 1):
            cols = rows.get(r, {})
            line = []
            for c in range(min_c, max_c + 1):
                line.append(str(cols.get(c, "")))
            lines.append("\t".join(line))

        QApplication.clipboard().setText("\n".join(lines))

    def _save_csv(self):
        rows = self.proxy.rowCount()
        cols = self.proxy.columnCount()
        if rows <= 0 or cols <= 0:
            QMessageBox.information(self, "Nothing to save", "Table is empty.")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Save Table As", "",
                                              "CSV (*.csv)")
        if not path:
            return
        out = np.empty((rows, cols), dtype=object)
        for r in range(rows):
            for c in range(cols):
                p_idx = self.proxy.index(r, c)
                s_idx = self.proxy.mapToSource(p_idx)
                try:
                    out[r, c] = self.model._data[s_idx.row(), s_idx.column()]
                except Exception:
                    out[r, c] = p_idx.data()

        err = util.save_table(path, out)
        if err:
            QMessageBox.critical(self, "Save failed", str(err))
        else:
            QMessageBox.information(self, "Saved", f"CSV saved to:\n{path}")


class StatisticsWindow(BaseWindow):
    """Display Image Statistics"""

    def __init__(self, parent=None, title="", stats=None, help_text=""):
        super().__init__(parent, title + " " + help_text, ratio=0.4)
        self.resize(400, 300)
        layout = QVBoxLayout(self)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)

        if stats:
            self.table.setRowCount(len(stats))
            for i, (metric, value) in enumerate(stats.items()):
                self.table.setItem(i, 0, QTableWidgetItem(metric))
                self.table.setItem(i, 1, QTableWidgetItem(f"{value:.5f}"))

        layout.addWidget(self.table)


class Viewer2DWindow(BaseWindow):
    """2D Image Viewer using pyqtgraph"""
    def __init__(self, parent=None, title="", image=None, file_path="",
                 ratio=util.PLT_WIN_2D_RATIO):
        super().__init__(parent, title, ratio)
        self.parent_app = parent
        self.file_path = file_path
        self.image = np.asarray(image)
        self.is_color = False

        # Preprocessing
        if self.image.ndim == 3 and self.image.shape[2] in [3, 4]:
            self.is_color = True
            nmin, nmax = np.min(self.image), np.max(self.image)
            if nmax > nmin:
                self.image = (self.image - nmin) / (nmax - nmin)
            self.image = np.clip(self.image, 0.0, 1.0)
        if np.isnan(self.image).any():
            self.image = np.nan_to_num(self.image)

        # UI Setup
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(util.UI_MARGIN_S, util.UI_MARGIN_S,
                                       util.UI_MARGIN_S, util.UI_MARGIN_S)
        main_layout.setSpacing(util.UI_SPACING_M)
        # Canvas Area
        self.imv = pg.ImageView()
        grid = self.imv.ui.gridLayout
        grid.setHorizontalSpacing(util.UI_SPACING_M)
        grid.setContentsMargins(util.UI_MARGIN_XS, util.UI_MARGIN_XS,
                                util.UI_MARGIN_XS, util.UI_MARGIN_XS)
        hist_w = self.imv.getHistogramWidget()
        gui_font = QApplication.font()

        hist_font = QFont(gui_font)
        hist_font.setPointSize(max(8, gui_font.pointSize() - 3))

        hist = self.imv.getHistogramWidget()
        hist_axis = hist.axis

        hist_axis.setTickFont(hist_font)
        hist_axis.label.setFont(hist_font)
        hist_w.setMinimumWidth(util.HIST_MIN_W)

        self.imv.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.imv.ui.roiBtn.hide()
        self.imv.ui.menuBtn.hide()
        self.imv.view.setDefaultPadding(0)

        # Set bright-grey background for Histogram handles (triangles)
        self.imv.getHistogramWidget().setBackground(pg.mkColor(220, 220, 220))

        self.imv.setImage(self.image)
        self.imv.view.autoRange(padding=0)
        main_layout.addWidget(self.imv, 0)

        # --- Control Area: single row, tight layout ---
        controls = QWidget()
        controls.setContentsMargins(0, 0, 0, 0)
        row = QHBoxLayout(controls)
        row.setContentsMargins(util.UI_MARGIN_XS, util.UI_MARGIN_XS,
                               util.UI_MARGIN_S, 0)
        row.setSpacing(util.UI_SPACING_M)

        self.btn_reset = QPushButton("Reset")
        self.btn_reset.clicked.connect(self.reset)

        self.btn_stats = QPushButton("Statistics")
        self.btn_stats.clicked.connect(self.open_statistics)

        self.btn_hist = QPushButton("Histogram")
        self.btn_hist.clicked.connect(self.open_histogram)

        self.btn_perc = QPushButton("Percentile")
        self.btn_perc.clicked.connect(self.open_percentile)

        self.lbl_aspect = QLabel("Aspect")
        self.lbl_aspect.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.combo_aspect = QComboBox()
        self.combo_aspect.addItems(["equal", "auto"])
        self.combo_aspect.currentTextChanged.connect(self.update_aspect_ratio)

        # uniform sizing
        buttons = [self.btn_reset, self.btn_stats, self.btn_hist, self.btn_perc]
        for b in buttons:
            b.setFixedHeight(util.BTN_H)

        max_w = max(b.sizeHint().width() for b in buttons)
        for b in buttons:
            b.setFixedWidth(max_w)

        self.combo_aspect.setFixedHeight(util.BTN_H)

        row.addWidget(self.btn_reset)
        row.addWidget(self.btn_stats)
        row.addWidget(self.btn_hist)
        row.addWidget(self.btn_perc)
        row.addSpacing(util.UI_MARGIN_L)
        row.addWidget(self.lbl_aspect)
        row.addWidget(self.combo_aspect)
        row.addStretch(1)

        controls.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        controls.setFixedHeight(controls.sizeHint().height())

        main_layout.addWidget(controls, 0)

        # --- Status bar row ---
        status_row = QWidget()
        status_layout = QHBoxLayout(status_row)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(4)

        self.msg_label = QLabel(self.file_path)
        self.msg_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.lbl_cursor = QLabel("x=—  y=—  value=—")
        self.lbl_cursor.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_cursor.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        status_layout.addWidget(self.msg_label, 1)
        status_layout.addWidget(self.lbl_cursor, 0)

        main_layout.addWidget(status_row, 0)
        self.imv.view.scene().sigMouseMoved.connect(self._on_mouse_moved)

    def _on_mouse_moved(self, pos):
        if self.image is None or self.image.ndim != 2:
            return
        vb = self.imv.view
        mouse_point = vb.mapSceneToView(pos)
        x = int(np.floor(mouse_point.x()))
        y = int(np.floor(mouse_point.y()))
        h, w = self.image.shape
        if 0 <= x < w and 0 <= y < h:
            v = self.image[y, x]
            if isinstance(v, (float, np.floating)):
                vtxt = f"{float(v):.6g}"
            else:
                vtxt = str(v)
            self.lbl_cursor.setText(f"x={x}  y={y}  value={vtxt}")
        else:
            self.lbl_cursor.setText("x=—  y=—  value=—")

    def update_aspect_ratio(self, text):
        if text == "equal":
            self.imv.view.setAspectLocked(True)
        else:
            self.imv.view.setAspectLocked(False)

    def reset(self):
        if self.image is not None:
            vmin, vmax = np.nanmin(self.image), np.nanmax(self.image)
            if vmin == vmax:
                vmin, vmax = vmin - 0.5, vmax + 0.5
            hist_item = self.imv.getHistogramWidget().item
            hist_item.region.setRegion([vmin, vmax])
            hist_item.gradient.loadPreset('grey')
            self.imv.setLevels(vmin, vmax)
            hist_item.autoHistogramRange()
            self.imv.view.autoRange(padding=0)

            if hasattr(self, "combo_aspect"):
                try:
                    self.combo_aspect.blockSignals(True)
                    self.combo_aspect.setCurrentText("equal")
                finally:
                    self.combo_aspect.blockSignals(False)
            try:
                self.update_aspect_ratio("equal")
            except Exception:
                pass

    def open_statistics(self):
        stats = util.get_image_statistics(self.image)
        win = StatisticsWindow(self,
                               title=f"Stats: "
                                     f"{os.path.basename(self.file_path)}",
                               stats=stats)
        win.setAttribute(Qt.WA_DeleteOnClose)
        win.show()

    def open_histogram(self):
        win = PlotWindow1D(self,
                           title=f"Histogram: "
                                 f"{os.path.basename(self.file_path)}",
                           data_y=self.image, plot_type="histogram")
        win.setAttribute(Qt.WA_DeleteOnClose)
        win.show()

    def open_percentile(self):
        try:
            percentiles, density = util.get_percentile_density(self.image)
            win = PlotWindow1D(self,
                               title=f"Percentile: "
                                     f"{os.path.basename(self.file_path)}",
                               data_x=percentiles, data_y=density,
                               plot_type="percentile")
            win.setAttribute(Qt.WA_DeleteOnClose)
            win.show()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def focusInEvent(self, event):
        if self.parent_app and hasattr(self.parent_app, 'set_active_viewer'):
            self.parent_app.set_active_viewer(self)
        super().focusInEvent(event)

    def closeEvent(self, event):
        try:
            self.imv.view.scene().sigMouseMoved.disconnect(self._on_mouse_moved)
        except (TypeError, RuntimeError):
            pass
        try:
            if hasattr(self, "imv") and self.imv is not None:
                try:
                    self.imv.clear()
                except Exception:
                    pass
                try:
                    self.imv.setParent(None)
                except Exception:
                    pass
                try:
                    self.imv.deleteLater()
                except Exception:
                    pass
                self.imv = None
        except Exception:
            pass
        super().closeEvent(event)


class InteractiveViewerWindow(BaseWindow):
    """3D Stack Viewer using pyqtgraph"""

    def __init__(self, parent_app, file_path, file_type, hdf_key=None,
                 list_files=None):
        ratio = util.PLT_WIN_3D_RATIO
        title = f"Viewing: {os.path.basename(file_path)}"
        super().__init__(parent_app, title, ratio)

        self.parent_app = parent_app
        self.file_path = file_path
        self.file_type = file_type
        self.hdf_key = hdf_key
        self.list_files = list_files
        self.hdf_file_obj = None

        # Initialization logic from original
        if file_type == "tif":
            self.depth = len(list_files)
            initial_image = util.load_image(list_files[0], average=True)
            self.height, self.width = initial_image.shape[:2]
        elif file_type == "cine":
            metadata = util.get_metadata_cine(file_path)
            self.width = metadata["biWidth"]
            self.height = metadata["biHeight"]
            self.depth = metadata["TotalImageCount"]
            initial_image = util.extract_frame_cine(file_path, 0)
        elif file_type == "hdf":
            self.data_obj, self.hdf_file_obj = util.load_hdf(
                file_path, hdf_key, return_file_obj=True)
            self.depth, self.height, self.width = self.data_obj.shape
            initial_image = self.data_obj[0, :, :]

        self.viewer_state = {
            "image": initial_image,
            "table": None,
            "index": 0,
            "axis": 0,
            "img_width": self.width,
            "img_height": self.height,
            "img_depth": self.depth,
            "last_profile_point": None,
            "last_profile_orientation": None
        }

        # Debounce timer
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.setInterval(util.DEBOUNCE_TIMER_MS)
        self.update_timer.timeout.connect(self.perform_update)

        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(util.UI_MARGIN_S, util.UI_MARGIN_S,
                                       util.UI_MARGIN_S, util.UI_MARGIN_S)
        main_layout.setSpacing(0)

        # Canvas Area (Image + Plot)
        canvas_widget = QWidget()
        canvas_layout = QHBoxLayout(canvas_widget)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.setSpacing(util.UI_SPACING_S)

        self.imv = pg.ImageView()
        self.imv.view.setMenuEnabled(False)
        self.imv.ui.roiBtn.hide()
        self.imv.ui.menuBtn.hide()

        self.imv.ui.gridLayout.setContentsMargins(util.UI_MARGIN_XS,
                                                  util.UI_MARGIN_XS,
                                                  util.UI_MARGIN_XS,
                                                  util.UI_MARGIN_XS)
        self.imv.ui.gridLayout.setSpacing(util.UI_SPACING_M)
        self.imv.view.setDefaultPadding(0)

        # --- Darker histogram/LUT background so white triangles are visible ---
        hist_w = self.imv.getHistogramWidget()
        hist_w.setMinimumWidth(util.HIST_MIN_W)
        hist_w.setMaximumWidth(util.HIST_MAX_W)
        hist_w.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        hist_w.setBackground(pg.mkColor(215, 215, 215))

        # Profile plot
        self.plot_widget = pg.PlotWidget(title="Line Profile")
        self.plot_widget.getViewBox().setDefaultPadding(0)
        self.plot_curve = self.plot_widget.plot(pen='b')

        # --- Make plot fonts match GUI font ---
        gui_font = QApplication.font()
        plot_font = QFont(gui_font)
        plot_font.setPointSize(max(8, gui_font.pointSize() - 3))
        for axis_name in ("bottom", "left"):
            axis = self.plot_widget.getAxis(axis_name)
            axis.setTickFont(plot_font)
            axis.label.setFont(plot_font)
        self.plot_widget.getPlotItem().titleLabel.setFont(plot_font)

        hist = self.imv.getHistogramWidget()
        hist_axis = hist.axis
        hist_axis.setTickFont(plot_font)
        hist_axis.label.setFont(plot_font)

        canvas_layout.addWidget(self.imv, 3)
        canvas_layout.addWidget(self.plot_widget, 2)
        main_layout.addWidget(canvas_widget, 1)

        # Interactions
        self.imv.view.scene().sigMouseClicked.connect(self.on_image_click)
        self.imv.view.sigRangeChanged.connect(self.on_view_range_changed)

        # Profile Lines
        self.v_line = pg.InfiniteLine(angle=90, movable=False, pen='r')
        self.h_line = pg.InfiniteLine(angle=0, movable=False, pen='r')
        self.imv.addItem(self.v_line, ignoreBounds=True)
        self.imv.addItem(self.h_line, ignoreBounds=True)
        self.v_line.hide()
        self.h_line.hide()

        # Controls
        controls = QWidget()
        c_layout = QGridLayout(controls)
        c_layout.setHorizontalSpacing(util.UI_SPACING_M)
        c_layout.setVerticalSpacing(util.UI_SPACING_M)
        c_layout.setContentsMargins(util.UI_MARGIN_S, util.UI_MARGIN_S,
                                    util.UI_MARGIN_S, 0)

        # Row 0
        if self.file_type == "hdf" or self.depth > 1:
            self.radio_axis0 = QRadioButton("Axis 0")
            self.radio_axis0.setChecked(True)
            self.radio_axis0.toggled.connect(
                lambda checked: self.on_axis_select(0) if checked else None)
            c_layout.addWidget(self.radio_axis0, 0, 0,
                               alignment=Qt.AlignVCenter)
            self.slider0 = QSlider(Qt.Horizontal)
            self.slider0.setRange(0, self.depth - 1)
            self.slider0.valueChanged.connect(self.on_slice_change_request)
            self.slider0.setFixedHeight(20)
            c_layout.addWidget(self.slider0, 0, 1, alignment=Qt.AlignVCenter)

            self.lbl_slice0 = QLabel("0")
            self.lbl_slice0.setFixedWidth(40)
            c_layout.addWidget(self.lbl_slice0, 0, 2, alignment=Qt.AlignVCenter)
        else:
            c_layout.addWidget(QWidget(), 0, 0, 1, 3)

        self.btn_reset = QPushButton("Reset")
        self.btn_reset.clicked.connect(self.reset)
        c_layout.addWidget(self.btn_reset, 0, 3, alignment=Qt.AlignVCenter)

        self.btn_stats = QPushButton("Statistics")
        self.btn_stats.clicked.connect(self.open_statistics)
        c_layout.addWidget(self.btn_stats, 0, 4, alignment=Qt.AlignVCenter)

        self.btn_save_img = QPushButton("Save Image")
        self.btn_save_img.clicked.connect(self.save_current_image)
        c_layout.addWidget(self.btn_save_img, 0, 5, alignment=Qt.AlignVCenter)

        self.lbl_aspect = QLabel("Aspect")
        self.lbl_aspect.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        c_layout.addWidget(self.lbl_aspect, 0, 6)

        # Row 1
        if self.file_type == "hdf" and self.height > 1 and self.depth > 1:
            self.radio_axis1 = QRadioButton("Axis 1")
            self.radio_axis1.toggled.connect(
                lambda checked: self.on_axis_select(1) if checked else None)
            c_layout.addWidget(self.radio_axis1, 1, 0,
                               alignment=Qt.AlignVCenter)

            self.slider1 = QSlider(Qt.Horizontal)
            self.slider1.setRange(0, self.height - 1)
            self.slider1.setEnabled(False)
            self.slider1.valueChanged.connect(self.on_slice_change_request)
            self.slider1.setFixedHeight(20)
            c_layout.addWidget(self.slider1, 1, 1, alignment=Qt.AlignVCenter)

            self.lbl_slice1 = QLabel("0")
            self.lbl_slice1.setFixedWidth(40)
            c_layout.addWidget(self.lbl_slice1, 1, 2, alignment=Qt.AlignVCenter)
        else:
            c_layout.addWidget(QWidget(), 1, 0, 1, 3)

        self.btn_hist = QPushButton("Histogram")
        self.btn_hist.clicked.connect(self.open_histogram)
        c_layout.addWidget(self.btn_hist, 1, 3, alignment=Qt.AlignVCenter)

        self.btn_perc = QPushButton("Percentile")
        self.btn_perc.clicked.connect(self.open_percentile)
        c_layout.addWidget(self.btn_perc, 1, 4, alignment=Qt.AlignVCenter)

        self.btn_save_tbl = QPushButton("Save Table")
        self.btn_save_tbl.clicked.connect(self.save_current_table)
        c_layout.addWidget(self.btn_save_tbl, 1, 5, alignment=Qt.AlignVCenter)

        self.combo_aspect = QComboBox()
        self.combo_aspect.addItems(["equal", "auto"])
        self.combo_aspect.currentTextChanged.connect(self.update_aspect_ratio)
        self.combo_aspect.setFixedHeight(util.BTN_H)
        c_layout.addWidget(self.combo_aspect, 1, 6, alignment=Qt.AlignVCenter)

        # --- Make buttons same width/height ---
        buttons_equal = [self.btn_reset, self.btn_stats, self.btn_save_img,
                         self.btn_hist, self.btn_perc, self.btn_save_tbl]
        for b in buttons_equal:
            b.setFixedHeight(util.BTN_H)
        max_w = max(b.sizeHint().width() for b in buttons_equal)
        for b in buttons_equal:
            b.setFixedWidth(max_w)
        # keep slider column expanding
        c_layout.setColumnStretch(1, 1)
        main_layout.addWidget(controls, 0)

        # Status message
        status_row = QWidget()
        status_layout = QHBoxLayout(status_row)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(4)
        self.msg_label = QLabel(self.file_path)
        self.msg_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.lbl_cursor = QLabel("x=—  y=—  value=—")
        self.lbl_cursor.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_cursor.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        status_layout.addWidget(self.msg_label, 1)
        status_layout.addWidget(self.lbl_cursor, 0)
        main_layout.addWidget(status_row, 0)
        self.imv.view.scene().sigMouseMoved.connect(self._on_mouse_moved)

        self.imv.setImage(self.viewer_state["image"])
        self.imv.view.autoRange(padding=0)

    def _on_mouse_moved(self, pos):
        img = self.viewer_state.get("image")
        if img is None or getattr(img, "ndim", 0) != 2:
            return
        vb = self.imv.view
        mouse_point = vb.mapSceneToView(pos)
        x = int(np.floor(mouse_point.x()))
        y = int(np.floor(mouse_point.y()))
        h, w = img.shape[:2]
        if 0 <= x < w and 0 <= y < h:
            v = img[y, x]
            if isinstance(v, (float, np.floating)):
                vtxt = f"{float(v):.6g}"
            else:
                vtxt = str(v)
            self.lbl_cursor.setText(f"x={x}  y={y}  value={vtxt}")
        else:
            self.lbl_cursor.setText("x=—  y=—  value=—")

    def update_aspect_ratio(self, text):
        if text == "equal":
            self.imv.view.setAspectLocked(True)
        else:
            self.imv.view.setAspectLocked(False)

    def reset(self):
        img = self.viewer_state["image"]
        if img is not None:
            vmin, vmax = np.nanmin(img), np.nanmax(img)
            if vmin == vmax:
                vmin, vmax = vmin - 0.5, vmax + 0.5
            hist_item = self.imv.getHistogramWidget().item
            hist_item.region.setRegion([vmin, vmax])
            hist_item.gradient.loadPreset('grey')
            self.imv.setLevels(vmin, vmax)
            hist_item.autoHistogramRange()
            self.imv.view.autoRange(padding=0)

            if hasattr(self, "combo_aspect"):
                try:
                    self.combo_aspect.blockSignals(True)
                    self.combo_aspect.setCurrentText("equal")
                finally:
                    self.combo_aspect.blockSignals(False)
            try:
                self.update_aspect_ratio("equal")
            except Exception:
                pass

    def on_slice_change_request(self, value):
        if self.depth == 1 or (hasattr(self, 'height') and self.height == 1):
            return
        axis = self.viewer_state["axis"]
        if axis == 0:
            self.lbl_slice0.setText(str(value))
        else:
            self.lbl_slice1.setText(str(value))
        self.update_timer.start()

    def perform_update(self):
        axis = self.viewer_state["axis"]
        index = self.slider0.value() if axis == 0 else \
            (self.slider1.value() if hasattr(self, 'slider1') else 0)
        prev = self.viewer_state.get("image")
        prev_shape = prev.shape[:2] if (
                    prev is not None and hasattr(prev, "shape")) else None
        try:
            if self.file_type == "tif":
                img = util.load_image(self.list_files[index], average=True)
            elif self.file_type == "cine":
                img = util.extract_frame_cine(self.file_path, index)
            elif self.file_type == "hdf":
                if axis == 0:
                    img = self.data_obj[index, :, :]
                else:
                    img = self.data_obj[:, index, :]
        except Exception as e:
            util.logger.error(f"Error loading slice: {e}")
            return

        hei, wid = img.shape[:2]
        self.viewer_state["image"] = img
        self.viewer_state["index"] = index

        shape_changed = False
        if self.file_type == "tif" and prev_shape is not None:
            new_shape = (hei, wid)
            shape_changed = (prev_shape != new_shape)

        if shape_changed:
            self.height, self.width = hei, wid
            self.viewer_state["img_height"] = hei
            self.viewer_state["img_width"] = wid
            if self.viewer_state.get("last_profile_point"):
                y0, x0 = self.viewer_state["last_profile_point"]
                if not (0 <= y0 < hei and 0 <= x0 < wid):
                    self.clear_profile()
            else:
                self.clear_profile()
            self.imv.setImage(img, autoLevels=True, autoRange=True)
            self.reset()
        else:
            self.imv.setImage(img, autoLevels=False, autoRange=False)

        if self.file_type == "tif":
            self.msg_label.setText(
                f"{self.list_files[index]} | Slice: {index} | Axis: "
                f"{axis} | HxW: {hei}x{wid}")
        else:
            self.msg_label.setText(
                f"{self.file_path} | Slice: {index} | Axis: "
                f"{axis} | HxW: {hei}x{wid}")

        if self.viewer_state["last_profile_point"]:
            self.update_profile()
        else:
            self.on_view_range_changed()

    def on_axis_select(self, axis_idx):
        self.viewer_state["axis"] = axis_idx
        if axis_idx == 0:
            self.slider0.setEnabled(True)
            if hasattr(self, 'slider1'):
                self.slider1.setEnabled(False)
        else:
            self.slider0.setEnabled(False)
            if hasattr(self, 'slider1'):
                self.slider1.setEnabled(True)

        self.clear_profile()
        self.perform_update()
        self.reset()

    def clear_profile(self):
        self.viewer_state["table"] = None
        self.viewer_state["last_profile_point"] = None
        self.viewer_state["last_profile_orientation"] = None
        self.v_line.hide()
        self.h_line.hide()
        self.plot_curve.setData([])

    def on_view_range_changed(self):
        if not self.viewer_state["last_profile_point"]:
            return

        orientation = self.viewer_state["last_profile_orientation"]
        data = self.viewer_state["table"]
        if data is None:
            return
        img = self.viewer_state["image"]
        if img is None:
            return
        h, w = img.shape[:2]
        n = w if orientation == "horizontal" else h
        if n <= 1:
            return
        vr = self.imv.view.viewRange()
        if orientation == "horizontal":
            x_min, x_max = vr[0][0], vr[0][1]
        else:
            x_min, x_max = vr[1][0], vr[1][1]

        if not (np.isfinite(x_min) and np.isfinite(x_max)):
            return

        x0 = int(np.clip(np.floor(min(x_min, x_max)), 0, n - 1))
        x1 = int(np.clip(np.ceil(max(x_min, x_max)), 0, n - 1))
        if x1 <= x0:
            return
        # Set plot X range strictly in index space
        self.plot_widget.setXRange(x0, x1, padding=0)
        # Robust Y range from the visible segment
        seg = np.asarray(data[x0:x1], dtype=np.float64)
        seg = seg[np.isfinite(seg)]
        if seg.size == 0:
            return
        lmin = float(seg.min())
        lmax = float(seg.max())
        pad = (lmax - lmin) * 0.05 if lmax != lmin else 1.0
        self.plot_widget.setYRange(lmin - pad, lmax + pad, padding=0)

    def on_image_click(self, event):
        if event.button() not in [Qt.LeftButton, Qt.RightButton]:
            return
        pos = event.pos()
        if self.imv.view.sceneBoundingRect().contains(pos):
            mouse_point = self.imv.view.mapSceneToView(pos)
            x, y = int(mouse_point.x()), int(mouse_point.y())
            img = self.viewer_state["image"]
            h, w = img.shape[:2]
            if 0 <= x < w and 0 <= y < h:
                orientation = 'horizontal' \
                    if event.button() == Qt.LeftButton else 'vertical'
                self.viewer_state["last_profile_point"] = (y, x)
                self.viewer_state["last_profile_orientation"] = orientation
                self.update_profile()

    def update_profile(self):
        if not self.viewer_state["last_profile_point"]:
            return
        y, x = self.viewer_state["last_profile_point"]
        orientation = self.viewer_state["last_profile_orientation"]
        img = self.viewer_state["image"]
        if orientation == 'horizontal':
            self.h_line.setPos(y)
            self.h_line.show()
            self.v_line.hide()
            data = np.asarray(img[y, :], dtype=np.float64)
            self.plot_widget.setTitle(f"Intensity at row: {y}")
        else:
            self.v_line.setPos(x)
            self.v_line.show()
            self.h_line.hide()
            # data = img[:, x]
            data = np.asarray(img[:, x], dtype=np.float64)
            self.plot_widget.setTitle(f"Intensity at column: {x}")
        if not np.isfinite(data).all():
            data = np.nan_to_num(data, nan=0.0, posinf=0.0, neginf=0.0)
        self.viewer_state["table"] = data
        self.plot_curve.setData(data)
        self.on_view_range_changed()

    def open_statistics(self):
        stats = util.get_image_statistics(self.viewer_state["image"])
        win = StatisticsWindow(self, title=f"Stats", stats=stats)
        win.show()

    def open_histogram(self):
        win = PlotWindow1D(self, title="Histogram",
                           data_y=self.viewer_state["image"],
                           plot_type="histogram")
        win.show()

    def open_percentile(self):
        try:
            percentiles, density = util.get_percentile_density(
                self.viewer_state["image"])
            win = PlotWindow1D(self, title="Percentile", data_x=percentiles,
                               data_y=density, plot_type="percentile")
            win.show()
        except Exception:
            pass

    def save_current_image(self):
        if hasattr(self.parent_app, "set_active_viewer"):
            self.parent_app.set_active_viewer(self)
        self.parent_app.save_to_image()

    def save_current_table(self):
        if hasattr(self.parent_app, "set_active_viewer"):
            self.parent_app.set_active_viewer(self)
        self.parent_app.save_to_table()

    def focusInEvent(self, event):
        p = self.parent_app
        if p and hasattr(p, 'set_active_viewer'):
            p.set_active_viewer(self)
        super().focusInEvent(event)

    def closeEvent(self, event):
        try:
            if hasattr(self, "update_timer") and self.update_timer:
                self.update_timer.stop()
        except Exception:
            pass
        try:
            self.imv.view.scene().sigMouseClicked.disconnect(
                self.on_image_click)
        except (TypeError, RuntimeError):
            pass
        try:
            self.imv.view.scene().sigMouseMoved.disconnect(self._on_mouse_moved)
        except (TypeError, RuntimeError):
            pass
        try:
            self.imv.view.sigRangeChanged.disconnect(self.on_view_range_changed)
        except (TypeError, RuntimeError):
            pass
        if self.hdf_file_obj:
            try:
                self.hdf_file_obj.close()
            except Exception:
                pass
        try:
            if hasattr(self, "imv") and self.imv is not None:
                try:
                    self.imv.clear()
                except Exception:
                    pass
                try:
                    self.imv.setParent(None)
                except Exception:
                    pass
                try:
                    self.imv.deleteLater()
                except Exception:
                    pass
                self.imv = None
        except Exception:
            pass
        try:
            if hasattr(self, "plot_widget") and self.plot_widget is not None:
                try:
                    self.plot_widget.clear()
                except Exception:
                    pass
                try:
                    self.plot_widget.setParent(None)
                except Exception:
                    pass
                try:
                    self.plot_widget.deleteLater()
                except Exception:
                    pass
                self.plot_widget = None
        except Exception:
            pass
        super().closeEvent(event)


class ExportDialog(BaseWindow):
    """
    Dialog for Export parameters
    """

    def __init__(self, parent_app, file_path, file_type, hdf_key=None,
                 shape=None):
        super().__init__(None, f"Export TIF: {os.path.basename(file_path)}",
                         0.5)
        self.input_width = 80
        self.parent_app = parent_app
        self.file_path = file_path
        self.file_type = file_type  # "hdf" | "cine"
        self.hdf_key = hdf_key
        self.shape = tuple(shape) if shape else (0, 0, 0)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(util.UI_MARGIN_S, util.UI_MARGIN_S,
                                  util.UI_MARGIN_S, util.UI_MARGIN_S)
        layout.setSpacing(util.UI_SPACING_L)

        # ---------------- Destination ----------------
        grp_dest = QGroupBox("Destination")
        gl_dest = QGridLayout(grp_dest)
        gl_dest.setContentsMargins(util.UI_MARGIN_S, util.UI_MARGIN_S,
                                   util.UI_MARGIN_S, util.UI_MARGIN_S)
        gl_dest.setHorizontalSpacing(util.UI_SPACING_S)
        gl_dest.setVerticalSpacing(util.UI_SPACING_S)

        self.txt_path = QLabel("No folder selected...")
        self.txt_path.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)

        btn_browse = QPushButton("Browse base folder")
        btn_browse.clicked.connect(self.browse_folder)

        self.edt_subfolder = QLineEdit("tifs")
        btn_mkdir = QPushButton("Make subfolder")
        btn_mkdir.clicked.connect(self.make_subfolder)

        gl_dest.addWidget(self.txt_path, 0, 0)
        gl_dest.addWidget(btn_browse, 0, 1)
        gl_dest.addWidget(self.edt_subfolder, 1, 0)
        gl_dest.addWidget(btn_mkdir, 1, 1)

        layout.addWidget(grp_dest)

        # ---------------- Slicing ----------------
        grp_slice = QGroupBox("Slicing")
        gl_slice = QGridLayout(grp_slice)
        gl_slice.setContentsMargins(util.UI_MARGIN_S, util.UI_MARGIN_S,
                                    util.UI_MARGIN_S, util.UI_MARGIN_S)
        gl_slice.setHorizontalSpacing(util.UI_SPACING_S)
        gl_slice.setVerticalSpacing(util.UI_SPACING_S)

        self.combo_axis = QComboBox()
        self.combo_axis.addItems(["Axis 0", "Axis 1"])
        if file_type == "cine":
            self.combo_axis.setEnabled(False)

        gl_slice.addWidget(QLabel("Export along:"), 0, 0)
        gl_slice.addWidget(self.combo_axis, 0, 1)

        gl_slice.addWidget(QLabel("Start:"), 1, 0)
        self.edt_start = QLineEdit("0")
        gl_slice.addWidget(self.edt_start, 1, 1, alignment=Qt.AlignLeft)

        gl_slice.addWidget(QLabel("Stop (-1=End):"), 1, 2)
        self.edt_stop = QLineEdit("-1")
        gl_slice.addWidget(self.edt_stop, 1, 3, alignment=Qt.AlignLeft)

        gl_slice.addWidget(QLabel("Step:"), 1, 4)
        self.edt_step = QLineEdit("1")
        gl_slice.addWidget(self.edt_step, 1, 5, alignment=Qt.AlignLeft)
        layout.addWidget(grp_slice)

        # ---------------- Cropping ----------------
        grp_crop = QGroupBox("Cropping")
        gl_crop = QGridLayout(grp_crop)
        gl_crop.setContentsMargins(util.UI_MARGIN_S, util.UI_MARGIN_S,
                                   util.UI_MARGIN_S, util.UI_MARGIN_S)
        gl_crop.setHorizontalSpacing(util.UI_SPACING_S)
        gl_crop.setVerticalSpacing(util.UI_SPACING_S)
        gl_crop.setColumnStretch(0, 0)
        gl_crop.setColumnStretch(1, 0)
        gl_crop.setColumnStretch(2, 0)
        gl_crop.setColumnStretch(3, 0)
        gl_crop.setColumnStretch(4, 1)

        gl_crop.addWidget(QLabel("Y-Start:"), 0, 0)
        self.edt_ystart = QLineEdit("0")
        gl_crop.addWidget(self.edt_ystart, 0, 1)

        gl_crop.addWidget(QLabel("Y-Stop (-1):"), 0, 2)
        self.edt_ystop = QLineEdit("-1")
        gl_crop.addWidget(self.edt_ystop, 0, 3)

        gl_crop.addWidget(QLabel("X-Start:"), 1, 0)
        self.edt_xstart = QLineEdit("0")
        gl_crop.addWidget(self.edt_xstart, 1, 1)

        gl_crop.addWidget(QLabel("X-Stop (-1):"), 1, 2)
        self.edt_xstop = QLineEdit("-1")
        gl_crop.addWidget(self.edt_xstop, 1, 3)
        layout.addWidget(grp_crop)

        # ---------------- Rescaling ----------------
        grp_rescale = QGroupBox("Rescaling")
        gl_resc = QGridLayout(grp_rescale)
        gl_resc.setContentsMargins(util.UI_MARGIN_S, util.UI_MARGIN_S,
                                   util.UI_MARGIN_S, util.UI_MARGIN_S)
        gl_resc.setHorizontalSpacing(util.UI_SPACING_S)
        gl_resc.setVerticalSpacing(util.UI_SPACING_S)

        self.combo_rescale = QComboBox()
        self.combo_rescale.addItems(["None", "8-bit", "16-bit"])
        gl_resc.addWidget(QLabel("Rescale to:"), 0, 0)
        gl_resc.addWidget(self.combo_rescale, 0, 1)

        gl_resc.addWidget(QLabel("Min %:"), 1, 0)
        self.edt_minp = QLineEdit("0")
        gl_resc.addWidget(self.edt_minp, 1, 1)

        gl_resc.addWidget(QLabel("Max %:"), 1, 2)
        self.edt_maxp = QLineEdit("100")
        gl_resc.addWidget(self.edt_maxp, 1, 3)

        gl_resc.addWidget(QLabel("Sample Step:"), 1, 4)
        self.edt_samp = QLineEdit("10")
        gl_resc.addWidget(self.edt_samp, 1, 5)
        layout.addWidget(grp_rescale)

        # ---------------- Run ----------------
        h_run = QHBoxLayout()
        h_run.setContentsMargins(util.UI_MARGIN_S, util.UI_MARGIN_S,
                                 util.UI_MARGIN_S, util.UI_MARGIN_S)
        h_run.setSpacing(util.UI_SPACING_S)

        h_run.addWidget(QLabel("Prefix:"))
        self.edt_prefix = QLineEdit("img")
        self.edt_prefix.setAlignment(Qt.AlignLeft)
        h_run.addWidget(self.edt_prefix)
        h_run.addStretch(0)

        self.btn_export = QPushButton("Export")
        self.btn_export.setFixedWidth(150)
        self.btn_export.clicked.connect(self.run_export)
        h_run.addWidget(self.btn_export)

        layout.addLayout(h_run)

        self.lbl_status = QLabel(f"Shape: {self.shape}")
        layout.addWidget(self.lbl_status)

        for w in (
                self.edt_start,
                self.edt_stop,
                self.edt_step,
                self.edt_ystart,
                self.edt_ystop,
                self.edt_xstart,
                self.edt_xstop,
                self.edt_minp,
                self.edt_maxp,
                self.edt_samp,
                self.edt_prefix,
        ):
            w.setAlignment(Qt.AlignLeft)
            w.setFixedWidth(self.input_width)

        self.adjustSize()
        self.setMinimumSize(self.sizeHint())

    def browse_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Select Destination")
        if d:
            self.txt_path.setText(os.path.normpath(d))

    def make_subfolder(self):
        base = self.txt_path.text().strip()
        sub = self.edt_subfolder.text().strip()

        if base == "No folder selected..." or not os.path.isdir(base):
            QMessageBox.critical(self, "Error",
                                 "Please select a base folder first.")
            return
        if not sub:
            QMessageBox.information(self, "Input needed",
                                    "Please give name for the new folder.")
            return

        path = os.path.join(base, sub)
        try:
            os.makedirs(path, exist_ok=True)
            self.txt_path.setText(path)
            self.edt_subfolder.setText("")
            QMessageBox.information(self, "Success", f"Folder created:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    @staticmethod
    def _parse_int(value, default=0, allow_negative=False):
        try:
            v = int(str(value).strip())
            if not allow_negative and v < 0 and v != -1:
                return default
            return v
        except Exception:
            return default

    def _axis(self) -> int:
        return 0 if self.combo_axis.currentIndex() == 0 else 1

    def validate_export_parameters(self):
        out_path = self.txt_path.text().strip()
        if not os.path.isdir(out_path):
            QMessageBox.critical(self, "Invalid Input",
                                 "Please select a valid folder.")
            return None

        prefix = self.edt_prefix.text().strip()
        if not prefix:
            QMessageBox.critical(self, "Invalid Input",
                                 "Please enter a file prefix.")
            return None

        depth, height, width = self.shape
        axis = self._axis()
        slice_dim = depth if axis == 0 else height
        s_start = self._parse_int(self.edt_start.text(), 0)
        s_stop = self._parse_int(self.edt_stop.text(), slice_dim,
                                 allow_negative=True)
        s_step = self._parse_int(self.edt_step.text(), 1)
        if s_step == 0:
            s_step = 1

        if s_stop == -1 or s_stop > slice_dim:
            s_stop = slice_dim
        if s_start < 0:
            s_start = 0
        if s_start >= s_stop:
            QMessageBox.critical(self, "Invalid Input",
                                 "Start index must be < Stop index.")
            return None
        # Crop dims: for axis==0, each slice is (height, width)
        # for axis==1, each slice is (depth, width)
        y_dim = height if axis == 0 else depth
        x_dim = width

        y_start = self._parse_int(self.edt_ystart.text(), 0)
        y_stop = self._parse_int(self.edt_ystop.text(), y_dim,
                                 allow_negative=True)
        x_start = self._parse_int(self.edt_xstart.text(), 0)
        x_stop = self._parse_int(self.edt_xstop.text(), x_dim,
                                 allow_negative=True)

        if y_stop == -1 or y_stop > y_dim:
            y_stop = y_dim
        if x_stop == -1 or x_stop > x_dim:
            x_stop = x_dim

        y_start = max(0, min(y_start, y_dim))
        x_start = max(0, min(x_start, x_dim))

        if y_start >= y_stop or x_start >= x_stop:
            QMessageBox.critical(self, "Invalid Input",
                                 "Invalid crop dimensions.")
            return None
        # Rescale
        rescale = self.combo_rescale.currentText()

        try:
            min_p = float(self.edt_minp.text().strip())
            max_p = float(self.edt_maxp.text().strip())
        except Exception:
            QMessageBox.critical(self, "Invalid Input",
                                 "Percentiles must be numbers.")
            return None
        if min_p >= max_p:
            QMessageBox.critical(self, "Invalid Input",
                                 "Min Percentile must be < Max.")
            return None

        slice_skip = self._parse_int(self.edt_samp.text(), 1)
        if slice_skip <= 0:
            slice_skip = 1

        return {
            "output_path": out_path,
            "input_path": self.file_path,
            "hdf_key": self.hdf_key,
            "prefix": prefix,
            "axis": axis,
            "slice_start": s_start,
            "slice_stop": s_stop,
            "slice_step": s_step,
            "y_start": y_start,
            "y_stop": y_stop,
            "x_start": x_start,
            "x_stop": x_stop,
            "rescale": rescale,
            "min_percent": min_p,
            "max_percent": max_p,
            "slice_skip": slice_skip,
        }

    def run_export(self):
        params = self.validate_export_parameters()
        if params is None:
            return

        self.btn_export.setEnabled(False)

        def _status(msg):
            self.lbl_status.setText(str(msg))
            QApplication.processEvents()

        _status("Exporting...")

        try:
            res = util.export_hdf_cine_to_tif(params, _status)
            if res == "Success":
                QMessageBox.information(self, "Done",
                                        f"Export Complete\n\nSaved to:"
                                        f"\n{params['output_path']}")
                self.lbl_status.setText(f"Shape: {self.shape}")
            else:
                self.lbl_status.setText(str(res))
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            self.lbl_status.setText(f"Shape: {self.shape}")
        finally:
            self.btn_export.setEnabled(True)


class DatviewMainWindow(QMainWindow):
    """Main Application Window"""
    # Signals for interactions.py to connect to
    sig_browse_requested = Signal()
    sig_folder_selected = Signal()
    sig_file_select_changed = Signal()
    sig_file_double_clicked = Signal(object)
    sig_launch_inter_requested = Signal()
    sig_launch_table_requested = Signal()
    sig_launch_export_requested = Signal()
    sig_tree_expand_requested = Signal(object)
    sig_ctx_copy_full_path = Signal(str)
    sig_ctx_rename_file = Signal(str)
    sig_ctx_make_subfolder = Signal(str)

    def __init__(self, base_folder="."):
        super().__init__()
        self.setWindowTitle(f"{util.APP_NAME}")
        icon_path = os.path.join(os.path.dirname(__file__),
                                 "..", "assets", "datview_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.setGeometry(calculate_geometry(util.MAIN_WIN_RATIO))

        self.base_folder = Path(base_folder).expanduser()
        if not self.base_folder.exists():
            self.base_folder = Path.home()
        self.selected_folder_path = str(self.base_folder)

        # Central Widget & Layout
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QGridLayout(central)
        main_layout.setContentsMargins(util.UI_MARGIN_M, util.UI_MARGIN_M,
                                       util.UI_MARGIN_M, util.UI_MARGIN_M)
        main_layout.setSpacing(util.UI_SPACING_L)

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(util.UI_MARGIN_M, 0, 0, 0)
        header_layout.setSpacing(util.UI_SPACING_L)

        title = QLabel("Current base: ")
        self.lbl_base_folder = QLabel(str(self.base_folder))
        self.lbl_base_folder.setTextInteractionFlags(Qt.TextSelectableByMouse)

        btn_select_folder = QPushButton("Select Base Folder")
        btn_select_folder.clicked.connect(self.sig_browse_requested)

        header_layout.addWidget(title, 0)
        header_layout.addWidget(self.lbl_base_folder, 1)
        header_layout.addWidget(btn_select_folder, 0)

        main_layout.addWidget(header, 0, 0, 1, 3)

        # --- Body Splitter ---
        body_splitter = QSplitter(Qt.Horizontal)

        # Left: Folder Tree
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setMinimumWidth(util.TREE_MIN_W)
        self.tree.itemExpanded.connect(
            lambda item: self.sig_tree_expand_requested.emit(item))
        self.tree.itemSelectionChanged.connect(self.sig_folder_selected)
        body_splitter.addWidget(self.tree)

        # Right: File list + actions
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(util.UI_SPACING_M)

        # File list
        self.list_files = QListWidget()
        self.list_files.itemSelectionChanged.connect(
            self.sig_file_select_changed)
        self.list_files.itemDoubleClicked.connect(
            lambda item: self.sig_file_double_clicked.emit(item))
        self.list_files.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_files.customContextMenuRequested.connect(
            self.on_file_context_menu)
        right_layout.addWidget(self.list_files, 1)

        actions_group = QGroupBox("")
        vs_layout = QGridLayout(actions_group)
        vs_layout.setContentsMargins(util.UI_MARGIN_S, util.UI_MARGIN_S,
                                     util.UI_MARGIN_S, util.UI_MARGIN_S)
        vs_layout.setHorizontalSpacing(util.UI_SPACING_M)
        vs_layout.setVerticalSpacing(util.UI_SPACING_M)

        btn_inter = QPushButton("Interactive Viewer")
        btn_inter.setToolTip(
            "View HDF dataset (array), CINE, or TIF stack in folder")
        btn_inter.clicked.connect(self.sig_launch_inter_requested)
        vs_layout.addWidget(btn_inter, 0, 0)

        btn_table = QPushButton("Table Viewer")
        btn_table.setToolTip("Show table of 1D/2D dataset in a HDF file")
        btn_table.clicked.connect(self.sig_launch_table_requested)
        vs_layout.addWidget(btn_table, 0, 1)

        self.combo_hdf = QComboBox()
        self.combo_hdf.setToolTip("HDF keys to array-like datasets")
        self.combo_hdf.setEnabled(False)
        self.combo_hdf.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.combo_hdf.setFixedHeight(util.BTN_H)
        vs_layout.addWidget(self.combo_hdf, 0, 2)
        self.combo_hdf.currentIndexChanged.connect(
            lambda _idx: self.list_files.setFocus())

        btn_export = QPushButton("Export to TIF")
        btn_export.setToolTip("Export 3D HDF/CINE dataset to TIF files")
        btn_export.clicked.connect(self.sig_launch_export_requested)
        vs_layout.addWidget(btn_export, 0, 3)

        # --- Uniform button sizing ---
        buttons_equal = [btn_inter, btn_table, btn_export]

        for b in buttons_equal:
            b.setMinimumHeight(util.BTN_H)

        max_width = max(b.sizeHint().width() for b in buttons_equal)
        for b in buttons_equal:
            b.setFixedWidth(max_width)

        right_layout.addWidget(actions_group, 0)
        body_splitter.addWidget(right_panel)

        # Make right side larger by default
        body_splitter.setStretchFactor(0, 1)
        body_splitter.setStretchFactor(1, 3)

        main_layout.addWidget(body_splitter, 1, 0, 1, 3)

        self._init_statusbar()

        main_layout.setRowStretch(1, 1)
        main_layout.setColumnStretch(1, 1)

    def _init_statusbar(self):
        sb = QStatusBar(self)
        sb.setSizeGripEnabled(True)
        self.setStatusBar(sb)
        sb.showMessage("Ready")

        self.sb_filetype = QLabel("")
        self.sb_dims = QLabel("")

        self.sb_filetype.setObjectName("StatusPill")
        self.sb_dims.setObjectName("StatusPill")

        sb.addPermanentWidget(self.sb_filetype)
        sb.addPermanentWidget(self.sb_dims)

    def on_file_context_menu(self, pos):
        if not getattr(self, "selected_folder_path", ""):
            return

        item = self.list_files.itemAt(pos)
        menu = QMenu(self)

        act_mkdir = menu.addAction("Make sub-folder")

        act_copy = None
        act_rename = None
        full_path = None

        if item is not None:
            fname = item.text()
            full_path = os.path.join(self.selected_folder_path, fname)
            act_copy = menu.addAction("Copy full path")
            act_rename = menu.addAction("Change file name")

        if item is not None and full_path and os.path.exists(full_path):
            info = util.get_file_created_size_lines(full_path)
            if info:
                menu.addSeparator()
                a1 = menu.addAction(info[0])
                a1.setEnabled(False)
                a2 = menu.addAction(info[1])
                a2.setEnabled(False)

        chosen = menu.exec(QCursor.pos())
        if chosen is None:
            return

        if chosen == act_mkdir:
            self.sig_ctx_make_subfolder.emit(self.selected_folder_path)
        elif act_copy is not None and chosen == act_copy and full_path:
            self.sig_ctx_copy_full_path.emit(full_path)
        elif act_rename is not None and chosen == act_rename and full_path:
            self.sig_ctx_rename_file.emit(full_path)
