from PyQt5 import QtWidgets, QtGui
import sys

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Пример сворачивания в трей")
        self.setGeometry(100, 100, 300, 200)

        # Создаем системный трей и устанавливаем иконку
        self.tray_icon = QtWidgets.QSystemTrayIcon(self)
        self.tray_icon.setIcon(QtGui.QIcon("tray.png"))  # Замените на путь к вашей иконке
        self.tray_icon.activated.connect(self.tray_icon_activated)

        # Отображаем трей
        self.tray_icon.show()

        # Сигнал для закрытия окна
        self.close_event = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Q"), self)
        self.close_event.activated.connect(self.close)

    def closeEvent(self, event):
        """Событие закрытия окна"""
        event.ignore()  # Игнорируем событие закрытия
        self.hide()     # Скрываем окно

    def tray_icon_activated(self, reason):
        """Сигнал при активации трей-иконки"""
        if reason == QtWidgets.QSystemTrayIcon.Trigger:
            self.show()  # Показываем окно при нажатии на трей-иконку
            self.activateWindow()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())