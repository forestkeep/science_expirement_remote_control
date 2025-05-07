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
import time
import copy
import logging
from datetime import datetime

from PyQt5.QtWidgets import QApplication
from Devices.Classes import ch_response_to_step
from Handler_manager import messageBroker
#from profilehooks import profile
import numpy

from multiprocessing import Queue
from shared_buffer_manager import SharedBufferManager

from functions import get_active_ch_and_device, write_data_to_buf_file, clear_queue, clear_pipe, create_clients

logger = logging.getLogger(__name__)

class experimentControl( ):

	def __init__(self, 
						device_classes:        dict,
						message_broker:        messageBroker,
						is_debug:              bool, 
						is_experiment_endless: bool, 
						repeat_exp:            int, 
						repeat_meas:           int,
						is_run_anywhere:       bool,
						first_queue:           Queue,
						second_queue:          Queue,
						third_queue:           Queue,
						important_queue:       Queue,
						buf_file:              str,
						pipe_installation,
						data_pipe,
						session_id:            int
						):
		
		super().__init__()
		self.device_classes = device_classes
		self.message_broker = message_broker
		self.is_debug = is_debug
		self.is_experiment_endless = is_experiment_endless
		self.repeat_experiment = repeat_exp
		self.repeat_meas = repeat_meas
		self.session_id = session_id
		self.buf_file = buf_file
		self.pipe_installation = pipe_installation

		self.is_closed = False

		self.is_exp_run_anywhere = is_run_anywhere
		self.first_queue = first_queue
		self.second_queue = second_queue
		self.third_queue = third_queue
		self.important_queue = important_queue

		self.remaining_time = 10
		self.__stop_experiment = False
		self.__is_paused = False

		self.shared_buffer_manager = SharedBufferManager(data_pipe)

		self.has_unsaved_data = False 

	def check_pipe(self):
			if self.pipe_installation.poll():
				buf = self.pipe_installation.recv()
				if buf[0] == "stop":
					self.__stop_experiment = True
					print(f"стоп {time.perf_counter()}")
				elif buf[0] == "pause":
					if buf[1]:
						print(f"пауза {time.perf_counter()}")
						self.__is_paused = True
					else:
						self.__is_paused = False
				elif buf[0] == "close":
					self.is_closed = True

	#snakeviz baseline.prof - команда для просмотра профилирования
	#@profile(stdout=False, filename='baseline.prof')
	def set_clients(self):
		clients, _ = create_clients([], self.device_classes)
		for device, client in zip(self.device_classes.values(), clients):
			if client:
				device.set_client(client)
			else:
				logger.warning(f"Для прибора {device.name} не создан клиент {client=}")

	def run(self):
		self.has_unsaved_data = False 
		self.set_clients()

		self.start_exp_time = time.perf_counter()
		  
		status = self.check_connections()

		if status != False:
			status = self.set_settings_before_exp()

		error = not status
		error_start_exp = not status

		if error is False and self.__stop_experiment is False:

			self.remaining_time = self.calculate_exp_time()
			if self.remaining_time is True:
				# эксперимент бесконечен
				pass

			elif self.remaining_time is False:
				self.remaining_time = 100000
				# не определено время

			self.first_queue.put(("update_remaining_time", {"remaining_time": self.remaining_time}))

			self.start_exp_time = time.perf_counter()

			self.set_start_priorities()

		target_execute = False
		number_active_device = 4
		last_number_active_device = 0

		self.count_excrt =0

		#----------------------------------------------------------------------------------------------
		if not error_start_exp:
			for i in range(self.repeat_experiment):
				if error :
					break
				if i > 0:
					self.__stop_experiment = False
					self.set_between_experiments()
					
				while not self.__stop_experiment and not error and not self.is_closed:

					self.check_pipe()

					if not self.__is_paused:
						if number_active_device != last_number_active_device or target_execute!=False:
							message_continue_exp = QApplication.translate('exp_flow',"Продолжение эксперимента, приборов:") + str(number_active_device)
							self.third_queue.put(("set_state_text", {"text": message_continue_exp}))
							last_number_active_device = number_active_device

						number_active_device = 0
						number_device_which_act_while = 0

						for device, ch in get_active_ch_and_device( self.device_classes ):

							if not device.get_steps_number(ch) :
								if not ch.do_last_step:
									number_device_which_act_while += 1

							if ch.am_i_active_in_experiment:
								number_active_device += 1
								if device.get_trigger(ch) == QApplication.translate('exp_flow', "Таймер"):
									if time.perf_counter() - ch.previous_step_time >= ch.pause_time:
										ch.previous_step_time = time.perf_counter()
										device.set_status_step(ch.get_name(), True)
										
						if number_active_device == 0:
							"""остановка эксперимента, нет активных приборов"""
							text = QApplication.translate('exp_flow',"Остановка эксперимента") + "..."
							self.first_queue.put(("set_state_text", {"text": text}))

							self.__stop_experiment = True
						if (
							number_device_which_act_while == number_active_device
							and number_active_device == 1
						):
							"""если активный прибор один и он работает, пока работают другие, и у него не стоит флаг последнего шага то стоп"""
							self.__stop_experiment = True

						target_execute = self.get_execute_part()

						if target_execute is not False:
							device = target_execute[0]
							ch = target_execute[1]
							
							device.set_status_step(ch_name=ch.get_name(), status=False)

							ans_device = device.on_next_step(ch, repeat=3)

							ans_request = False

							if ans_device == ch_response_to_step.Step_done:

								ch.number_meas += 1

								if ch.get_type() == "act":
									error, ans_request, time_step = self.do_act(device=device, ch=ch)

								elif ch.get_type() == "meas":
									error, ans_request, time_step = self.do_meas(device=device, ch=ch)

								if not self.has_unsaved_data:
									self.has_unsaved_data = True
									self.important_queue.put(("has_data_to_save", {}))

							elif ans_device == ch_response_to_step.End_list_of_steps:
								ch.am_i_active_in_experiment = False
							else:
								ch.am_i_active_in_experiment = False

							if device.get_steps_number(ch) is not False:
								if (ch.number_meas >= device.get_steps_number(ch) ):
									ch.am_i_active_in_experiment = False

							if ch.do_last_step:#был сделан последний шаг
								ch.am_i_active_in_experiment = False
								ch.do_last_step = False

							if not ch.am_i_active_in_experiment:
								text = device.get_name()\
										+ " "\
										+ str(ch.get_name()) + " "\
										+ QApplication.translate('exp_flow',"завершил работу")
								status = "ok"

								self.first_queue.put(("add_text_to_log", {"text": text, "status": status}))

							current_priority = ch.get_priority()
							self.manage_subscribers(ch = ch)
							self.update_actors_priority(exclude_dev = device, exclude_ch = ch)

							text = f'''\n\r 
										{device.get_name()} {ch.get_name()} \n\r
										Status request = {ans_request} \n\r
										Step time = {round(time_step, 3)} s\n\r
										Number step = {ch.number_meas} \n\r
										Priority = {current_priority}\n\r
									'''
							self.first_queue.put( ("meta_data", {"name": f"{device.get_name()} {ch.get_name()}", "info": text}) )

					status_send = self.shared_buffer_manager.send_data()

		if not self.is_closed:
			for dev, ch in get_active_ch_and_device( self.device_classes ):
				try:
					ans = dev.action_end_experiment(ch)
				except Exception as e:
					logger.warning(f"Ошибка действия прибора {dev} при окончании эксперимента {e}")

			logger.info(f"основной цикл эксперимента завершен, ждем доставки всех данных")

			#ждем пока все данные будут переданы в основной поток
			status_send = True
			text = QApplication.translate('exp_flow', "Обрабатываем данные. Осталось пакетов: {}")
			text = text.format(len(self.shared_buffer_manager.buffer))
			self.important_queue.put(("set_state_text", {"text": text}))
			start_save_time = time.perf_counter()
			print("начали обрабатывать оставшиеся данные в буфере")
			
			self.shared_buffer_manager.max_single_pending = 50#уыеличиваем количество отправляемых за раз пакетов
			while status_send:
				status_send = self.shared_buffer_manager.send_data()
				if time.perf_counter() - start_save_time > 1:
					start_save_time = time.perf_counter()
					text = QApplication.translate('exp_flow', "Обрабатываем данные. Осталось пакетов: {}")
					text = text.format(len(self.shared_buffer_manager.buffer) + len(self.shared_buffer_manager.sent_queue))
					self.important_queue.put(("set_state_text", {"text": text}))

			self.important_queue.put(("finalize_experiment", {"error": error, "error_start_exp": error_start_exp}))

			print("Отправили команду остановки эксперимента")

			time.sleep(1)

			self.__stop_experiment = True

			clear_pipe(self.pipe_installation)
			clear_queue(self.third_queue)

			self.pipe_installation.close()
			self.third_queue.close()

			for device, ch in get_active_ch_and_device( self.device_classes ):
				device.client.close()
		else:
			logger.warning("процесс эксперимента закрыт")

	def do_act(self, device, ch):
		error = False
		step_time = 0

		text = \
			QApplication.translate('exp_flow',"Выполняется действие") + " "\
			+ device.get_name()\
			+ str(ch.get_name())
		self.third_queue.put(("set_state_text", {"text": text}))

		try:
			ans, param, step_time = device.do_action(ch)
		except Exception as ex:
			ans = ch_response_to_step.Step_fail
			logger.warning(f"Ошибка действия прибора {device} в эксперименте: {str(ex)}")

		if ans == ch_response_to_step.Incorrect_ch:
			pass
		elif ans == ch_response_to_step.Step_done:

			text = QApplication.translate('exp_flow',"шаг") + " "\
				+ device.get_name() + " "\
				+ str(ch.get_name()) + " "\
				+ QApplication.translate('exp_flow',"сделан за") + " "\
				+ str(round(step_time, 3))\
				+ " s"

			self.third_queue.put(("add_text_to_log", {"text": text, "status": ""}))
			
		elif ans == ch_response_to_step.Step_fail:
			ch.am_i_active_in_experiment = False

			text = QApplication.translate('exp_flow',"Ошибка опроса") + " "\
				+ device.get_name()\
				+ str(ch.get_name())

			self.first_queue.put(("add_text_to_log", {"text": text, "status": "err"}))

			if not self.is_exp_run_anywhere:
				error = True 
		else:
			pass

		self.remaining_time = self.calc_last_exp_time()
		self.first_queue.put(("update_remaining_time", {"remaining_time": self.remaining_time}))

		return error, ans, step_time

	def do_meas(self, device, ch):

		error = False
		ans = ch_response_to_step.Step_fail
		text = \
			QApplication.translate('exp_flow',"Выполняется измерение") + " "\
			+ device.get_name()\
			+ str(ch.get_name())

		self.third_queue.put(("set_state_text", {"text": text}))

		logger.debug(
			"Выполняется измерение "
			+ device.get_name()
			+ str(ch.get_name())
		)
		repeat_counter = 0
		step_time = 0
		while repeat_counter < self.repeat_meas:
			repeat_counter += 1

			try:
				result = device.do_meas(ch)
			except Exception as ex:
				result = ch_response_to_step.Step_fail
				logger.warning(
					f"Ошибка измерения прибора {device} в эксперименте: {str(ex)}")
					
			if result != ch_response_to_step.Step_fail:
				if len(result) == 3:
					ans, param, step_time = result
					message = False
				elif len(result) == 4:
					ans, param, step_time, message = result
				else:
					logger.warning(f"неправильная структура ответа прибора result = {result}")

				logger.info(f"расшифрованные параметры {param=}")
				if ans == ch_response_to_step.Incorrect_ch:
					break

				if message != False:
					text = device.get_name()\
						+ " "\
						+ str(ch.get_name())\
						+ message
					
					self.third_queue.put(("add_text_to_log", {"text": text, "status": ""}))
				
				time_t = time.perf_counter() - self.start_exp_time

				if device.device_type == "oscilloscope":
					par = copy.deepcopy(param)
					par = device.distribute_parameters(par)
				else:
					par = {1:param}
					
				for val in par.values():
						if len(val) > 1:#если размер меньше одного, то данных нет
							self.shared_buffer_manager.add_data(val, time_t)

				ch.last_step_time = step_time

				text = "\t".join( [str(param) for param in param] ) + "\n"
				message = f"{datetime.now().strftime('%H:%M:%S.%f')[:-3] + ' '} {text.replace('.', ',')}"
				write_data_to_buf_file(file = self.buf_file, message = message, addTime = False)

				if ans == ch_response_to_step.Step_done:
					text = \
						QApplication.translate('exp_flow',"шаг") + " "\
						+ device.get_name()\
						+ " "\
						+ str(ch.get_name()) + " "\
						+ QApplication.translate('exp_flow',"сделан за")+ " "\
						+ str(round(step_time, 3))\
						+ " s"

					self.third_queue.put(("add_text_to_log", {"text": text, "status": ""}))
					
				elif ans == ch_response_to_step.Step_fail:
					text = \
						QApplication.translate('exp_flow',"Ошибка опроса") + " "\
						+ device.get_name() + " "\
						+ str(ch.get_name())

					self.first_queue.put(("add_text_to_log", {"text": text, "status": "err"}))

					if not self.is_exp_run_anywhere :
						ch.am_i_active_in_experiment = False
						error = True
					break
			else:

				text =\
					QApplication.translate('exp_flow',"Ошибка опроса") + " "\
					+ device.get_name() + " "\
					+ str(ch.get_name())

				self.first_queue.put(("add_text_to_log", {"text": text, "status": "err"}))

				if not self.is_exp_run_anywhere :
					ch.am_i_active_in_experiment = False
					error = True
				break

			self.remaining_time = self.calc_last_exp_time()
			self.first_queue.put(("update_remaining_time", {"remaining_time": self.remaining_time}))

		return error, ans, step_time
	
	def set_pause(self):
		self.__is_paused = True

	def unset_pause(self):
		self.__is_paused = False

	def stop_exp(self):
		self.__stop_experiment = True

	'''
	def update_parameters(self, data, entry, time):
			try:
				device, channel = entry[0].split()
			except:
				device, channel = "unknown_dev_1", "unknown_ch-1"
			parameter_pairs = entry[1:]
			status = True

			if "pig_in_a_poke" in device:
				new_pairs = []
				for index, pair in enumerate(parameter_pairs):
					new_pairs.append(pair)
				parameter_pairs = new_pairs

			if device not in data:
				data[device] = {}

			if channel not in data[device]:
				data[device][channel] = {}

			for parameter_pair in parameter_pairs:
				try:
					name, value = parameter_pair[0].split("=")
				except:
					logger.warning(f"ошибка при декодировании параметра {parameter_pair}")
					continue

				if "wavech" in name:  # oscilloscope wave
					value = value.split("|")
					buf = []
					for val in value:
						try:
							buf.append(float(val))
						except ValueError:
							logger.warning(f"не удалось преобразовать в число: {device=} {channel=} {name=} {val=}")
							continue
					value = numpy.array(buf)

				else:
					try:
						value = float(value)
					except ValueError:
						logger.info(f"не удалось преобразовать в число: {device=} {channel=} {name=} {value=}")
						continue

				if name not in data[device][channel]:
					data[device][channel][name] = [[], []]
				data[device][channel][name][0].append(value)
				data[device][channel][name][1].append(time)

			return status, data
	'''
	def calc_last_exp_time(self) -> float:
		buf_time = [0]
		for device, ch in get_active_ch_and_device( self.device_classes ):

			if ch.am_i_active_in_experiment :
				trig = device.get_trigger(ch)
				if trig == QApplication.translate('exp_flow', "Таймер"):
					steps = device.get_steps_number(ch) - ch.number_meas
					if steps is not False:
						t = (
							steps
							* (device.get_trigger_value(ch) + ch.last_step_time)
							* float(self.repeat_meas)
						)
						buf_time.append(t)
		remaining_time = max(buf_time) + (time.perf_counter() - self.start_exp_time)
		return remaining_time

	def calculate_exp_time(self):
		"""оценивает продолжительность эксперимента, возвращает результат в секундах, если эксперимент бесконечно долго длится, то вернется ответ True. В случае ошибки при расчете количества секунд вернется False"""
		# проверить, есть ли бесконечный эксперимент, если да, то расчет не имеет смысла, и анализ в процессе выполнения тоже
		# во время эксперимента после каждого измерения пересчитывается максимальное время каждого прибора и выбирается максимум, от этого максимума рассчитывается оставшийся процент времени

		#self.is_experiment_endless = self.analyse_endless_exp()

		if self.is_experiment_endless :
			return True  # вернем правду в случае бесконечного эксперимента

		max_exp_time = 0

		for device in self.device_classes.values():
			for ch in device.channels:
				buf_time = False
				if ch.is_ch_active():
					trig = device.get_trigger(ch)
					if trig == QApplication.translate('exp_flow', "Таймер"):
						steps = device.get_steps_number(ch)
						if steps is not False:
							buf_time = (
								steps
								* (device.get_trigger_value(ch) + ch.base_duration_step)
							) * float(self.repeat_meas) * float(self.repeat_experiment)

					elif trig == QApplication.translate('exp_flow', "Внешний сигнал"):
						# TODO: рассчитать время в случае срабатывания цепочек приборов. Найти корень цепочки и смотреть на его параметры, значение таймера и количество повторов, затем рассчитать длительность срабатывания цепочки и сравнить со значением таймера, вернуть наибольшее
						continue
					else:
						continue

				if buf_time is not False:

					max_exp_time = max(max_exp_time, buf_time)

		return max_exp_time

	def get_execute_part(self):
		"""Возващает спсок из устройства и канала, которые должны сделать действие, отбор выполняется с учетом приоритета"""

		target_execute = False
		target_priority = self.min_priority + 1
		for device in self.device_classes.values():
			for ch in device.channels:
				if ch.is_ch_active():
					if ch.am_i_active_in_experiment:
						if device.get_status_step(ch_name=ch.get_name()) :
							if ch.get_priority() < target_priority:
								target_execute = [device, ch]
								target_priority = ch.get_priority()
		return target_execute

	def set_start_priorities(self):
		self.min_priority = 0
		priority = 1

		for device in self.device_classes.values():
			for ch in device.channels:
				if ch.is_ch_active():
					ch.am_i_active_in_experiment = True
					ch.do_last_step = False
					ch.number_meas = 0
					ch.previous_step_time = time.perf_counter()
					ch.pause_time = device.get_trigger_value(ch)
					priority += 1
					self.min_priority += 1

	def set_settings_before_exp(self):

		ch_done = {}
		status = True
		for dev, ch in get_active_ch_and_device( self.device_classes ):


			if ch.number in ch_done.values() and dev.get_name() in ch_done.keys():
				continue

			ch_done[dev.get_name()] = ch.number

			try:
				ans = dev.action_before_experiment(ch.number)
			except Exception as ex:
				ans = False
				logger.warning(
					f"Ошибка действия прибора {dev} перед экспериментом: {str(ex)}"
				)
			if not ans:
				logger.debug(
					"ошибка при настройке " + dev.get_name() + " перед экспериментом"
				)

				text = \
					QApplication.translate('exp_flow',"Ошибка настройки") + " "\
					+ dev.get_name() + " ch-"\
					+ str(ch.number) + " "\
					+ QApplication.translate('exp_flow',"перед экспериментом. Проверьте подключение."),
					
				self.first_queue.put(("add_text_to_log", {"text": text, "status": "err"}))

				if not self.is_debug:
					status = False
					text = QApplication.translate('exp_flow',"Остановка, ошибка")
					self.third_queue.put(("set_state_text", {"text": text}))
				# --------------------------------------------------------
			else:
				text = \
					dev.get_name() + " ch-" + str(ch.number) + QApplication.translate('exp_flow'," настроен")
				self.third_queue.put(("add_text_to_log", {"text": text, "status": ""}))

		return status

	def check_connections(self):
		'''checking connection devices'''
		status = True
		for dev in self.device_classes.values():
			is_connect = dev.check_connect()

			if not is_connect:
				status = False
				logger.warning(f"Нет ответа прибора {dev.get_name()}")
				text =\
					QApplication.translate('exp_flow',"Прибор")\
					+ " " + dev.get_name() + " "\
					+ QApplication.translate('exp_flow',"не отвечает")
					
				self.first_queue.put(("add_text_to_log", {"text": text, "status": "err"}))
			else:
				if is_connect != None:
					text =\
						QApplication.translate('exp_flow',"Ответ") + " " + dev.get_name() + " " + str(is_connect)
					self.third_queue.put(("add_text_to_log", {"text": text, "status": ""}))


		if self.is_debug:
			status = True

		return status

	def manage_subscribers(self, ch):
		subscribers_do_operation = self.message_broker.get_subscribers(
			publisher=ch, name_subscribe=ch.do_operation_trigger
		)

		if not ch.am_i_active_in_experiment :
			"""останавливаем подписчиков, которые срабатывали по завершению операции"""

			for subscriber in subscribers_do_operation:     
				if subscriber.am_i_active_in_experiment :            
					dev = subscriber.device_class
					if "do_operation" in dev.get_trigger_value(subscriber):                   

						text=dev.get_name()\
							+ " "\
							+ str(subscriber.get_name()) + " "\
							+ QApplication.translate('exp_flow'," завершил работу")

						self.third_queue.put(("add_text_to_log", {"text": text, "status": "ok"}))

						subscriber.do_last_step = True

			self.message_broker.push_publish(
				name_subscribe=ch.end_operation_trigger, publisher=ch
			)
			subscribers_end_operation = self.message_broker.get_subscribers(
				publisher=ch, name_subscribe=ch.end_operation_trigger
			)
			for subscriber in subscribers_end_operation:
				subscriber.do_last_step = True
		

		"""передаем сигнал всем подписчикам о том, что операция произведена"""
		self.message_broker.push_publish(
			name_subscribe=ch.do_operation_trigger, publisher=ch
		)

	def update_actors_priority(self, exclude_dev, exclude_ch):
		for dev in self.device_classes.values():
			for channel in dev.channels:
				if channel.is_ch_active():
					if (
						dev == exclude_dev
						and exclude_ch.get_name() == channel.get_name()
					):
						continue
					else:
						if channel.get_priority() > exclude_ch.get_priority():
							channel.increment_priority()
		exclude_ch.set_priority(priority=self.min_priority)

	def set_between_experiments(self):
			for device in self.device_classes.values():
				for ch in device.channels:
					if ch.is_ch_active():
						ch.am_i_active_in_experiment = True
						ch.number_meas = 0
				device.confirm_parameters()
