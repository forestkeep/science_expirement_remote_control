from installation_window import Ui_Installation
import sys
from PyQt5 import QtCore, QtGui, QtWidgets
import copy

class installation_class():
	def __init__(self) -> None:
		print("класс установки создан")

	def reconstruct_installation(self,current_installation_list):
		print(current_installation_list)
		self.current_installation_list = current_installation_list
		self.installation_window = Ui_Installation()
		self.installation_window.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
		self.installation_window.setupUi(self.installation_window,current_installation_list)#размер передан для масштабирования окна
		if len(current_installation_list) > 0:
			self.installation_window.change_device_button[current_installation_list[0]].clicked.connect(lambda : self.testable(current_installation_list[0]))
		if len(current_installation_list) > 1:
			self.installation_window.change_device_button[current_installation_list[1]].clicked.connect(lambda : self.testable(current_installation_list[1]))
		if len(current_installation_list) > 2:
			self.installation_window.change_device_button[current_installation_list[2]].clicked.connect(lambda : self.testable(current_installation_list[2]))
		if len(current_installation_list) > 3:
			self.installation_window.change_device_button[current_installation_list[3]].clicked.connect(lambda : self.testable(current_installation_list[3]))
		if len(current_installation_list) > 4:
			self.installation_window.change_device_button[current_installation_list[4]].clicked.connect(lambda : self.testable(current_installation_list[4]))
		if len(current_installation_list) > 5:
			self.installation_window.change_device_button[current_installation_list[5]].clicked.connect(lambda : self.testable(current_installation_list[5]))
		'''
		for i in range(len(current_installation_list)):
			self.installation_window.change_device_button[current_installation_list[0]].clicked.connect(lambda : self.testable(i))
		'''

		print("реконструирован класс установки")
	def testable(self,device):
		print(type(device))

		print("кнопка нажата, устройство -" + str(device))

	def show_window_installation(self):
		print("показать окно класса установки")
		self.installation_window.show()
		#sys.exit(self.app.exec_())
	def close_window_installation(self):
		print("закрыть окно установки")
		try:
			self.installation_window.close()
			print("окно закрылось")
		except:
			print("объект был удален и посему закрытия не получилось, оно итак закрыто")

if __name__ == "__main__":
	lst = ["m1","m2","m3","m4"]
	app = QtWidgets.QApplication(sys.argv)
	a = installation_class()
	a.reconstruct_installation(lst)
	a.show_window_installation()
	sys.exit(app.exec_())