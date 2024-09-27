import sys
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
from PyQt5.QtGui import QPixmap
from io import BytesIO
from plantuml import PlantUML

def generate_plantuml_diagram(devices):
    uml_diagram = '@startuml\n'
    for device in devices:
        uml_diagram+= f'participant {device.name}\n'

    for device in devices:
        trigger_type = device.get_trigger(0)
        trigger_value = device.get_trigger_value(0)

        if trigger_type == "таймер":
            uml_diagram += f'{device.name} -> {trigger_value} \n'
        elif trigger_type == "внешний сигнал":
            uml_diagram += f'{device.name} -> {trigger_value}\n'

    uml_diagram += '@enduml'

    uml_diagram1 = """
        @startuml
        Прибор 1 -> Прибор 3
        @enduml
        """

    return uml_diagram

def get_plantuml_image(uml_diagram):
    # Укажите URL вашего сервера PlantUML или используйте локальный
    plantuml_url = "http://www.plantuml.com/plantuml/png/"
    plantuml = PlantUML(url=plantuml_url)

    # Получаем изображение в формате PNG
    print(uml_diagram)
    sequence_diagram = """
        @startuml
        class БП {
            +бп()
        }

        БП --> БП: 10 сек
        note left of БП: 20 Повторов
        @enduml
        """
    response = plantuml.processes(uml_diagram)
    return response

class UMLViewer(QWidget):
    def __init__(self, devices):
        super().__init__()
        self.initUI(devices)

    def initUI(self, devices):
        diagram = generate_plantuml_diagram(devices)
        image_data = get_plantuml_image(diagram)
        
        # Создаем QPixmap из байтового потока
        pixmap = QPixmap()
        pixmap.loadFromData(image_data)

        label = QLabel(self)
        label.setPixmap(pixmap)

        layout = QVBoxLayout()
        layout.addWidget(label)
        self.setLayout(layout)

        self.setWindowTitle('PlantUML Diagram')
        self.resize(800, 600)

class Device:
    def __init__(self, name, trigger_type, trigger_value):
        self.name = name
        self.trigger_type = trigger_type
        self.trigger_value = trigger_value

    def get_trigger(self, _):
        return self.trigger_type

    def get_trigger_value(self, _):
        return self.trigger_value

# Тестовый список приборов
devices = [
    Device("Прибор1", "внешний сигнал", "Прибор2"),
    Device("Прибор2", "внешний сигнал", "Прибор3"),
    Device("Прибор3", "внешний сигнал", "Прибор4"),
    Device("Прибор4", "внешний сигнал", "Прибор1"),
]

if __name__ == '__main__':
    app = QApplication(sys.argv)
    viewer = UMLViewer(devices)
    viewer.show()
    sys.exit(app.exec_())