from PySide6 import QtCore
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QFrame, QGraphicsDropShadowEffect

css = """
        QWidget{
            Background: rgba(70, 70, 70, 0.4);
            font:14px bold;
            font-weight:normal;
            height: 11px;
            border-top-left-radius: 5px;
            border-bottom-left-radius: 5px;
        }
        QPushButton{
            color: rgb(255, 255, 255);
            background-color: grey;
            border-radius: 5px;
        }
        QPushButton:hover{
            Background: rgba(60, 60, 60, .9);
            border-radius: 5px;
        }
        QPushButton:pressed{
            background-color: rgb(70, 70, 70);
            border-radius: 5px;
        }
        """

qss = """
        QPushButton{
            color: rgb(255, 255, 255);
            Background: rgba(100, 100, 100, .9);
            border-radius: 5px;
        }
        QPushButton:hover{
            background-color: grey;
            border-radius: 5px;
        }"""


class QSITitleBar(QWidget):
    def __init__(self, parent, title: str, only_close: bool):
        QWidget.__init__(self, parent)

        btn_size = 24
        # central_widget = QWidget()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.parent = parent
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        # self.setStyleSheet(qss)
        self.normal_win = True
        # self.setGeometry(0, 300, 0, 50)

        lay1 = QHBoxLayout()
        lay1.setSpacing(0)

        fr = QFrame(None)
        fr.setMaximumHeight(40)
        fr.setMinimumHeight(40)
        fr.setLayout(lay1)
        fr.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        fr.setStyleSheet("""
            background-color: rgb(30,30,30);""")
        self.layout.addWidget(fr)

        # creating a QGraphicsDropShadowEffect object
        shadow = QGraphicsDropShadowEffect()

        # setting blur radius
        shadow.setBlurRadius(15)
        shadow.setColor(Qt.black)
        fr.setGraphicsEffect(shadow)

        self.label_img1 = QLabel(self)
        self.label_img1.setPixmap(QPixmap('static/camera.png').scaled(16, 16))
        self.label_img1.setMargin(10)

        lay1.addWidget(self.label_img1)
        lay1.setAlignment(Qt.AlignVCenter)
        lay1.setContentsMargins(0, 0, 10, 0)
        lay1.setSpacing(0)
        self.label_img1.setParent(fr)

        if not title:
            self.title = QLabel("Admin Panel  |  Geo Location Monitoring")
        else:
            self.title = QLabel(title)
        # self.title.setAlignment(Qt.AlignTop)

        self.initial_pos = None
        lay1.addWidget(self.title)
        self.title.setParent(fr)

        if not only_close:
            self.btn_min = QPushButton()
            self.btn_min.clicked.connect(self.btn_min_clicked)
            self.btn_min.setFixedSize(btn_size, btn_size)
            self.btn_min.setIcon(QIcon('static/minimize-window-256.icns'))
            self.btn_min.setIconSize(QtCore.QSize(16, 16))
            self.btn_min.setFixedSize(QtCore.QSize(btn_size, btn_size))
            self.btn_min.setStyleSheet("""
                QPushButton:hover{
                    background-color: rgb(70,70,70);
                    border-radius: 5px;
                }""")
            lay1.addWidget(self.btn_min)
            self.btn_min.setParent(fr)

            self.btn_res = QPushButton()
            self.btn_res.clicked.connect(self.btn_restore_clicked)
            self.btn_res.setFixedSize(btn_size, btn_size)
            self.btn_res.setIcon(QIcon('static/maximize-window-256.icns'))
            self.btn_res.setIconSize(QtCore.QSize(16, 16))
            self.btn_res.setFixedSize(QtCore.QSize(btn_size, btn_size))
            self.btn_res.setStyleSheet("""
                QPushButton:hover{
                    background-color: rgb(70,70,70);
                    border-radius: 5px;
                }""")
            lay1.addWidget(self.btn_res)
            self.btn_res.setParent(fr)

        self.btn_close = QPushButton()
        self.btn_close.clicked.connect(self.btn_close_clicked)
        self.btn_close.setFixedSize(btn_size, btn_size)
        self.btn_close.setIcon(QIcon('static/power-256.icns'))
        self.btn_close.setIconSize(QtCore.QSize(16, 16))
        self.btn_close.setFixedSize(QtCore.QSize(btn_size, btn_size))
        self.btn_close.setContentsMargins(0, 0, 0, 0)
        self.btn_close.setStyleSheet("""
            QPushButton:hover{
                background-color: red;
                border-radius: 5px;
            }""")
        lay1.addWidget(self.btn_close)
        self.btn_close.setParent(fr)

        # self.title.setFixedHeight(50)
        self.title.setAlignment(Qt.AlignVCenter)
        self.setLayout(self.layout)

        self.start = QPoint(0, 0)
        self.pressing = False

    def resizeEvent(self, QResizeEvent):
        super(QSITitleBar, self).resizeEvent(QResizeEvent)
        self.title.setFixedWidth(self.parent.width())

    def mousePressEvent(self, event):
        self.start = self.mapToGlobal(event.pos())
        self.pressing = True

    def mouseMoveEvent(self, event):
        if self.pressing:
            end = self.mapToGlobal(event.pos())
            movement = end - self.start
            self.parent.move(self.parent.pos() + movement)
            self.start = end

    def mouseReleaseEvent(self, QMouseEvent):
        self.pressing = False

    def btn_close_clicked(self):
        self.parent.close()

    def btn_max_clicked(self):
        self.parent.showMaximized()

    def btn_min_clicked(self):
        self.parent.showMinimized()

    def btn_restore_clicked(self):
        if self.normal_win:
            self.parent.showMaximized()
        else:
            self.parent.showNormal()
        self.normal_win = not self.normal_win

if __name__ == '__main__':
    pass
