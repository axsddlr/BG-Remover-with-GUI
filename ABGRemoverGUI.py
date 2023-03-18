import os
import sys
import time

from PyQt5.QtCore import QSettings, QPoint, QCoreApplication
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow, QAction, QFileDialog, QLabel, QWidget
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QProgressBar, QMessageBox, QDialog

from ABGR import apply_abgr

TOP_NAME = "arca.live/b/aiart"
APP_NAME = "ABG Remover GUI"
APP_TITLE = "ABG Remover GUI - Drag and drop to separate the background and image!"
TEXT_ABOUT = """
Main Channel: Archive AI Art Channel. https://arca.live/b/aiart
Author : https://arca.live/b/aiart @DeepCreamPy
Original WebUI extension function : https://github.com/KutsuyaYuki/ABG_extension
Original ABGRemoving : https://huggingface.co/spaces/skytnt/anime-remove-background
"""
TEXT_SAVE_LOC_DEFAULT = "(Location of the original image)"

SRC_EXECUTABLE_PATH = os.path.dirname(os.path.abspath(sys.executable)) if getattr(sys, 'frozen',
                                                                                  False) else os.path.dirname(
    os.path.abspath(__file__))
SRC_MODEL = SRC_EXECUTABLE_PATH + "\\" + "model\\isnetis.onnx"


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path).replace("\\", "/")


class Worker(QThread):
    progressChanged = pyqtSignal(int)

    def __init__(self, filenames, save_loc):
        super().__init__()
        self.power = True
        self.filenames = filenames
        self.count = len(filenames)
        self.save_loc = save_loc
        self.index = 0

    def run(self):
        while self.power:
            if self.index < self.count:
                print(str(self.index) + "/" + str(self.count), "번째 이미지 작업 시작")
                filename = self.filenames[self.index]
                apply_abgr(SRC_MODEL, filename, self.save_loc)
                self.progressChanged.emit(int(self.index / self.count * 99))
                self.index += 1
                print()
            else:
                self.power = False
                self.progressChanged.emit(100)

    def stop(self):
        # 멀티쓰레드를 종료하는 메소드
        self.power = False
        self.quit()
        self.wait(3000)  # 3초 대기 (바로 안꺼질수도)


