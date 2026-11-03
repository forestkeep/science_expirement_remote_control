# code/saving_data/Parse_data.py
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

import enum
import logging
import os
import time
from datetime import datetime

import pandas
from PyQt5.QtWidgets import QApplication
from send2trash import send2trash
from PyQt5 import QtWidgets
import multiprocessing
from PyQt5.QtCore import QTimer
from openpyxl.workbook.child import INVALID_TITLE_REGEX

from file_io import load_file
from file_io.errors import FileError

logger = logging.getLogger(__name__)


class type_save_file(enum.Enum):
    txt = 1
    excel = 2
    origin = 3


class savingDataClass:
    """Обёртка над BufferData: разбор — в модели, здесь — сохранение в файл."""

    def __init__(self) -> None:
        self.resul_df = None

    def __save_excell(self, output_file_path, result_name):
        message = ""
        status = True
        excel_writer = None

        result_name = INVALID_TITLE_REGEX.sub(' ', result_name)

        if os.path.exists(output_file_path):
            mode = "a"
            try:
                excel_writer = pandas.ExcelWriter(
                    output_file_path,
                    engine='openpyxl',
                    mode=mode,
                    if_sheet_exists='new',
                )
            except PermissionError:
                output_file_path = self.get_free_file_name(output_file_path)
            except Exception as e:
                logger.error(
                    "ошибка создания рабочего класса для сохранения в эксель - %s", e
                )
                message = f"{type(e).__name__} - {e}"
                return output_file_path, message, False

        if excel_writer is None:
            mode = "w"
            excel_writer = pandas.ExcelWriter(
                output_file_path,
                engine='openpyxl',
                mode=mode,
            )

        try:
            self.resul_df.to_excel(excel_writer, sheet_name=result_name, index=False)
        except Exception as e:
            message += f"{type(e).__name__} - {e}"
            logger.error(
                "ошибка сохранения в excel после парсинга - %s %s %s",
                message, result_name, output_file_path,
            )
            return output_file_path, message, False
        finally:
            excel_writer.close()

        return output_file_path, message, status

    def get_free_file_name(self, output_file_path):
        output_file_path = output_file_path[:-5] + "(0).xlsx"
        for i in range(1, 100):
            output_file_path = output_file_path[:-8] + f"({i}).xlsx"
            if os.path.exists(output_file_path):
                continue
            return output_file_path
        return output_file_path

    def __save_txt(self, output_file_path, result_name):
        status = False
        message = ""
        try:
            with open(output_file_path, "a") as file:
                file.write("\n#############################################\n")
                file.write(f"{result_name}\n")
                file.write("#############################################\n")
                file.write(self.resul_df.to_string(index=False))
                status = True
        except Exception as e:
            logger.error(
                "ошибка сохранения в txt после парсинга - %s %s %s",
                e, result_name, output_file_path,
            )
            message = f"{type(e).__name__} - {e}"

        return output_file_path, message, status

    def __save_origin(self, output_file_path, result_name):
        return output_file_path, "", False

    def save_data(self, input_file_path, output_file_path, output_type,
                  result_name, result_description, meta_data):
        """Разобрать buf через load_file → BufferData → записать результата.

        Возвращает (output_file_path, message, status).
        """
        try:
            buffer_data = load_file(input_file_path, hint="buffer_data")
        except FileError as e:
            logger.warning(
                "Ошибка разбора буферного файла %s: %s", input_file_path, e
            )
            return output_file_path, str(e), False

        try:
            self.resul_df = buffer_data.to_dataframe(result_description, meta_data)
        except MemoryError:
            logger.warning("Недостаточно памяти при построении DataFrame")
            message = QApplication.translate(
                "parse_data",
                "Не хватает оперативной памяти для обработки буферного файла. "
                "Не волнуйтесь, данные измерений не пострадали. Попробуйте "
                "перезагрузить приложение и сохранить результаты из буферного файла.",
            )
            return output_file_path, message, False
        except Exception as e:
            logger.exception("Ошибка построения DataFrame")
            return output_file_path, str(e), False

        if not result_name:
            result_name = datetime.now().strftime("%Y-%m-%d %H-%M-%S")

        if output_type == type_save_file.txt:
            return self.__save_txt(output_file_path, result_name)
        if output_type == type_save_file.excel:
            return self.__save_excell(output_file_path, result_name)
        if output_type == type_save_file.origin:
            return self.__save_origin(output_file_path, result_name)

        logger.warning("тип сохранения не определен %s", output_type)
        message = QApplication.translate("parse_data", "Тип сохранения не определен")
        return output_file_path, message, False


def run_saving_worker(queue, input_file_path, output_file_path, output_type,
                      is_delete_buf_file, result_name, result_description, meta_data):
    try:
        save_class = savingDataClass()
        status = True
        message = ""

        output_file_path, message, status = save_class.save_data(
            input_file_path, output_file_path, output_type,
            result_name, result_description, meta_data,
        )
        if status:
            if is_delete_buf_file:
                try:
                    send2trash(input_file_path)
                    queue.put({
                        'status': status,
                        'output_file_path': output_file_path,
                        'message': message,
                        'deleted_buf_file': input_file_path,
                    })
                except Exception as e:
                    message += (
                        f"\nФайл сохранен, но буферный файл не удалось "
                        f"отправить в корзину - {e}"
                    )
                    queue.put({
                        'status': status,
                        'output_file_path': output_file_path,
                        'message': message,
                    })
            else:
                queue.put({
                    'status': status,
                    'output_file_path': output_file_path,
                    'message': message,
                })
        else:
            queue.put({
                'status': status,
                'output_file_path': output_file_path,
                'message': message,
            })
    except Exception as e:
        print(e)
        queue.put({
            'status': False,
            'output_file_path': None,
            'message': f"Критическая ошибка: {str(e)}",
        })


