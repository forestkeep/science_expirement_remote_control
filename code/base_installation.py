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

import logging
import sys
import threading
import time
from datetime import datetime

from pymodbus.client import ModbusSerialClient
from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from Adapter import Adapter, instrument
from Devices.Classes import (not_ready_style_background,
                             not_ready_style_border, ready_style_border)
from graph.online_graph import GraphWindow
from interface.experiment_settings_window import (experimentSettings,
                                                  settigsDialog)
from interface.Message import messageDialog
from saving_data.Parse_data import process_and_export, type_save_file

from functions import get_active_ch_and_device

logger = logging.getLogger(__name__)

class baseInstallation:
    def __init__(self) -> None:
        self.way_to_save_installation_file = None
        self.save_results_now = False
        self.is_search_resources = True

        self.is_window_save_dialog_showing = False
        self.is_debug = False
        self.down_brightness = False
        self.bright = 50
        self.pause_flag = False
        self.is_experiment_endless = False
        self.pbar_percent = 0
        self.way_to_save_file = False
        self.type_file_for_result = type_save_file.excel

        self.dict_active_device_class = {}
        self.clients = []
        self.key_to_start_installation = False

        self.repeat_experiment = 1
        self.repeat_meas = 1

        self.list_resources = []
        self.thread_scan_resources = threading.Thread(target=self._search_resources)
        self.thread_scan_resources.daemon = True
        self.stop_scan_thread = False

        self.gen_set_class = experimentSettings()
        self.thread_scan_resources.start()

    def show_information_window(self, message):
        msg = QtWidgets.QMessageBox()
        msg.setWindowTitle("Info")
        msg.setText(message)
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.exec_()

    def show_warning_window(self, message):
        msg = QtWidgets.QMessageBox()
        msg.setWindowTitle("Warning")
        msg.setText(message)
        msg.setIcon(QtWidgets.QMessageBox.Warning)
        msg.exec_()

    def show_critical_window(self, message):
        msg = QtWidgets.QMessageBox()
        msg.setWindowTitle("Error")
        msg.setText(message)
        msg.setIcon(QtWidgets.QMessageBox.Critical)
        msg.exec_()

    def get_channel_widget(self, name_device, num_channel):
        return self.installation_window.devices_lay[name_device].channels[num_channel]

    def get_device_widget(self, name_device):
        return self.installation_window.devices_lay[name_device]

    def clear_log(self):
        self.installation_window.log.clear()

    def get_signal_list(self, name_device, ch) -> tuple:
        buf_list = []
        for dev in self.dict_active_device_class.values():
            for chan in dev.channels:
                if chan.is_ch_active():
                    if dev.name != name_device:
                        buf_list.append(dev.name + " " + chan.get_name())
                    elif chan.get_name() != ch.get_name():
                        buf_list.append(dev.name + " " + chan.get_name())
        return buf_list

    def name_to_class(self, name_device):
        """возвращает экземпляр класса прибора"""
        for dev in self.dict_active_device_class.keys():
            if name_device == dev:
                return self.dict_active_device_class[dev]
        return False

    def set_priorities(self):
        """устанавливает приоритеты в эксперименте всем активным каналам во всех приборах"""
        priority = 1
        for dev, ch in get_active_ch_and_device( self.dict_active_device_class ):
            ch.set_priority(priority=priority)
            priority += 1

    def add_text_to_log(self, text: str, status: str = None):
        logger.info(f"add_text_to_log {text=} {status=}")
        if status == "err":
            self.installation_window.log.setTextColor(QtGui.QColor("red"))
        elif status == "war":
            self.installation_window.log.setTextColor(QtGui.QColor("orange"))
        elif status == "ok":
            self.installation_window.log.setTextColor(QtGui.QColor("green"))
        else:
            self.installation_window.log.setTextColor(QtGui.QColor("white"))


        self.installation_window.log.append(
            (str(datetime.now().strftime("%H:%M:%S")) + " : " + str(text))
        )
        self.installation_window.log.ensureCursorVisible()

        #cur_text = self.installation_window.log.toPlainText().split("\n")

    def set_state_text(self, text):
        logger.info(f"set_state_text {text}")
        self.installation_window.label_state.setText(text)

    def show_window_installation(self):
        logger.debug(f"вызвана функция показать окно установки")
        self.installation_window.show()

    def close_window_installation(self):
        try:
            self.installation_window.close()
            self.installation_window.setParent(None)
            logger.debug("окно установки закрыто")
        except Exception as e:
            logger.warning(f"ошибка: {str(e)}")

    def _search_resources(self):
        while  not self.stop_scan_thread:
            if self.is_search_resources and not self.is_experiment_running():
                self.list_resources = instrument.get_resourses()
                self.list_visa_resources = instrument.get_visa_resourses()
                time.sleep(0.1)

    def get_list_resources(self) -> list:
        return self.list_resources
    
    def get_list_visa_resources(self) -> list:
        return self.list_visa_resources

    def set_way_save(self):
        self.is_window_save_dialog_showing = True

        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        fileName, ans = QtWidgets.QFileDialog.getSaveFileName(
            self.installation_window,
            QApplication.translate('base_install',"укажите путь сохранения результатов"),
            "",
            "Книга Excel (*.xlsx);; Text Files(*.txt)",
            #"Text Files(*.txt);; Книга Excel (*.xlsx);;Origin (*.opju)",
            options=options,
        )
        if fileName:
            if ans == "Origin (*.opju)":
                if fileName.find(".opju") == -1:
                    fileName = fileName + ".opju"
                self.type_file_for_result = type_save_file.origin

            elif ans == "Книга Excel (*.xlsx)":
                if fileName.find(".xlsx") == -1:
                    fileName = fileName + ".xlsx"
                self.type_file_for_result = type_save_file.excel

            else:
                if fileName.find(".txt") == -1:
                    fileName = fileName + ".txt"
                self.type_file_for_result = type_save_file.txt

            self.way_to_save_file = fileName

            if self.save_results_now == True:
                self.save_results_now = False

                session_name, session_description = self.meas_session.session_name, self.meas_session.session_description
                print(f"{session_name=} {session_description=}")

                process_and_export(
                    self.buf_file,
                    self.way_to_save_file,
                    self.type_file_for_result,
                    session_name,
                    session_description,
                    self.is_delete_buf_file,
                    self.answer_save_results
                )
        else:
            self.type_file_for_result = False
        self.is_window_save_dialog_showing = False

    def answer_save_results(self, status, output_file_path, message = None, deleted_buf_file = False):

        message_status = "ok"
        text = ""
        if status == True:
            if deleted_buf_file:
                try:
                    text=QApplication.translate('base_install',"Результаты сохранены в {way}, файл {file} был удален")
                    text = text.format(way = output_file_path, file = deleted_buf_file)
                except:
                    text=QApplication.translate('base_install',"Результаты сохранены в {way}")
                    text = text.format(way = output_file_path)
            else:
                text = QApplication.translate('base_install',"Результаты сохранены в {way}")
                text = text.format(way = output_file_path)
        else:
            text = QApplication.translate('base_install',"Не удалось сохранить результаты в {way}")
            if message is not None:
                text+="\n" + str(message)
            text = text.format(way = output_file_path)
            message_status = "err"

        self.add_text_to_log(
                text=text,
                status=message_status
        )

    def save_results(self) -> bool:

        session_name, session_description = self.meas_session.session_name, self.meas_session.session_description
        print(f"{session_name=} {session_description=}")

        if (
            self.way_to_save_file != False
            and self.way_to_save_file != None
            and self.way_to_save_file != ''
        ):  # если выбран путь для сохранения результатов

            if self.type_file_for_result == type_save_file.origin:
                pass
            elif self.type_file_for_result == type_save_file.excel:
                pass
            elif self.type_file_for_result == type_save_file.txt:
                pass
            else:
                self.type_file_for_result = type_save_file.excel

            process_and_export(
                self.buf_file,
                self.way_to_save_file,
                self.type_file_for_result,
                session_name,
                session_description,
                self.is_delete_buf_file,
                self.answer_save_results
            )
            return True
        else:
            return False


    def show_about_autors(self):
        text = QApplication.translate('base_install',"""
        Авторы:

        Разработка:
        - Захидов Дмитрий
                                      
        Тестирование:        
        - Тимофеев Сергей
        - Астахов Василий
        - Морченко Александр

        Если у вас есть вопросы, замечания, или предложения по улучшению приложения, 
        пожалуйста, свяжитесь с нами по почте zakhidov.dim@yandex.ru

        Благодарим вас за использование приложения!
        """)
        dialog = messageDialog(text=text, title=QApplication.translate('base_install',"Информация об авторах") )
        dialog.exec_()

    def show_version(self):
        text = QApplication.translate('base_install',"Текущая версия - {version}")
        text = text.format(version = self.version_app)
        dialog = messageDialog(text=text, title=QApplication.translate('base_install',"Версия приложения"))
        dialog.exec_()

    def show_basic_instruction(self):
        if (
            self.is_show_basic_instruction_again == "true"
            or self.is_show_basic_instruction_again == True
        ):
            text = QApplication.translate('base_install',"""
                Настройте каждый прибор, нажав кнопку "Настроить" под его каналом. 
                Открывайте (кнопка +) и закрывайте каналы, а также добавляйте и удаляйте приборы по необходимости.

                После настройки всех приборов система проверяет конфликты интерфейсов. 
                Если конфликты обнаружены, вы получите сообщение желтым цветом в 
                логе под полем приборов. Чтобы устранить конфликты, заново внесите
                настройки интерфейсов в указанные приборы. Система также проверяет,
                имеет ли эксперимент окончание или будет продолжаться бесконечно,
                и выдаст соответствующее сообщение. После успешного завершения 
                всех проверок кнопка "Старт" подсветится зеленым цветом.

                Установите количество измерений в каждой точке и количество повторов 
                эксперимента в поле справа от приборов. Количество измерений больше 1 
                поможет усреднить результаты, а количество повторов больше 1 позволит 
                проверить их повторяемость.

                Контроллер установки покажет текущий прогресс в процентах и оставшееся 
                время работы. В логе будут отображаться информационные сообщения о 
                текущих действиях и их результатах. По завершении эксперимента 
                программа предложит выбрать файл для сохранения результатов, 
                если вы не сделали этого заранее.

                В ходе эксперимента или после его завершения вы можете нажать кнопку 
                "Показать график". График отображает зависимость измеряемого параметра
                от времени или других параметров. Вы можете масштабировать графики,
                менять цвета и фон, сохранять их в виде картинок и производить 
                несложную цифровую обработку.

                Для подробной инструкции по использованию приложения нажмите кнопку "Инфо" -> "Инструкция".
            """)

            dialog = messageDialog(
                text=text, title=QApplication.translate('base_install',"Инструкция по настройке"), are_show_again=True
            )

            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                self.is_show_basic_instruction_again = (
                    not dialog.check_not_show.isChecked()
                )
                self.settings.setValue(
                    "is_show_basic_instruction_again",
                    self.is_show_basic_instruction_again,
                )

    def open_graph_in_exp(self):
        if self.graph_window is not None:
            pass
        else:
            self.graph_window = GraphWindow(experiment_controller = self)
            self.graph_window.graph_win_close_signal.connect(self.graph_win_closed)
            self.graph_window.update_graphics(self.measurement_parameters)
        self.graph_window.show()

    def add_new_device(self):
        logger.debug("нажата кнопка добавления нового прибора")
        device_list, json_device_dict = self.device_selector.get_multiple_devices()
        self.message_from_new_installation(device_list, json_device_dict)



        #self.new_window = installation_Ui_Dialog()
        #self.new_window.setupUi(self, dict_device_class)
        #self.new_window.signal_to_main_window.connect(self.message_from_new_installation)
        #self.key_to_new_window_installation = True
        #self.new_window.show()

    def message_from_new_installation(self, device_list, json_device_list):

        new_added_device = {}
        if device_list or json_device_list:
            number_device = len(self.dict_active_device_class.keys()) + 1
            for key in device_list:
                try:
                    key_dev = key + "_" + str(number_device)
                    dev = self.dict_device_class[key](
                            name=key_dev, installation_class=self
                        )
                    self.dict_active_device_class[key_dev] = (dev)
                    new_added_device[key_dev] = (dev)

                    number_device = number_device + 1
                except:
                    logger.debug("под прибор |" + key + "| не удалось создать экземпляр")

            for key in json_device_list.values():
                try:
                    key_dev = key.name + "_" + str(number_device)
                    dev = self.JSON_dict_device_class[ key.json_data['device_type'] ](
                        name=key_dev, installation_class=self
                        )
                    dev.load_json(key.json_data)
                    self.dict_active_device_class[key_dev] = (dev)
                    new_added_device[key_dev] = (dev)

                    number_device = number_device + 1
                except KeyError:
                    logger.debug(f"Извините, под тип {key.json_data['device_type']} пока не разработан шаблон класса")

                except Exception as e:
                    logger.error(f"Failed to create instance of {key.name} {e}")

            self.installation_window.add_new_devices(new_added_device)

    def change_check_debug(self):
        if not self.is_experiment_running():
            if not self.is_debug:
                self.is_debug = True
                self.installation_window.develop_mode.setText(QApplication.translate('base_install',"Выкл режим разработчика"))
                self.add_text_to_log(
                    QApplication.translate('base_install',"Режим разработчика включен. В этом режиме корректность показаний с приборов не гарантируется"),
                    status="war",
                )
            else:
                self.installation_window.develop_mode.setText(QApplication.translate('base_install',"Вкл режим разработчика"))
                self.add_text_to_log(QApplication.translate('base_install',"Режим разработчика выключен"))
                self.is_debug = False

            for dev in self.dict_active_device_class.values():
                dev.set_debug(self.is_debug)

        self.preparation_experiment()

    def format_bool_settings(self, value):

        if isinstance(value, str ):
            if value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
            else:
                value = True
        return value

    def open_general_settings(self):

        (is_change,
        self.is_exp_run_anywhere,
        self.is_delete_buf_file,
        self.should_prompt_for_session_name,
        self.way_to_save_file,
        self.type_file_for_result,
        self.repeat_experiment,
        self.repeat_meas) = self.gen_set_class.read_settings(
                                                            self.is_exp_run_anywhere,
                                                            self.is_delete_buf_file,
                                                            self.should_prompt_for_session_name,
                                                            self.way_to_save_file,
                                                            self.type_file_for_result,
                                                            self.repeat_experiment,
                                                            self.repeat_meas
                                                           )

        if is_change:
            self.settings.setValue("is_exp_run_anywhere", self.is_exp_run_anywhere)
            self.settings.setValue("is_delete_buf_file", self.is_delete_buf_file)
            self.settings.setValue("should_prompt_for_session_name", self.should_prompt_for_session_name)


    ########### devices class connect func #############

    def confirm_devices_parameters(self):
        """подтверждаем параметры приборам и передаем им настроенные и созданные клиенты для подключения"""
        for device in self.dict_active_device_class.values():
            device.confirm_parameters()

    def set_clients_for_device(self):
        for device, client in zip(self.dict_active_device_class.values(), self.clients):
            if client:
                device.set_client(client)
            else:
                logger.warning(f"Для прибора {device.name} не создан клиент {client=}")

    def message_from_device_status_connect(self, answer, name_device):
        if answer == True:
            self.add_text_to_log(name_device + " - " + QApplication.translate('base_install',"соединение установлено"))
        else:
            self.add_text_to_log(
                name_device + " - " + QApplication.translate('base_install',"соединение не установлено, проверьте подлючение"),
                status="err",
            )
            self.set_border_color_device(
                device_name=name_device, status_color=not_ready_style_border
            )
            self.installation_window.start_button.setStyleSheet(
                not_ready_style_background
            )
            self.installation_window.start_button.setText(QApplication.translate('base_install',"Старт"))
            self.key_to_start_installation = False  # старт экспериепнта запрещаем

    def write_data_to_buf_file(self, message: str, addTime: bool=False):
        logger.info(f"write_data_to_buf_file {message}")
        message = f"{datetime.now().strftime('%H:%M:%S') + ' ' if addTime else ''}{message.replace('.', ',')}"
        with open(self.buf_file, "a") as file:
            file.write( str(message) )

    def message_from_device_settings(
        self,
        name_device,
        num_channel,
        status_parameters,
        list_parameters_device,
        list_parameters_act=None,
        list_parameters_meas=None,
    ):
        logger.debug(
            f"Настройки канала {num_channel}  прибора "
            + str(name_device)
            + " переданы классу установка, статус - "
            + str(status_parameters)
        )

        if status_parameters == True:
            self.set_border_color_device(
                device_name=name_device,
                status_color=ready_style_border,
                num_ch=num_channel,
            )
            self.show_parameters_of_device_on_label(
                name_device,
                num_channel,
                list_parameters_device,
                list_parameters_act,
                list_parameters_meas,
            )

            # ---------------этот блок необходим лля того, чтобы обновлять параметры устройства на лейбле всех каналов----------------
            device = self.name_to_class(name_device=name_device)
            for ch in device.channels:
                if ch.is_active == True:
                    if (
                        self.get_channel_widget(
                            device.get_name(), ch.get_number()
                        ).label_settings_channel.text
                        != QApplication.translate('base_install',"Не настроено")
                    ):
                        act_param, meas_param, dev_param = device.get_label_parameters(
                            ch.get_number()
                        )
                        self.show_parameters_of_device_on_label(
                            device.get_name(),
                            ch.get_number(),
                            dev_param,
                            act_param,
                            meas_param,
                        )
            # -----------------------------------------------------------------------------------------------------------------

        else:
            self.set_border_color_device(
                device_name=name_device,
                status_color=not_ready_style_border,
                num_ch=num_channel,
            )
            self.get_channel_widget(
                name_device, num_channel
            ).label_settings_channel.setText(QApplication.translate('base_install',"Не настроено"))

        self.dict_active_device_class[name_device].set_status_settings_ch(
            num_channel, status_parameters
        )

        self.preparation_experiment()
        logger.info("передали настройки прибора установке")

    ##############################################
    def create_clients(self) -> list:
        self.is_search_resources = False
        """функция создает клиенты для приборов с учетом того, что несколько приборов могут быть подключены к одному порту. Возвращает список ресурсов, которые не удалось создать"""
        logger.info("создаем клиенты для приборов")
        list_type_connection = []
        list_COMs = []
        list_baud = []
        dict_modbus_clients = {}
        dict_serial_clients = {}
        bad_resources = []
        for client in self.clients:
            try:
                client.close()
                del client
            except:
                pass
        self.clients.clear()
        for device in self.dict_active_device_class.values():
            is_dev_active = False
            for ch in device.channels:
                if ch.is_ch_active():
                    is_dev_active = True
                    break
            if is_dev_active:
                list_type_connection.append(device.get_type_connection())
                list_COMs.append(device.get_COM())
                list_baud.append(device.get_baud())
            else:

                list_type_connection.append(False)
                list_COMs.append(False)
                list_baud.append(False)
        for i in range(len(list_baud)):

            if list_type_connection[i] == False:
                self.clients.append(False)

            elif list_type_connection[i] != "modbus":
                if list_COMs[i] in dict_serial_clients.keys():
                    self.clients.append(dict_serial_clients[list_COMs[i]])
                else:
                    try:
                        ser = Adapter(list_COMs[i], int(list_baud[i]))
                    except Exception as e:
                        logger.warning(f"Error create {list_COMs[i]} client: {str(e)}")
                        bad_resources.append(list_COMs[i])
                        ser = False

                    dict_serial_clients[list_COMs[i]] = ser
                    self.clients.append(ser)

            elif list_type_connection[i] == "modbus":
                if list_COMs[i] in dict_modbus_clients.keys():
                    # если клиент был создан ранее, то просто добавляем ссылку на него
                    self.clients.append(dict_modbus_clients[list_COMs[i]])
                else:  # иначе создаем новый клиент и добавляем в список клиентов и список модбас клиентов

                    try:
                        dict_modbus_clients[list_COMs[i]] = ModbusSerialClient(
                                port=list_COMs[i],
                                baudrate=int(list_baud[i]),
                                stopbits=1,
                                bytesize=8,
                                parity="E",
                                timeout=0.3,
                                retries=1,
                        )
                    except Exception as e:
                        bad_resources.append(list_COMs[i])
                        dict_modbus_clients[list_COMs[i]] = False
                        logger.warning(f"Error create {list_COMs[i]} modbus client: {str(e)}")

                    self.clients.append(dict_modbus_clients[list_COMs[i]])
        self.is_search_resources = True
        return bad_resources

if __name__ == "__main__":
    import sys
    print(sys.path)