class ProgressDialog(QDialog):
    def __init__(self, parent, filenames):
        super().__init__()
        self.filenames = filenames
        self.parent = parent
        self.initUI(parent.pos())
        QTimer.singleShot(100, self.start)
        super().exec_()

    def initUI(self, parent_pos):
        self.setWindowTitle('Sub Window')
        self.setGeometry(parent_pos.x() + 50, parent_pos.y() + 50, 200, 100)
        layout = QVBoxLayout()

        progressbar = QProgressBar(self)
        progressbar.setAlignment(Qt.AlignCenter)
        self.progressbar = progressbar

        label = QLabel("Loading...")
        label.setAlignment(Qt.AlignCenter)
        font = label.font()
        font.setPointSize(18)
        label.setFont(font)
        self.label = label

        button = QPushButton("Confirm")
        button.clicked.connect(self.on_button_clicked)
        button.setEnabled(False)
        self.button = button

        layout.addStretch(1)
        layout.addWidget(self.progressbar)
        layout.addWidget(self.label)
        layout.addStretch(1)
        layout.addWidget(self.button)
        layout.addStretch(1)

        self.setLayout(layout)

    def set_value(self, value):
        self.label.setText(str(value) + "%")
        self.progressbar.setValue(value)

        if value >= 100:
            self.button.setEnabled(True)
            print("=====Work completed!=====")

    def start(self):
        print("=====Starting the task=====")
        print()
        worker = Worker(self.filenames, self.parent.settings.value("save_location", ""))
        worker.progressChanged.connect(self.set_value)
        self.worker = worker
        worker.start()

    def on_button_clicked(self):
        self.worker.stop()
        self.reject()

    def closeEvent(self, event):
        if self.worker and self.worker.power:
            reply = QMessageBox.question(self, 'Confirm', 'Do you really want to stop the operation?',
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

            if reply == QMessageBox.Yes:
                self.worker.stop()
                event.accept()
            else:
                event.ignore()


class OptionDialog(QDialog):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.initUI(parent.pos())
        super().exec_()

    def initUI(self, parent_pos):
        self.setWindowTitle('Option Window')
        self.move(parent_pos.x() + 50, parent_pos.y() + 50)
        self.setFixedSize(300, 200)
        layout = QVBoxLayout()

        label_title = QLabel("File storage location : ", self)
        label_title.setStyleSheet("font-size: 20px")

        label_save_loc = QLabel(self.parent.get_save_loc())
        label_save_loc.setStyleSheet("font-size: 14px")
        self.label_save_loc = label_save_loc

        button_select_save_loc = QPushButton("Location change")
        button_select_save_loc.clicked.connect(self.on_button_clicked_select_save_loc)
        self.button_select_save_loc = button_select_save_loc

        button_reset_save_loc = QPushButton("Reset")
        button_reset_save_loc.clicked.connect(self.on_button_clicked_reset_save_loc)
        self.button_reset_save_loc = button_reset_save_loc

        button_close = QPushButton("Close")
        button_close.clicked.connect(self.on_button_clicked_close)
        self.button_close = button_close

        layout.addWidget(label_title, 1)

        layout.addWidget(self.label_save_loc, 1)
        qhl_save_loc = QHBoxLayout()
        qhl_save_loc.addWidget(self.button_select_save_loc, 4)
        qhl_save_loc.addWidget(self.button_reset_save_loc, 4)
        layout.addLayout(qhl_save_loc)

        layout.addStretch(2)

        qhl_close = QHBoxLayout()
        qhl_close.addStretch(4)
        qhl_close.addWidget(self.button_close, 2)
        layout.addLayout(qhl_close)

        self.setLayout(layout)

    def on_button_clicked_select_save_loc(self):
        select_dialog = QFileDialog()
        save_loc = select_dialog.getExistingDirectory(
            self, 'Please choose the location to save.')
        self.parent.set_save_loc(save_loc)
        self.label_save_loc.setText(self.parent.get_save_loc())

    def on_button_clicked_reset_save_loc(self):
        self.parent.set_save_loc("")
        self.label_save_loc.setText(self.parent.get_save_loc())

    def on_button_clicked_close(self):
        self.reject()


class MyWidget(QMainWindow):

    def __init__(self, app):
        super().__init__()
        self.app = app

        self.init_window()
        self.init_menubar()
        self.init_statusbar()
        self.init_content()
        self.show()

    def init_window(self):
        self.setWindowTitle(APP_TITLE)
        self.setWindowIcon(QIcon(resource_path('icon.ico')))
        self.settings = QSettings(TOP_NAME, APP_NAME)
        self.move(self.settings.value("pos", QPoint(300, 300)))
        self.setAcceptDrops(True)

    def init_content(self):
        menubar_height = self.menuBar().height()
        statusbar_height = self.statusBar().height()

        widget = QWidget()
        widget.resize(512, 512)
        self.setCentralWidget(widget)

        button = QPushButton("", widget)
        button.resize(512, 512)
        button.clicked.connect(self.show_select_dialog)
        button.setStyleSheet(
            "background-image: url(" + resource_path("content.png") + ");")
        self.button = button

        self.setFixedSize(512, int(512 + (menubar_height + statusbar_height) * 0.7))

    def init_menubar(self):
        selectAction = QAction('Select File(s) ...', self)
        selectAction.setShortcut('Ctrl+O')
        selectAction.setStatusTip('Select File(s) to apply ABG Removing')
        selectAction.triggered.connect(self.show_select_dialog)

        optionAction = QAction('Option', self)
        optionAction.setShortcut('Ctrl+U')
        optionAction.setStatusTip('Open option window')
        optionAction.triggered.connect(self.show_option_dialog)

        exitAction = QAction('Exit', self)
        exitAction.setShortcut('Ctrl+W')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(self.quit_app)

        aboutAction = QAction('About', self)
        aboutAction.setStatusTip('About application')
        aboutAction.triggered.connect(self.show_about_dialog)

        menubar = self.menuBar()
        menubar.setNativeMenuBar(False)
        filemenu = menubar.addMenu('&File')
        filemenu.addAction(selectAction)
        filemenu.addAction(optionAction)
        filemenu.addAction(exitAction)
        filemenu = menubar.addMenu('&Etc')
        filemenu.addAction(aboutAction)

    def init_statusbar(self):
        statusbar = self.statusBar()

        statusbar.messageChanged.connect(self.on_statusbar_message_changed)

        self.renew_statusbar()

    def renew_statusbar(self):
        statusbar = self.statusBar()

        statusbar.showMessage("save location : " + self.get_save_loc())

    def get_save_loc(self):
        save_loc = self.settings.value("save_location", "")
        return save_loc if save_loc else TEXT_SAVE_LOC_DEFAULT

    def set_save_loc(self, save_loc):
        self.settings.setValue("save_location", save_loc)
        self.init_statusbar()

    def show_option_dialog(self):
        OptionDialog(self)

    def show_select_dialog(self):
        select_dialog = QFileDialog()
        select_dialog.setFileMode(QFileDialog.ExistingFiles)
        fname = select_dialog.getOpenFileNames(
            self, 'Open file to apply ABGR', '', 'PNG File(*.png)')

        if fname != "" and isinstance(fname[0], list) and len(fname[0]) > 0:
            self.apply_abgr_to_files(fname[0])

    def show_about_dialog(self):
        QMessageBox.information(self, 'About', TEXT_ABOUT)

    def apply_abgr_to_files(self, filenames_target, check_png=False):
        text_warning = f'{str(len(filenames_target))} images will be processed. Do you want to ' \
                              f'proceed?'

        if check_png:
            filenames_prev = filenames_target[:]
            filenames_target = []

            for filepath in filenames_prev:
                if filepath.endswith('.png'):
                    filenames_target.append(filepath)

            # check length
            len_files = len(filenames_prev)
            len_pngs = len(filenames_target)

            text_warning = 'Total ' + f' Apply ABGR to {str(len_pngs)} images. Do you want to continue?'
            if len_files != len_pngs:
                text_warning = 'Selected ' + f'Select only PNG files among the {str(len_files)}files, \n' + text_warning

        reply = QMessageBox.question(self, 'Confirm', text_warning, QMessageBox.Yes | QMessageBox.No,
                                     QMessageBox.No)
        if reply == QMessageBox.Yes:
            ProgressDialog(self, filenames_target)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]

        self.apply_abgr_to_files(files, check_png=True)

    def closeEvent(self, e):
        self.settings.setValue("pos", self.pos())

        e.accept()

    def on_statusbar_message_changed(self, t):
        if not t:
            self.renew_statusbar()

    def quit_app(self):
        time.sleep(0.1)
        self.close()
        self.app.closeAllWindows()
        QCoreApplication.exit(0)


if __name__ == '__main__':
    input_list = sys.argv
    app = QApplication(sys.argv)
    widget = MyWidget(app)

    time.sleep(0.1)

    if not os.path.isfile(SRC_MODEL):
        QMessageBox.critical(
            widget, 'Error', "The model file does not exist. The path is 'model/isnetis.ckpt or isnetis.onnx'.")
        QTimer.singleShot(100, widget.quit_app)
    elif len(input_list) > 1:
        src_list = input_list[1:]
        widget.apply_abgr_to_files(src_list)

    sys.exit(app.exec_())