class saving_data_processing:
    def __init__(self, info_callback=None):
        self.info_callback = info_callback
        self.queue = multiprocessing.Queue()
        self.saving_process = None
        self.process_start_time = 0
        self.next_report_time = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self._check_queue_and_status)

        self.input_file_path = None
        self.output_file_path = None
        self.output_type = None
        self.is_delete_buf_file = None
        self.result_name = "Result"
        self.result_description = ""
        self.meta_data = None
        self.adress_return = None

    def terminate(self):
        if self.saving_process and self.saving_process.is_alive():
            self.saving_process.terminate()
            self.saving_process.join()

    def set_parameters(self, input_file_path, output_file_path, output_type,
                       is_delete_buf_file, result_name, result_description, meta_data):
        self.input_file_path = input_file_path
        self.output_file_path = output_file_path
        self.output_type = output_type
        self.is_delete_buf_file = is_delete_buf_file
        self.meta_data = meta_data

        if result_name:
            self.result_name = result_name
        if result_description:
            self.result_description = result_description

    def set_adress_return(self, adress_return):
        self.adress_return = adress_return

    def start_saving(self):
        if not all([self.input_file_path, self.output_file_path, self.adress_return]):
            raise ValueError("Не установлены обязательные параметры или callback")

        self.saving_process = multiprocessing.Process(
            target=run_saving_worker,
            args=(
                self.queue,
                self.input_file_path,
                self.output_file_path,
                self.output_type,
                self.is_delete_buf_file,
                self.result_name,
                self.result_description,
                self.meta_data,
            ),
        )
        self.process_start_time = time.perf_counter()
        self.next_report_time = self.process_start_time + 60 * 3
        self.timer.start(5000)
        self.saving_process.start()
        if self.info_callback is not None:
            self.info_callback(
                f"Сохраняем результаты {self.input_file_path} в {self.output_file_path}"
            )

    def _check_queue_and_status(self):
        while not self.queue.empty():
            try:
                result = self.queue.get_nowait()
                self._handle_result(result)
                return
            except Exception:
                break

        current_time = time.perf_counter()

        if current_time >= self.next_report_time:
            elapsed = int(current_time - self.process_start_time)

            if self.info_callback is not None:
                self.info_callback(
                    f"Сохранение результатов в {self.output_file_path} идет дольше "
                    f"обычного: {elapsed // 60} мин {elapsed % 60} сек. "
                    f"Пожалуйста, подождите..."
                )

            self.next_report_time = current_time + 60 * 30

        if not self.saving_process.is_alive():
            self.timer.stop()
            self.saving_process.join()

    def _handle_result(self, result):
        self.timer.stop()
        if self.saving_process.is_alive():
            self.saving_process.terminate()

        if result['status']:
            if 'deleted_buf_file' in result:
                self.adress_return(
                    status=result['status'],
                    output_file_path=result['output_file_path'],
                    message=result['message'],
                    deleted_buf_file=result['deleted_buf_file'],
                )
            else:
                self.adress_return(
                    status=result['status'],
                    output_file_path=result['output_file_path'],
                    message=result['message'],
                )
        else:
            self.adress_return(
                status=result['status'],
                output_file_path=result['output_file_path'],
                message=result['message'],
            )


class savingController():
    def __init__(self):
        self.saving_processes = []
        self.info_callback = None

    def set_info_callback(self, func):
        self.info_callback = func

    def terminate_saving_processes(self):
        for process in self.saving_processes:
            process.saving_process.terminate()
        self.saving_processes = []

    def process_and_export(self, input_file_path, output_file_path, output_type,
                           meas_session_data, is_delete_buf_file, func_result):
        result_name = meas_session_data.session_name
        result_descriptions = meas_session_data.session_description
        meta_data = meas_session_data.get_meta_data()
        save = saving_data_processing(self.info_callback)
        save.set_parameters(
            input_file_path,
            output_file_path,
            output_type,
            is_delete_buf_file,
            result_name,
            result_descriptions,
            meta_data,
        )
        save.set_adress_return(func_result)
        save.start_saving()
        self.saving_processes.append(save)


# ---------------------------------------------------------------------------
# Тестовые утилиты (сохранены для совместимости, __main__)
# ---------------------------------------------------------------------------

start = time.perf_counter()


def info_callback(message):
    print(message)


def func_answer_test(status, output_file_path, message, deleted_buf_file=False):
    global start

    if status is True:
        print(f"Результаты сохранены в {output_file_path}")
    else:
        print("Ошибка сохранения.", message)

    print(f"Время выполнения {time.perf_counter() - start}")


class mock_measSessionData:
    def __init__(self):
        self.session_name = ''
        self.session_description = ''
        self.session_start_time = ''
        self.session_end_time = ''
        self.session_duration = ''
        self.measurement_parameters = {}

    def get_meta_data(self) -> str:
        return (
            f"start_time={self.session_start_time}\n"
            f"end_time={self.session_end_time}\n"
            f"duration={self.session_duration}"
        )


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    input_file = "pig_in_a_poke_1_2025-06-03 15-57-25.txt"
    is_delete_buf_file = False
    output_file_path = "testData.xlsx"
    meas_session_data = mock_measSessionData()
    saving_ctrl = savingController()
    saving_ctrl.set_info_callback(info_callback)

    saving_ctrl.process_and_export(
        input_file, output_file_path, type_save_file.excel,
        meas_session_data, is_delete_buf_file, func_answer_test,
    )
    sys.exit(app.exec_())