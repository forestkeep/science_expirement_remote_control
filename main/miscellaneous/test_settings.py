from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QCheckBox, QGridLayout, QLabel, QSpacerItem, \
    QSizePolicy
from PyQt5.QtCore import QSize, QCoreApplication, QSettings
 
 
ORGANIZATION_NAME = 'Example App'
ORGANIZATION_DOMAIN = 'example.com'
APPLICATION_NAME = 'QSettings program'
SETTINGS_TRAY = 'settings/tray'
 
 
class MainWindow(QMainWindow):
    """
        Объявление чекбокса.
        Инициализироваться будет в конструкторе.
    """
    check_box = None
 
    # Переопределяем конструктор класса
    def __init__(self):
        # Обязательно нужно вызвать метод супер класса
        QMainWindow.__init__(self)
        self.test_param = 152
 
        self.setMinimumSize(QSize(480, 240))  # Устанавливаем размеры
        self.setWindowTitle("Settings Application")  # Устанавливаем заголовок окна
        central_widget = QWidget(self)  # Создаём центральный виджет
        self.setCentralWidget(central_widget)  # Устанавливаем центральный виджет
 
        grid_layout = QGridLayout()  # Создаём QGridLayout
        central_widget.setLayout(grid_layout)  # Устанавливаем данное размещение в центральный виджет
        grid_layout.addWidget(QLabel("Application, which can minimize to Tray", self), 0, 0)
 
        # Добавляем чекбокс, состояние которого будет сохраняться в настройках
        self.check_box = QCheckBox('Settings CheckBox for minimizing to tray')
        grid_layout.addWidget(self.check_box, 1, 0)
        grid_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding), 2, 0)
 
        # Обращаемся к настройкам программы
        settings = QSettings()
        # Забираем состояние чекбокса, с указанием типа данных:
        # type=bool является заменой метода toBool() в PyQt5
        check_state = settings.value(SETTINGS_TRAY, False, type=bool)
        # Устанавливаем состояние
        self.check_box.setChecked(check_state)
        # подключаем слот к сигналу клика по чекбоксу, чтобы созранять его состояние в настройках
        self.check_box.clicked.connect(self.save_check_box_settings)
 
    # Слот для сохранения настроек чекбокса
    def save_check_box_settings(self):
        settings = QSettings()
        settings.setValue(SETTINGS_TRAY, self.check_box.isChecked())
        settings.sync()
class testings():
    def __init__(self) -> None:
        self.name = None
    def set_name(self, name):
        self.name = name
    def get_name(self):
        return self.name
 
if __name__ == "__main__":
    import sys
    import pickle

    def test():
        print("testing message")

    cls = testings()
    cls.set_name("alexrrrttrttrtrttrt")

    s = pickle.dumps(cls)
    deserialized_data = pickle.loads(s)

    print(deserialized_data.get_name())
 
    # Для того, чтобы каждый раз при вызове QSettings не вводить данные вашего приложения
    # по которым будут находиться настройки, можно
    # установить их глобально для всего приложения
    QCoreApplication.setApplicationName(ORGANIZATION_NAME)
    QCoreApplication.setOrganizationDomain(ORGANIZATION_DOMAIN)
    QCoreApplication.setApplicationName(APPLICATION_NAME)
 
    app = QApplication(sys.argv)
    mw = MainWindow()
    print(mw.__dict__)
    mw.show()
    sys.exit(app.exec())