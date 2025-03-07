# Copyright © 2023 Zakhidov Dmitry <zakhidov.dim@yandex.ru>
# 
# This file may be used under the terms of the GNU General Public License
# version 3.0 as published by the Free Software Foundation and appearing in
# the file LICENSE included in the packaging of this file. Please review the
# following information to ensure the GNU General Public License version 3.0
# requirements will be met: https://www.gnu.org/copyleft/gpl.html.
# 
# This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
# WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.

import json
import re
import sys

from PyQt5 import QtCore
from PyQt5.QtWidgets import (QApplication, QDialog, QHBoxLayout, QInputDialog,
                             QLabel, QLineEdit, QMessageBox, QPushButton,
                             QVBoxLayout)
import sys
from PyQt5.QtWidgets import (
    QApplication, QDialog, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QPushButton, QHBoxLayout, QMessageBox, QHeaderView
)
from PyQt5.QtGui import QColor

try:
    from dev_template import templates
    from test_commands import TestCommands
except:
    from device_creator.dev_template import templates
    from device_creator.test_commands import TestCommands

TYPE_DEVICES = ['power_supply']
class InvalidTemplate(Exception):
    pass

class deviceCreator(QDialog):
    cancel_click = QtCore.pyqtSignal()
    def __init__(self):
        super().__init__()
        self.initial_setup()

    def initial_setup(self):
        self.check_command_line = None
        self.focus_answer_line = None
        self.new_commands = {}
        self.is_first_test = True
        self.device_name = None
        self.device_type = None
        self.number_of_channels = None
        self.result_parameters = None
        self.commands = []
        self.current_index = 0
        self.initUI() 

    def initUI(self):
        self.setWindowTitle('Конструктор')
        self.setMinimumWidth(500)

        welcome_message = QApplication.translate('device_creator',"""Добро пожаловать в Конструктор нового прибора!
                        Здесь вы сможете добавить новый прибор для использования 
                        в автоматическом контроллере физического эксперимента. 
                        Вам будет предложено ввести информацию о приборе, выбрать тип подключения, 
                        указать количество каналов и задать команды управления. 
                        Пожалуйста, следуйте инструкциям на экране для завершения процесса. 
                        Если Вы хотите прервать процесс, просто нажмите кнопку отмена или закройте окно.
                        Обратите внимание, что устройство должно поддерживать SCPI формат команд,
                          в ином случае добавить его не получится.""" )
        self.main_label = QLabel(welcome_message, self)
        
        self.test_commands_window = None
        self.test_button = QPushButton(QApplication.translate('device_creator',"Протестировать команду"))
        self.test_button.clicked.connect(self.test_function)
        self.input_field = QLineEdit()
        self.input_field.adjustSize()
        self.input_field.returnPressed.connect(self.submit_command)  # Обработка нажатия Enter

        self.main_layout = QVBoxLayout()
        self.main_layout.addWidget(self.main_label)

        self.twice_lay = QHBoxLayout()
        self.twice_lay.addWidget(self.input_field)
        self.twice_lay.addWidget(self.test_button)

        self.setLayout(self.main_layout)

        self.add_ok_cancel_buttons()
        self.ok_button.clicked.connect(self.get_type_device)
        self.cancel_button.clicked.connect(self.on_cancel_clicked)

    def first_ok_clicked(self):
        self.hide()
        self.device_name = self.get_device_name()
        if self.device_name == False:
            self.close()
            QApplication.quit()

        self.number_of_channels = self.get_number_of_channels()

        if not self.number_of_channels:
            self.close()
            QApplication.quit()

        data = templates[self.device_type]
        type_data = {"float": float, "int": int, "str": str, "bool": bool, "<class 'float'>": float, "<class 'int'>": int, "<class 'str'>": str, "<class 'bool'>": bool}
        if data.get("channels parameters", None):
            self.buf = data["channels parameters"]
            self.parameters = {}
            self.result_parameters = {}
            for key, value in self.buf.items():
                self.result_parameters[key] = []
                try:
                    self.parameters[key] = value[1](value[0])
                    self.result_parameters[key].append(str(value[1]))
                except Exception as e:
                    self.parameters[key] = type_data[value[1]](value[0])
                    self.result_parameters[key].append(str(type_data[value[1]]))

            self.get_channels_parameters()
        else:
            print("no channels parameters")
            self.start_questions()

    def get_channels_parameters(self):
        print("get_channels_parameters")
        self.ok_button.setParent(None)
        self.cancel_button.setParent(None)

        self.correct_color = QColor(40, 150, 0, 40)
        self.default_values = list(self.parameters.values())

        row = len(self.parameters)
        col = self.number_of_channels
        self.table = QTableWidget(int(row), int(col) )
        self.table.setHorizontalHeaderItem(0, QTableWidgetItem('Параметры'))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.table.setSelectionMode(QTableWidget.NoSelection)

        for i in range(int(self.number_of_channels)):
            self.table.setHorizontalHeaderItem(i, QTableWidgetItem(f'Канал {i + 1}'))

        for row, (param, default_value) in enumerate(self.parameters.items()):
            self.table.setVerticalHeaderItem(row, QTableWidgetItem(f'{param}'))
            for col in range(0, int(self.number_of_channels)):
                self.table.setItem(row, col, QTableWidgetItem(str(default_value)))
                item = self.table.item(row, col)
                item.setBackground(self.correct_color)

        self.table.cellChanged.connect(self.check_value)
        self.table.cellClicked.connect(self.choise_cell)
        self.first_lay = QVBoxLayout()
        self.first_lay.addWidget(self.table)
        self.main_layout.addLayout(self.first_lay)

        self.add_ok_cancel_buttons()
        self.ok_button.setText("Ок")
        self.ok_button.clicked.connect(self.on_ok)
        self.cancel_button.clicked.connect(self.on_cancel_clicked)
        self.show()

    def on_ok(self):
        for row in range(len(self.parameters)):
            for column in range(1, int(self.number_of_channels) + 1):  # Проверяем только столбцы с данными
                item = self.table.item(row, column)
                if item is not None and item.background() != self.correct_color:
                    QMessageBox.warning(self, 'Ошибка', 'Пожалуйста, проверьте корректность введенных данных.')
                    return

        for row, key in enumerate(self.result_parameters.keys()):
            row_results = []
            for column in range(self.number_of_channels):
                item = self.table.item(row, column)
                if item is not None:
                    row_results.append(item.text())
            for res in row_results:
                self.result_parameters[key].append(res)

        self.first_lay.removeWidget(self.table)
        self.table.setParent(None)
        self.first_lay.setParent(None)
        self.start_questions()

    def choise_cell(self, row, column):
        self.table.editItem(self.table.item(row, column))

    def check_value(self, row, column):
        item = self.table.item(row, column)
        value = item.text()
        default_value = self.default_values[row]
        focus_type = type(default_value)
        if focus_type == int:
            focus_type = float

        try:
            transformed_value = focus_type(value)
            item.setBackground(self.correct_color)
        except ValueError:
            item.setBackground(QColor("red"))

    def start_questions(self):
        #перестроить основное поле
        self.ok_button.setParent(None)
        self.cancel_button.setParent(None)
     
        self.main_layout.addLayout(self.twice_lay)
        self.add_ok_cancel_buttons()
        self.ok_button.setText("Ок")
        self.ok_button.clicked.connect(self.submit_command)
        self.cancel_button.clicked.connect(self.on_cancel_clicked)

        self.show()
        self.current_index = 0

        # считывать команды и задавать вопросы
        if self.commands :
            self.load_next_command()
        else:
            QMessageBox.critical(self, QApplication.translate('device_creator',"Ошибка"), QApplication.translate('device_creator',"Нет доступных команд для ввода."))
            self.close()

    def load_next_command(self):
        if self.current_index < len(self.commands):
            command_template = self.commands[self.current_index]
            example_input = command_template['command']
            self.actual_arguments = self.extract_arguments(example_input)
            self.is_add_lines = False
            for key in command_template.keys():
                if key == 'check_command':
                    self.is_add_lines = True

            if self.is_add_lines:
                if self.check_command_line != None and self.focus_answer_line != None:
                    self.check_command_line.setText(command_template['check_command'])
                    self.focus_answer_line.setText(command_template['focus_answer'])
                else:
                    self.ok_button.setParent(None)
                    self.cancel_button.setParent(None)
                    
                    self.main_layout.addLayout(self.create_check_command_line(command_template))
                    self.main_layout.addLayout(self.create_focus_answer_line(command_template))
                
                    self.add_ok_cancel_buttons()
                    self.ok_button.setText("Ок")
                    self.ok_button.clicked.connect(self.submit_command)
                    self.cancel_button.clicked.connect(self.on_cancel_clicked)
            else:
                if self.check_command_line != None and self.focus_answer_line != None:
                    self.check_command_line.setParent(None)
                    self.focus_answer_line.setParent(None)
                    self.check_command_label.setParent(None)
                    self.focus_answer_label.setParent(None)
                    self.check_command_line = None
                    self.focus_answer_line = None
            text = QApplication.translate('device_creator', "Введите значение для команды:\n\r {command_template}.\n\r Аргументы в фигурных скобках обязательно должны\n\r присутствовать в команде под теми же названиями,\n\r их обязательно обрамлять фигурными скобками.")
            text = text.format(command_template=command_template['description'])
            self.main_label.setText( text )
            self.input_field.setText(example_input)  # Устанавливаем шаблон в поле ввода
            self.transfer_command_to_test(example_input) # передаем команду окну с тестом
        else:
            self.finalize_commands()

    def create_check_command_line(self, command_template):
        self.check_command_label = QLabel(QApplication.translate('device_creator',"Команда запроса настройки/значения:") )
        self.check_command_line = QLineEdit(command_template['check_command'])
        self.check_command_line.adjustSize()
        check_command_layout = QVBoxLayout()
        check_command_layout.addWidget(self.check_command_label)
        check_command_layout.addWidget(self.check_command_line)
        return check_command_layout

    def create_focus_answer_line(self, command_template):
        self.focus_answer_label = QLabel(QApplication.translate('device_creator',"Возвращаемое значение:"))
        self.focus_answer_line = QLineEdit(command_template['focus_answer'])
        self.focus_answer_line.adjustSize()
        focus_answer_layout = QVBoxLayout()
        focus_answer_layout.addWidget(self.focus_answer_label)
        focus_answer_layout.addWidget(self.focus_answer_line)
        return focus_answer_layout

    def extract_arguments(self, s):
        """
        Extracts arguments enclosed in curly braces from a given string.

        This function takes a string input and uses a regular expression to 
        find all substrings that are enclosed in single pairs of curly braces 
        `{}`. It captures the content inside the braces and returns it as a list 
        of strings. If no arguments are found, or if the braces are empty, the 
        function will return an empty list or a list containing an empty string 
        for empty braces.

        Parameters:
        s (str): The input string from which to extract arguments.

        Returns:
        list: A list of strings containing the extracted arguments.
        """
        matches = re.findall(r'\{([^{}]*)\}', s)
        return matches

    def ensure_line_endings(self, input_str, newline_char="\r\n"):
        cleaned_str = re.sub(r'\\n|\\r|\n|\r|\\n\\n|\\r\\r|\n\n|\r\r|\n\r|\r\n|\\n\r|\r\\n|\\n\\r|\\r\\n|\\n\\r|\\n\\n|\\r\\n$', '', input_str)
        return cleaned_str + newline_char

    def finalize_commands(self):
        if self.result_parameters:
            final_commands = {
                "device_type": self.device_type,
                "device_name": self.device_name,
                "number_channels":int(self.number_of_channels),
                "channels parameters": self.result_parameters,
                "commands": self.new_commands
            }
        else:
            final_commands = {
                "device_type": self.device_type,
                "device_name": self.device_name,
                "number_channels":int(self.number_of_channels),
                "commands": self.new_commands
            }

        file_name = self.device_name
        with open(f"{file_name}.json", 'w') as outfile:
            json.dump(final_commands, outfile, indent=4)

        text = QApplication.translate('device_creator', "Ваш прибор создан и записан в {file_name}. Расположите его в той же директории, где расположен файл запуска программы построения установки, и он будет доступен в списке выбора приборов. Успехов!")
        text = text.format(file_name=file_name)

        QMessageBox.information(self, QApplication.translate('device_creator',"Готово"), text)
        self.cancel_click.emit()
        self.close()

    def get_type_device(self):
        self.ok_button.setParent(None)
        self.cancel_button.setParent(None)
        self.main_label.setText(QApplication.translate('device_creator',"Выберите тип добавляемого прибора"))
        global TYPE_DEVICES
        self.buttons_type = []
        for tp in TYPE_DEVICES:
            button = QPushButton(tp, self)
            button.clicked.connect(lambda checked, num=tp: self.type_button_click(num))
            self.main_layout.addWidget(button)
            self.buttons_type.append(button)

        self.show()

    def type_button_click(self, types):
        self.device_type = types
        for button in self.buttons_type:#удаляем кнопки
            button.setParent(None)

        status = False

        try:
            data = templates[self.device_type]
            commands = data.get('commands', {})
            dev_type = data.get('device_type')
            if dev_type.upper() != self.device_type.upper():
                raise InvalidTemplate(f"Шаблон устройства{self.device_type} не валиден, проверьте имя")
            self.commands_name = list(commands.keys())
            self.commands = list(commands.values())
            status = True

        except KeyError:
            QMessageBox.critical(None, QApplication.translate('device_creator',"Ошибка"), QApplication.translate('device_creator',"Шаблон не найден."))
            self.close()
        except InvalidTemplate:
            QMessageBox.critical(None, QApplication.translate('device_creator',"Ошибка"), QApplication.translate('device_creator',"Шаблон найден, но не валиден."))
            self.close()

        if status:
            self.first_ok_clicked()

    def get_number_of_channels(self):
        status = False
        while status == False:
            num_ch, ok = QInputDialog.getText(self, QApplication.translate('device_creator',"Количество каналов"), QApplication.translate('device_creator',"Введите количество каналов в приборе:"))
            
            if ok == False:#нажали отмену
                return status

            if not num_ch.strip():
                QMessageBox.critical(self, QApplication.translate('device_creator',"Ошибка"), QApplication.translate('device_creator',"Количество каналов не должно быть пустым."))
            else:
                status = True

            if status:#число не число
                try:
                    num_ch = int(num_ch)
                except:
                    QMessageBox.critical(self, QApplication.translate('device_creator',"Ошибка"), QApplication.translate('device_creator',"Введите число"))
                    status = False

            if status:
                max_num_ch = 8
                if num_ch > max_num_ch:
                    QMessageBox.critical(self, QApplication.translate('device_creator',"Ошибка"), QApplication.translate('device_creator',"Слишком много каналов, число не больше") + f" {max_num_ch}")
                    status = False
                    
        return num_ch
    
    def add_ok_cancel_buttons(self):
        '''Создает кнопки окей и отмена и добавляет их в конец главного слоя'''

        self.ok_button = QPushButton(QApplication.translate('device_creator','Поехали!'), self)
        self.cancel_button = QPushButton(QApplication.translate('device_creator','Отмена'), self)
        buf_lay = QHBoxLayout()
        buf_lay.addWidget(self.cancel_button)
        buf_lay.addWidget(self.ok_button)
        self.main_layout.addLayout(buf_lay)
        
    def get_device_name(self):
        status = False
        while status == False:
            device_name, ok = QInputDialog.getText(self, QApplication.translate('device_creator',"Имя прибора"), QApplication.translate('device_creator',"Введите имя прибора латиницей:"))

            if ok == False:#нажали отмену
                return status
            
            if not device_name.strip():
                QMessageBox.critical(self, QApplication.translate('device_creator',"Ошибка"), QApplication.translate('device_creator',"Имя прибора не должно быть пустым."))
            else:
                status = True
        return device_name
    
    def on_cancel_clicked(self):
        self.cancel_click.emit()
        self.close()
        del self

    def test_function(self):

        current_size = self.size()
        width = current_size.width()
        height = current_size.height()
        main_window_pos = self.pos()
    
        self.test_commands_window = TestCommands()
        self.test_commands_window.move(main_window_pos.x() + width, main_window_pos.y())
        self.test_commands_window.show()
        self.transfer_command_to_test(command=self.input_field.text())

        if self.is_first_test:
            text = QApplication.translate('device_creator','''
            Введите настройки для подключения к прибору. 
            Затем введите команду, замените аргументы в {} на нужные значения и нажмите кнопку отправить. 
            Смотрите на реакцию прибора и на ответ. 
            Проверьте все команды и формат ответа, после введите их в соответствующие поля и перейдите к следующей команде.

            Пример тестирования команды ":WAV:STARt {point}\r\n":
            {point} - этот аргумент мы меняем на какое-нибудь допустимое для прибора значение, пусть будет 125.
            Тогда наша команда в поле отправки будет выглядеть так: 
            ":WAV:STARt 125\r\n"''')
            QMessageBox.information(self, QApplication.translate('device_creator',"Инструкция"), text)
            self.is_first_test = False

    def transfer_command_to_test(self, command):
        if self.test_commands_window is not None:
            self.test_commands_window.entry.setText(command)

    def submit_command(self):
        input_text = self.input_field.text().strip()
        current_arguments = self.extract_arguments(input_text)
        #print(f"{self.actual_arguments=} {current_arguments=}")
        if set( self.actual_arguments ) != set( current_arguments ):
            '''если набор аргументов не одинаковый, то необходимо вывести сообщение с ошибкой'''
            QMessageBox.critical(self, QApplication.translate('device_creator',"Ошибка"), QApplication.translate('device_creator',"Аргументы в фигурных скобках должны быть такими же как и в образце. Их количесто так же должно быть равно количеству аргументов в образце. Может быть вы забыли обрамить аргументы фигурными скобками. Аргументы:") + f" {self.actual_arguments}")
            return
        input_text = self.ensure_line_endings(input_text)
        command_template = self.commands[self.current_index]

        command_template['command'] = input_text
        if self.is_add_lines:
            input_check = self.check_command_line.text().strip()
            input_focus = self.focus_answer_line.text().strip()
            command_template['check_command'] = self.ensure_line_endings(input_check)
            command_template['focus_answer'] = self.ensure_line_endings(input_focus, "\n")

        self.new_commands[ self.commands_name[self.current_index] ] = command_template
      
        self.current_index += 1
        self.load_next_command()

    def closeEvent(self, event):
        if self.test_commands_window is not None:
            self.test_commands_window.close()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = deviceCreator()
    ex.show()
    sys.exit(app.exec_())