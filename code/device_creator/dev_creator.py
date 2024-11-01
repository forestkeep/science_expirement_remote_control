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
import os


from PyQt5.QtWidgets import (QApplication, QHBoxLayout, QInputDialog, QLabel,
                             QLineEdit, QMessageBox, QPushButton, QVBoxLayout,
                             QDialog)

from device_creator.dev_template import templates
from device_creator.test_commands import TestCommands


class InvalidTemplate(Exception):
    pass

class deviceCreator(QDialog):
    def __init__(self):
        super().__init__()
        self.check_command_line = None
        self.focus_answer_line = None
        self.new_commands = {}
        self.is_first_test = True
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Конструктор')
        self.setMinimumWidth(500)

        # Создание метки с сообщением
        welcome_message = """Добро пожаловать в Конструктор нового прибора!
                        Здесь вы сможете добавить новый прибор для использования 
                        в автоматическом контроллере физического эксперимента. 
                        Вам будет предложено ввести информацию о приборе, выбрать тип подключения, 
                        указать количество каналов и задать команды управления. 
                        Пожалуйста, следуйте инструкциям на экране для завершения процесса. 
                        Если Вы хотите прервать процесс, просто нажмите кнопку отмена или закройте окно.
                        Обратите внимание, что устройство должно поддерживать SCPI формат команд,
                          в ином случае добавить его не получится."""
        self.main_label = QLabel(welcome_message, self)
        #self.main_label.setAlignment(Qt.AlignCenter)
        
        self.test_commands_window = None

        #Виджеты для диалога 
        self.test_button = QPushButton("Протестировать команду")
        self.test_button.clicked.connect(self.test_function)
        self.input_field = QLineEdit()
        self.input_field.adjustSize()
        self.input_field.returnPressed.connect(self.submit_command)  # Обработка нажатия Enter

        # Организация компоновки
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
        
        self.start_questions()

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
        #определить необходимые поля
        self.current_index = 0

        # считывать команды и задавать вопросы
        if self.commands :
            self.load_next_command()
        else:
            QMessageBox.critical(self, "Ошибка", "Нет доступных команд для ввода.")
            self.close()

    def load_next_command(self):
        print("след команда")
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

            self.main_label.setText(f"Введите значение для команды:\n\r {command_template['description']}.\n\r Аргументы в фигурных скобках обязательно должны\n\r присутствовать в команде под теми же названиями,\n\r их обязательно обрамлять фигурными скобками.")
            self.input_field.setText(example_input)  # Устанавливаем шаблон в поле ввода
            self.transfer_command_to_test(example_input) # передаем команду окну с тестом
        else:
            self.finalize_commands()

    def create_check_command_line(self, command_template):
        self.check_command_label = QLabel("Команда запроса настройки/значения:")
        self.check_command_line = QLineEdit(command_template['check_command'])
        self.check_command_line.adjustSize()
        check_command_layout = QVBoxLayout()
        check_command_layout.addWidget(self.check_command_label)
        check_command_layout.addWidget(self.check_command_line)
        return check_command_layout

    def create_focus_answer_line(self, command_template):
        self.focus_answer_label = QLabel("Возвращаемое значение:")
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

        final_commands = {
            "device_type": self.device_type,
            "device_name": self.device_name,
            "number_channels":int(self.number_of_channels),
            "commands": self.new_commands
        }

        file_name = self.device_name
        with open(f"{file_name}.json", 'w') as outfile:
            json.dump(final_commands, outfile, indent=4)

        QMessageBox.information(self, "Готово", f"Ваш прибор создан и записан в {file_name}. Расположите его в той же директории, где расположен файл запуска программы построения установки, и он будет доступен в списке выбора приборов. Успехов!")
        self.close()

    def get_type_device(self):
        self.ok_button.setParent(None)
        self.cancel_button.setParent(None)
        self.main_label.setText("Выберите тип добавляемого прибора")
        type_devices = ['oscilloscope']
        self.buttons_type = []
        for tp in type_devices:
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
            QMessageBox.critical(None, "Ошибка", "Шаблон не найден.")
            self.close()
        except InvalidTemplate:
            QMessageBox.critical(None, "Ошибка", "Шаблон найден, но не валиден.")
            self.close()

        if status:
            self.first_ok_clicked()

    def get_number_of_channels(self):
        status = False
        while status == False:
            num_ch, ok = QInputDialog.getText(self, "Количество каналов", "Введите количество каналов в приборе:")
            
            if ok == False:#нажали отмену
                return status

            if not num_ch.strip():
                QMessageBox.critical(self, "Ошибка", "Количество каналов не должно быть пустым.")
            else:
                status = True

            if status:#число не число
                try:
                    num_ch = float(num_ch)
                except:
                    QMessageBox.critical(self, "Ошибка", "Введите число")
                    status = False

            if status:
                max_num_ch = 8
                if num_ch > max_num_ch:
                    QMessageBox.critical(self, "Ошибка", f"Слишком много каналов, число не больше {max_num_ch}")
                    status = False
                    
        return num_ch

    def add_ok_cancel_buttons(self):
        '''Создает кнопки окей и отмена и добавляет их в конец главного слоя'''
        self.ok_button = QPushButton('Поехали!', self)
        self.cancel_button = QPushButton('Отмена', self)
        buf_lay = QHBoxLayout()
        buf_lay.addWidget(self.cancel_button)
        buf_lay.addWidget(self.ok_button)
        self.main_layout.addLayout(buf_lay)

        
    def get_device_name(self):
        status = False
        while status == False:
            device_name, ok = QInputDialog.getText(self, "Имя прибора", "Введите имя прибора латиницей:")

            if ok == False:#нажали отмену
                return status
            
            if not device_name.strip():
                QMessageBox.critical(self, "Ошибка", "Имя прибора не должно быть пустым.")
            else:
                status = True
        return device_name

    def on_cancel_clicked(self):
        self.close()  # Закрыть окно после нажатия Отмена

    def test_function(self):

        current_size = self.size()  # Получаем размер главного окна
        width = current_size.width()  # Ширина
        height = current_size.height()  # Высота
        main_window_pos = self.pos()
    
        # Устанавливаем положение для нового окна
        self.test_commands_window = TestCommands()
        self.test_commands_window.move(main_window_pos.x() + width, main_window_pos.y())
        self.test_commands_window.show()
        self.transfer_command_to_test(command=self.input_field.text())

        if self.is_first_test:
            text = r'''
            Введите настройки для подключения к прибору. 
            Затем введите команду, замените аргументы в {} на нужные значения и нажмите кнопку отправить. 
            Смотрите на реакцию прибора и на ответ. 
            Проверьте все команды и формат ответа, после введите их в соответствующие поля и перейдите к следующей команде.

            Пример тестирования команды ":WAV:STARt {point}\r\n":
            {point} - этот аргумент мы меняем на какое-нибудь допустимое для прибора значение, пусть будет 125.
            Тогда наша команда в поле отправки будет выглядеть так: 
            ":WAV:STARt 125\r\n"'''
            QMessageBox.information(self, "Инструкция", text)
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
            QMessageBox.critical(self, "Ошибка", f"Аргументы в фигурных скобках должны быть такими же как и в образце. Их количесто так же должно быть равно количеству аргументов в образце. Может быть вы забыли обрамить аргументы фигурными скобками. Аргументы: {self.actual_arguments}")
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

        print(f"{command_template=}")

        
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