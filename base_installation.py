from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QTimer, Qt
import logging
from datetime import datetime
from Parse_data import process_and_export, type_save_file
from interface.experiment_settings_window import settigsDialog
from Classes import ch_response_to_step
from Classes import not_ready_style_border, not_ready_style_background, ready_style_border, ready_style_background, warning_style_border, warning_style_background
from interface.About_autors_window import AboutAutorsDialog
from online_graph import GraphWindow
from interface.installation_check_devices import installation_Ui_Dialog

logger = logging.getLogger(__name__)

class baseInstallation():
    def __init__(self) -> None:
        self.is_exp_run_anywhere = True
        self.is_delete_buf_file = False

        self.way_to_save_installation_file = None
        self.save_results_now = False

        self.is_window_save_dialog_showing = False
        self.is_debug = False
        self.down_brightness = False
        self.bright = 50
        self.pause_flag = False
        self.is_experiment_endless = False
        self.pbar_percent = 0
        self.way_to_save_file = False
        self.type_file_for_result = type_save_file.txt
        
        self.dict_active_device_class = {}
        self.clients = [] 
        self.key_to_start_installation = False
    
        self.repeat_experiment = 1
        self.repeat_meas = 1
        self.way_to_save_fail = None
        
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
        
    def get_signal_list(self, name_device, num_ch) -> tuple:
        buf_list = []
        for dev in self.dict_active_device_class.values():
            for ch in dev.channels:
                if dev.name != name_device or ch.number != num_ch:
                    if ch.is_ch_active():
                        buf_list.append([dev.name, ch.number])
        return buf_list
    
    def update_pbar(self) -> None:
        self.installation_window.pbar.setValue(int(self.pbar_percent))
        
    def name_to_class(self, name):
        '''возвращает экземпляр класса прибора'''
        for dev in self.dict_active_device_class.keys():
            if name == dev:
                return self.dict_active_device_class[dev]
        return False
    
    def set_priorities(self):
        '''устанавливает приоритеты в эксперименте всем активным каналам во всех приборах'''
        priority = 1
        for dev, ch in self.get_active_ch_and_device():
                    ch.set_priority(priority = priority)
                    priority += 1
                    
    def get_active_ch_and_device(self):
        for device in self.dict_active_device_class.values():
            for channel in device.channels:
                if channel.is_ch_active():
                    yield device, channel
                    
    def add_text_to_log(self, text, status=None):
        if status == "err":
            self.installation_window.log.setTextColor(QtGui.QColor('red'))
        elif status == "war":
            self.installation_window.log.setTextColor(QtGui.QColor('orange'))
        else:
            self.installation_window.log.setTextColor(QtGui.QColor('white'))

        self.installation_window.log.append(
            (str(datetime.now().strftime("%H:%M:%S")) + " : " + str(text)))
        self.installation_window.log.ensureCursorVisible()
        
    def pause_actions(self):
        '''функция срабатывает по таймеру во время паузы эксперимента'''

        step = 15
        if self.down_brightness:
            self.bright = self.bright - step
            if self.bright < 30:
                self.bright = 0
                self.down_brightness = False
        else:
            self.bright += step
            if self.bright > 255:
                self.bright = 255
                self.down_brightness = True

        style = "background-color: rgb(" + str(self.bright) + \
            "," + "255" + "," + str(self.bright) + ");"

        self.installation_window.pause_button.setStyleSheet(
            style)
        
    def set_state_text(self, text):
        self.installation_window.label_state.setText(text)
        
    def show_window_installation(self):
        logger.debug(f"вызвана функция показать окно установки")
        self.installation_window.show()
        
    def close_window_installation(self):
        try:
            self.installation_window.close()
            self.installation_window.setParent(None)
            logger.debug("окно установки закрыто")
        except:
            pass
        
    def set_way_save(self):
        self.is_window_save_dialog_showing = True
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        fileName, ans = QtWidgets.QFileDialog.getSaveFileName(self.installation_window,
                                                              "укажите путь сохранения результатов", "", "Text Files(*.txt);; Книга Excel (*.xlsx);;Origin (*.opju)", options=options)
        if fileName:
            if ans == "Origin (*.opju)":
                if fileName.find(".opju") == -1:
                    fileName = fileName + ".opju"
                self.type_file_for_result = type_save_file.origin
                pass
            elif ans == "Книга Excel (*.xlsx)":
                if fileName.find(".xlsx") == -1:
                    fileName = fileName + ".xlsx"
                self.type_file_for_result = type_save_file.excel
                pass
            else:
                if fileName.find(".txt") == -1:
                    fileName = fileName + ".txt"
                self.type_file_for_result = type_save_file.txt
                pass

            self.way_to_save_file = fileName
            self.installation_window.way_save_text.setText(str(fileName))
            if self.save_results_now == True:
                process_and_export(self.buf_file, self.way_to_save_file, self.type_file_for_result, self.is_delete_buf_file)
                self.save_results_now = False
        else:
            self.type_file_for_result = False
        self.is_window_save_dialog_showing = False
        
    def save_results(self):
        if self.way_to_save_file != False:  # если выбран путь для сохранения результатов

            if self.type_file_for_result == type_save_file.origin:
                pass
            elif self.type_file_for_result == type_save_file.excel:
                pass
            elif self.type_file_for_result == type_save_file.txt:
                pass
            else:
                self.type_file_for_result = type_save_file.txt

            process_and_export(self.buf_file, self.way_to_save_file, self.type_file_for_result, self.is_delete_buf_file)

        else:
            self.exp_th_connect.ask_save_the_results = True

            while self.exp_th_connect.ask_save_the_results == True:
                pass
            
    def show_about_autors(self):
        dialog = AboutAutorsDialog()
        dialog.exec_()
        
    def open_graph_in_exp(self):
        if self.graph_window is not None:
            pass
        else:
            self.graph_window = GraphWindow()
            self.graph_window.graph_win_close_signal.connect(self.graph_win_closed)
            self.graph_window.update_dict_param(self.measurement_parameters)
        self.graph_window.show()
        
    def add_new_device(self):
        logger.debug("нажата кнопка добавления нового прибора")
        self.new_window = QtWidgets.QDialog()
        self.ui_window = installation_Ui_Dialog()
        self.ui_window.setupUi(self.new_window, self)
        self.key_to_new_window_installation = True
        self.new_window.show()
        
    def change_check_debug(self):
        if not self.is_experiment_running():
            if not self.is_debug:
                self.is_debug = True
                self.installation_window.develop_mode.setText("Выкл режим разработчика")
                self.add_text_to_log("Режим разработчика включен. В этом режиме корректность показаний с приборов не гарантируется",status="war")
            else:
                self.installation_window.develop_mode.setText("Вкл режим разработчика")
                self.add_text_to_log("Режим разработчика выключен")
                self.is_debug = False
            
            for dev in self.dict_active_device_class.values():
                dev.set_debug(self.is_debug)

        self.preparation_experiment()
        
    def open_general_settings(self):
        set_dialog = settigsDialog()
        is_exp_run_anywhere = [Qt.Checked]
        set_dialog.check_boxes_1[0].setChecked(self.is_exp_run_anywhere == True)
        set_dialog.check_boxes_1[0].stateChanged.connect(lambda state: is_exp_run_anywhere.__setitem__(0, state == Qt.Checked))

        is_delete_buf_file = [Qt.Checked]
        set_dialog.check_boxes_1[1].setChecked(self.is_delete_buf_file == True)
        set_dialog.check_boxes_1[1].stateChanged.connect(lambda state: is_delete_buf_file.__setitem__(0, state == Qt.Checked))

        answer = set_dialog.exec_()
        if answer:
            if is_exp_run_anywhere[0]:
                self.is_exp_run_anywhere = True
            else:
                self.is_exp_run_anywhere = False

            if is_delete_buf_file[0]:
                self.is_delete_buf_file = True
            else:
                self.is_delete_buf_file = False
            #print("сохранить настройки", self.is_exp_run_anywhere)
        else:
            pass
            #print("не сохранять изменения")