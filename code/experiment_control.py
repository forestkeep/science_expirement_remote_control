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

from functions import get_active_ch_and_device

logger = logging.getLogger(__name__)


class message_status(enum.Enum):
    info = 1
    warning = 2
    critical = 3


class ExperimentBridge(analyse):
    def __init__(self) -> None:
        super().__init__()
        self.experiment_thread = None
        self.stop_experiment   = False
        self.pause_start_time  = 0
        
    def is_experiment_running(self) -> bool:
        answer = False
        if hasattr(self, "experiment_thread"):
            answer = self.experiment_thread is not None and self.experiment_thread.is_alive()
        return answer

    def connection_two_thread(self):
        """функция для обновления интерфейса во время эксперимента"""
        if self.is_experiment_running():

            if not self.pause_flag:
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
            self.preparation_experiment()
            self.installation_window.label_time.setText("")

    def stoped_experiment(self):
        self.stop_experiment = True
        self.exp_controller.stop_exp()
        self.set_state_text(QApplication.translate('exp_flow',"Остановка") + "...")

    def pause_exp(self):
        if self.is_experiment_running():
            if self.pause_flag:
                self.pause_flag = False
                self.exp_controller.unset_pause()
                self.installation_window.pause_button.setText(QApplication.translate('exp_flow',"Пауза"))
                self.timer_for_pause_exp.stop()

                self.start_exp_time += time.perf_counter() - self.pause_start_time
                for device, ch in get_active_ch_and_device( self.dict_active_device_class):
                    if ch.am_i_active_in_experiment:
                        if device.get_trigger(ch) == QApplication.translate('exp_flow', "Таймер"):
                            ch.previous_step_time += time.perf_counter() - self.pause_start_time

                self.installation_window.pause_button.style_sheet = ready_style_background

            else:
                self.pause_flag = True
                self.exp_controller.set_pause()
                self.installation_window.pause_button.setText(QApplication.translate('exp_flow',"Возобновить"))
                self.set_state_text(QApplication.translate('exp_flow',"Ожидание продолжения") + "...")
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
        if not self.pause_flag:
            self.installation_window.pause_button.style_sheet = ready_style_background

        else:
            self.installation_window.pause_button.setStyleSheet(style)

    def finalize_experiment(self, error=False, error_start_exp=False):

        self.timer_for_connection_main_exp_thread.stop()
        self.timer_second_thread_tasks.stop()
        self.update_pbar( 0 )
        self.installation_window.label_time.setText( "" )
         
        if self.graph_window is not None:
            self.graph_window.update_graphics(self.measurement_parameters, is_exp_stop = True)

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

        if self.exp_controller.has_unsaved_data:

            self.set_state_text(QApplication.translate('exp_flow',"Сохранение результатов"))

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

        self.prepare_for_reexperiment()

    def prepare_for_reexperiment(self):
            # ------------------подготовка к повторному началу эксперимента---------------------
            self.set_state_text(QApplication.translate('exp_flow',"Подготовка к эксперименту"))
            self.message_broker.clear_all_subscribers()
            self.is_experiment_endless = False
            self.stop_experiment = False
            self.installation_window.start_button.setText(QApplication.translate('exp_flow',"Старт"))
            self.pause_flag = True
            self.pause_exp()
            self.installation_window.pause_button.setStyleSheet(not_ready_style_background)
            self.set_state_text(QApplication.translate('exp_flow',"Ожидание старта"))
            self.is_search_resources = True#разрешение на сканирование ресурсов

    