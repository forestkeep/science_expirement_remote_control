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


import copy
import enum
import logging
import time

import numpy
from PyQt5.QtWidgets import QApplication

from Analyse_in_installation import analyse
from Devices.Classes import not_ready_style_background, ready_style_background
from shared_buffer_manager import _process_received_data
from functions import get_active_ch_and_device, write_data_to_buf_file, clear_queue, clear_pipe, create_clients, ExperimentState

logger = logging.getLogger(__name__)


class message_status(enum.Enum):
    info = 1
    warning = 2
    critical = 3


class ExperimentBridge(analyse):
    def __init__(self) -> None:
        super().__init__()
        self.pause_start_time  = 0
        
    def is_experiment_running(self) -> bool:
        answer = False
        if hasattr(self, "experiment_process"):
            answer = self.experiment_process is not None and self.experiment_process.is_alive()
        return answer
    
    def receive_data_exp(self):
        if self.is_experiment_running():
            if self.data_from_exp.poll():
                received = self.data_from_exp.recv()
                if isinstance(received, tuple) and len(received) == 2:
                    data = _process_received_data(self.data_from_exp, *received)
                    if data:
                        val = [data[0], data[1]]
                        status_update = self.graph_controller.decode_add_exp_parameters(session_id = self.current_session_graph_id, entry      = val,time       = data[2])
                        if not status_update:
                            logger.warning(f"Error updating parameters: {val}")
                    else:
                        logger.warning(f"Ошибка в расшифровке принятых данных")
                    
    def connection_two_thread(self):
        """функция для обновления интерфейса во время эксперимента"""
        if self.is_experiment_running():

            if not self.current_state == ExperimentState.PAUSED:
                if self.is_experiment_endless:
                    pbar_percent = 50
                    self.installation_window.label_time.setText(
                        QApplication.translate('exp_flow',"Бесконечный эксперимент")
                    )
                else:
                    if self.remaining_exp_time == 0:
                        self.remaining_exp_time = 1
                    pbar_percent = ( ((time.perf_counter() - self.start_exp_time) / self.remaining_exp_time) ) * 100

                    min = 0
                    sec = 0
                    if self.remaining_exp_time - (time.perf_counter() - self.start_exp_time) > 0:
                        min = int((self.remaining_exp_time - (time.perf_counter() - self.start_exp_time))/ 60)
                        sec = int((self.remaining_exp_time - (time.perf_counter() - self.start_exp_time))% 60)

                    self.installation_window.label_time.setText(
                        QApplication.translate('exp_flow',f"Осталось {min}:{sec} мин"))
                    
                self.update_pbar( pbar_percent )
            else:
                self.installation_window.label_time.setText(QApplication.translate('exp_flow',"Осталось -- мин"))

        else:
            self.timer_for_connection_main_exp_thread.stop()
            self.installation_window.pbar.setValue(0)
            #self.preparation_experiment()
            self.installation_window.label_time.setText("")

    def stoped_experiment(self):
        self.pipe_exp.send(["stop"])
        self.current_state = ExperimentState.FINALIZING
        self.set_state_text(text = QApplication.translate('exp_flow',"Остановка") + "...")

    def pause_exp(self):
        if self.is_experiment_running():
            if self.current_state == ExperimentState.PAUSED:
                self.current_state = ExperimentState.IN_PROGRESS
                self.pipe_exp.send(["pause", 0])
                self.installation_window.pause_button.setText(QApplication.translate('exp_flow',"Пауза"))
                self.timer_for_pause_exp.stop()

                self.start_exp_time += time.perf_counter() - self.pause_start_time
                for device, ch in get_active_ch_and_device( self.dict_active_device_class):
                    if ch.am_i_active_in_experiment:
                        if device.get_trigger(ch) == QApplication.translate('exp_flow', "Таймер"):
                            ch.previous_step_time += time.perf_counter() - self.pause_start_time

                self.installation_window.pause_button.style_sheet = ready_style_background

            elif self.current_state == ExperimentState.IN_PROGRESS:
                self.current_state = ExperimentState.PAUSED
                self.pipe_exp.send(["pause", 1])
                self.installation_window.pause_button.setText(QApplication.translate('exp_flow',"Возобновить"))
                self.set_state_text(text = QApplication.translate('exp_flow',"Ожидание продолжения") + "...")
                self.timer_for_pause_exp.start(50)
                self.pause_start_time = time.perf_counter()

    def update_pbar(self, pbar_percent) -> None:
        self.installation_window.pbar.setValue(int(pbar_percent))

    def pause_actions(self):
        """функция срабатывает по таймеру во время паузы эксперимента"""

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

        style = (
            "background-color: rgb("
            + str(self.bright)
            + ","
            + "255"
            + ","
            + str(self.bright)
            + ");"
        )
        if not self.current_state == ExperimentState.PAUSED:
            self.installation_window.pause_button.style_sheet = ready_style_background

        else:
            self.installation_window.pause_button.setStyleSheet(style)

    def finalize_experiment(self, error=False, error_start_exp=False):
        self.current_state = ExperimentState.COMPLETED

        self.timer_for_connection_main_exp_thread.stop()
        self.timer_second_thread_tasks.stop()
        self.update_pbar( 0 )
        self.installation_window.label_time.setText( "" )
        self.timer_for_receive_data_exp.stop()
        self.graph_controller.stop_session_running( self.current_session_graph_id )

        if error:
            if error_start_exp :
                text = QApplication.translate('exp_flow',"Эксперимент прерван из-за ошибки при настройке прибора")
            else:
                text = QApplication.translate('exp_flow',"Эксперимент прерван из-за ошибки при опросе прибора")
            self.add_text_to_log( text, "err")
            self.show_critical_window( text )

        else:
            text = QApplication.translate('exp_flow',"Эксперимент завершен")
            self.add_text_to_log( text )
            self.show_information_window( text )

        if self.has_unsaved_data:

            self.set_state_text(text = QApplication.translate('exp_flow',"Сохранение результатов"))

            if self.settings_manager.get_setting('should_prompt_for_session_name')[1]:
                self.meas_session.ask_session_name_description( "Эксперимент завершен" )
            else:
                self.meas_session.set_default_session_name_description()

            if not self.settings_manager.get_setting('way_to_save')[1]:
                self.set_way_save()

            if not error_start_exp :
                try:
                    self.save_results()
                except Exception as e:
                    logger.warning(f"не удалось сохранить результаты {str(e)}", self.buf_file)

        clear_pipe(self.pipe_exp)
        clear_queue(self.experiment_queue)
        clear_queue(self.important_exp_queue)

        self.pipe_exp.close()
        self.experiment_queue.close()
        self.important_exp_queue.close()

        self.prepare_for_reexperiment()

    def prepare_for_reexperiment(self):
            # ------------------подготовка к повторному началу эксперимента---------------------
            self.set_state_text(text = QApplication.translate('exp_flow',"Подготовка к эксперименту"))
            self.message_broker.clear_all_subscribers()
            self.is_experiment_endless = False
            self.installation_window.start_button.setText(QApplication.translate('exp_flow',"Старт"))
            self.pause_exp()
            self.installation_window.pause_button.setStyleSheet(not_ready_style_background)
            self.set_state_text(text = QApplication.translate('exp_flow',"Ожидание старта"))
            self.is_search_resources = True#разрешение на сканирование ресурсов
            self.preparation_experiment()

    