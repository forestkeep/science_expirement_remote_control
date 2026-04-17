
from PyQt5 import QtWidgets, QtCore, QtGui

class AnimationWindow(QtWidgets.QWidget):
    """Отдельное окно для управления анимацией графика"""

    def __init__(self, animator, parent=None):
        super().__init__(parent)
        self.animator = animator
        self.setWindowTitle(self.animator.get_curve_name())
        self.setWindowFlags(QtCore.Qt.Window)
        self.setMinimumSize(400, 500)
        self.init_ui()
        self.connect_signals()
        self.update_ui_state()

    def init_ui(self):
        self.max_dots = 1000
        layout = QtWidgets.QVBoxLayout(self)

        # --- Кнопки управления ---
        buttons_layout = QtWidgets.QHBoxLayout()
        self.btn_start = QtWidgets.QPushButton("▶ Старт")
        self.btn_pause = QtWidgets.QPushButton("⏸ Пауза")
        self.btn_resume = QtWidgets.QPushButton("▶ Возобновить")
        self.btn_stop = QtWidgets.QPushButton("⏹ Стоп")
        self.btn_start.setToolTip("Начать анимацию (с начала)")
        self.btn_pause.setToolTip("Приостановить анимацию точек")
        self.btn_resume.setToolTip("Возобновить анимацию точек")
        self.btn_stop.setToolTip("Остановить анимацию и восстановить исходное состояние")
        buttons_layout.addWidget(self.btn_start)
        buttons_layout.addWidget(self.btn_pause)
        buttons_layout.addWidget(self.btn_resume)
        buttons_layout.addWidget(self.btn_stop)
        layout.addLayout(buttons_layout)

        # --- Режим анимации: применять фильтры после ---
        self.chk_apply_filters = QtWidgets.QCheckBox("Применять фильтры после анимации")
        self.chk_apply_filters.setChecked(True)
        self.chk_apply_filters.setToolTip("Если включено, после отображения всех точек последовательно применятся сохранённые фильтры")
        layout.addWidget(self.chk_apply_filters)

        # --- Настройка скорости ---
        speed_group = QtWidgets.QGroupBox("Скорость анимации точек")
        speed_layout = QtWidgets.QVBoxLayout(speed_group)

        self.speed_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.speed_slider.setRange(1, self.max_dots)
        self.speed_slider.setValue(50)
        self.speed_slider.setTickInterval(50)
        self.speed_slider.setTickPosition(QtWidgets.QSlider.TicksBelow)
        speed_layout.addWidget(self.speed_slider)

        speed_value_layout = QtWidgets.QHBoxLayout()
        self.speed_spin = QtWidgets.QSpinBox()
        self.speed_spin.setRange(1, self.max_dots)
        self.speed_spin.setValue(50)
        self.speed_spin.setSuffix(" pts/s")
        speed_value_layout.addWidget(QtWidgets.QLabel("Скорость:"))
        speed_value_layout.addWidget(self.speed_spin)
        speed_value_layout.addStretch()
        speed_layout.addLayout(speed_value_layout)

        duration_layout = QtWidgets.QHBoxLayout()
        self.duration_spin = QtWidgets.QDoubleSpinBox()
        self.duration_spin.setRange(0.1, 60.0)
        self.duration_spin.setValue(2.0)
        self.duration_spin.setSuffix(" сек")
        self.duration_spin.setToolTip("Установить общую длительность анимации (пересчитает скорость)")
        btn_set_duration = QtWidgets.QPushButton("Установить длительность")
        btn_set_duration.clicked.connect(self.set_duration_from_spin)
        duration_layout.addWidget(QtWidgets.QLabel("Длительность:"))
        duration_layout.addWidget(self.duration_spin)
        duration_layout.addWidget(btn_set_duration)
        duration_layout.addStretch()
        speed_layout.addLayout(duration_layout)

        layout.addWidget(speed_group)

        # --- Настройка задержки между фильтрами ---
        filter_group = QtWidgets.QGroupBox("Применение фильтров")
        filter_layout = QtWidgets.QHBoxLayout(filter_group)
        self.filter_delay_label = QtWidgets.QLabel("Задержка между фильтрами (мс):")
        self.filter_delay_spin = QtWidgets.QSpinBox()
        self.filter_delay_spin.setRange(50, 5000)
        self.filter_delay_spin.setValue(500)
        self.filter_delay_spin.setSuffix(" мс")
        filter_layout.addWidget(self.filter_delay_label)
        filter_layout.addWidget(self.filter_delay_spin)
        filter_layout.addStretch()
        layout.addWidget(filter_group)

        # --- Индикация прогресса ---
        progress_group = QtWidgets.QGroupBox("Прогресс")
        progress_layout = QtWidgets.QVBoxLayout(progress_group)

        self.progress_points = QtWidgets.QProgressBar()
        self.progress_points.setFormat("Точки: %v / %m")
        self.progress_filters = QtWidgets.QProgressBar()
        self.progress_filters.setFormat("Фильтры: %v / %m")
        progress_layout.addWidget(self.progress_points)
        progress_layout.addWidget(self.progress_filters)
        layout.addWidget(progress_group)

        # --- Информационная панель ---
        info_group = QtWidgets.QGroupBox("Информация")
        info_layout = QtWidgets.QFormLayout(info_group)
        self.lbl_total_points = QtWidgets.QLabel("0")
        self.lbl_total_filters = QtWidgets.QLabel("0")
        self.lbl_status = QtWidgets.QLabel("Остановлена")
        self.lbl_speed_display = QtWidgets.QLabel("50 pts/s")
        info_layout.addRow("Всего точек:", self.lbl_total_points)
        info_layout.addRow("Всего фильтров:", self.lbl_total_filters)
        info_layout.addRow("Статус:", self.lbl_status)
        info_layout.addRow("Текущая скорость:", self.lbl_speed_display)
        layout.addWidget(info_group)

        self.setLayout(layout)

    def connect_signals(self):
        self.btn_start.clicked.connect(self.start_animation)
        self.btn_pause.clicked.connect(self.animator.pause)
        self.btn_resume.clicked.connect(self.animator.resume)
        self.btn_stop.clicked.connect(self.stop_animation)

        self.speed_slider.valueChanged.connect(self.update_speed_from_slider)
        self.speed_spin.valueChanged.connect(self.update_speed_from_spin)

        self.animator.progress.connect(self.update_points_progress)
        self.animator.filter_progress.connect(self.update_filters_progress)
        self.animator.finished.connect(self.on_animation_finished)

        self.status_timer = QtCore.QTimer(self)
        self.status_timer.timeout.connect(self.update_status_display)
        self.status_timer.start(200)

    def update_ui_state(self):
        is_playing = getattr(self.animator, '_is_playing', False)
        is_paused = getattr(self.animator, '_is_paused', False)
        self.btn_start.setEnabled(not is_playing)
        self.btn_pause.setEnabled(is_playing and not is_paused)
        self.btn_resume.setEnabled(is_playing and is_paused)
        self.btn_stop.setEnabled(is_playing or is_paused)
        self.chk_apply_filters.setEnabled(not is_playing)
        self.filter_delay_spin.setEnabled(not is_playing)
        self.speed_slider.setEnabled(not is_playing)
        self.speed_spin.setEnabled(not is_playing)
        self.duration_spin.setEnabled(not is_playing)

    def start_animation(self):
        apply_filters = self.chk_apply_filters.isChecked()
        delay = self.filter_delay_spin.value()
        self.animator.set_speed(self.speed_slider.value())
        self.animator.start(reset=True, apply_filters_after=apply_filters, filter_delay_ms=delay)
        total_filters = len(self.animator.saved_filters) if hasattr(self.animator, 'saved_filters') else 0
        self.progress_filters.setMaximum(max(1, total_filters))
        self.lbl_total_filters.setText(str(total_filters))

    def stop_animation(self):
        self.animator.stop(restore_filters=True)
        self.progress_points.reset()
        self.progress_filters.reset()
        self.update_info()

    def set_duration_from_spin(self):
        duration = self.duration_spin.value()
        if duration > 0 and self.animator.total_points > 0:
            speed = int(self.animator.total_points / duration)
            speed = max(1, min(self.max_dots, speed))
            self.speed_slider.setValue(speed)
            self.speed_spin.setValue(speed)

    def update_speed_from_slider(self, value):
        self.speed_spin.blockSignals(True)
        self.speed_spin.setValue(value)
        self.speed_spin.blockSignals(False)
        self.animator.set_speed(value)
        self.lbl_speed_display.setText(f"{value} pts/s")

    def update_speed_from_spin(self, value):
        self.speed_slider.blockSignals(True)
        self.speed_slider.setValue(value)
        self.speed_slider.blockSignals(False)
        self.animator.set_speed(value)
        self.lbl_speed_display.setText(f"{value} pts/s")

    def update_points_progress(self, current, total):
        self.progress_points.setMaximum(total)
        self.progress_points.setValue(current)
        self.lbl_total_points.setText(str(total))

    def update_filters_progress(self, current, total):
        self.progress_filters.setMaximum(total)
        self.progress_filters.setValue(current)

    def update_info(self):
        total_points = self.animator.total_points if hasattr(self.animator, 'total_points') else 0
        self.lbl_total_points.setText(str(total_points))
        filters_count = len(self.animator.saved_filters) if hasattr(self.animator, 'saved_filters') else len(self.animator.curve.filters_history)
        self.lbl_total_filters.setText(str(filters_count))
        self.progress_filters.setMaximum(max(1, filters_count))
        self.progress_filters.setValue(0)

    def update_status_display(self):
        if not hasattr(self.animator, '_is_playing'):
            return
        is_playing = self.animator._is_playing
        is_paused = self.animator._is_paused
        if is_playing and not is_paused:
            status = "Анимация точек..."
        elif is_playing and is_paused:
            status = "Приостановлена"
        else:
            status = "Остановлена"
        self.lbl_status.setText(status)
        self.update_ui_state()

    def on_animation_finished(self):
        self.update_info()
        self.lbl_status.setText("Завершена")

    def closeEvent(self, event):
        """При закрытии окна останавливаем анимацию"""
        if self.animator:
            self.animator.stop(restore_filters=True)
        event.accept()