from PyQt5.QtWidgets import QLabel, QPushButton
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QPoint

class MovableLabel(QLabel):
    """Label déplaçable au clic sur lequel l'utilisateur peut tirer la fenêtre."""
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setMinimumHeight(30)
        self.pos_offset = None

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            if self.parent.press_control == 0:
                self.pos_offset = e.pos()
                self.main_pos = self.parent.pos()
        super().mousePressEvent(e)
        
    def mouseMoveEvent(self, e):
        if self.parent.cursor().shape() == Qt.ArrowCursor and isinstance(self.pos_offset, QPoint):
            self.last_pos = e.pos() - self.pos_offset
            self.main_pos += self.last_pos
            self.parent.move(self.main_pos)
        super(MovableLabel, self).mouseMoveEvent(e)


class HoverButton(QPushButton):
    """Bouton qui change d'icône SVG lorsqu'il est survolé."""
    def __init__(self, icon_path, hover_icon_path, parent=None):
        super().__init__(parent)
        self.icon_path = icon_path
        self.hover_icon_path = hover_icon_path
        self.setIcon(QIcon(self.icon_path))

    def enterEvent(self, event):
        self.setIcon(QIcon(self.hover_icon_path))

    def leaveEvent(self, event):
        self.setIcon(QIcon(self.icon_path))
