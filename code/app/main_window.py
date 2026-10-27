# code/app/main_window.py
import logging
import os

from PyQt5.QtGui import QKeySequence
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QAction, QFileDialog, QHBoxLayout, QLabel, QMainWindow,
    QMessageBox, QStackedWidget, QVBoxLayout, QWidget,
)

from app.sidebar import IconSidebar

logger = logging.getLogger(__name__)


class UnifiedMainWindow(QMainWindow):
    PAGE_INSTALL     = 0
    PAGE_GRAPHS      = 1
    PAGE_PUBLICATION = 2

    def __init__(self, settings_manager, version, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.version_app      = version

        self._install_ctrl       = None
        self._session_ctrl       = None
        self._installation_page  = None
        self._graphs_page        = None
        self._publication_page   = None
        self._publication_placeholder = None

        self._device_selector   = None
        self._local_devices     = {}
        self._test_commands_win = None
        self._device_creator    = None

        self._bootstrapped = False
        self._bootstrap_in_progress = False

        self.setWindowTitle(f"Experiment Control {version}")
        self.resize(1400, 900)

        # Лёгкий каркас — без installation_class, sessionController,
        # PublicationWindow, deviceSelector и чтения JSON.
        self._build_ui()
        self._build_menu()

        # Тяжёлая инициализация — после первого прохода event loop,
        # т.е. уже после show() главного окна.
        QTimer.singleShot(0, self._deferred_bootstrap)

    def _deferred_bootstrap(self):
        if self._bootstrapped or self._bootstrap_in_progress:
            return
        self._bootstrap_pages()
        self._bootstrapped = True
        self.set_current_page(self.PAGE_INSTALL)

    def _ensure_bootstrapped(self):
        if self._bootstrapped or self._bootstrap_in_progress:
            return
        self._bootstrap_in_progress = True
        self._bootstrap_pages()
        self._bootstrapped = True
        self._bootstrap_in_progress = False

    # ============================================================ UI
    def _build_ui(self):
        central = QWidget(self)
        self.setCentralWidget(central)
        row = QHBoxLayout(central)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        self.sidebar = IconSidebar(self)
        self.sidebar.page_changed.connect(self.set_current_page)
        row.addWidget(self.sidebar)

        self.stack = QStackedWidget(self)
        row.addWidget(self.stack, 1)

        self.sidebar.add_page_button("⚙", "Установка",  self.PAGE_INSTALL)
        self.sidebar.add_page_button("📊", "Графики",   self.PAGE_GRAPHS)
        self.sidebar.add_page_button("📄", "Публикация", self.PAGE_PUBLICATION)

        # Единая строка состояния — для сообщений на уровне главного окна
        self._status_bar = self.statusBar()

    # ========================================================== Menu
    def _build_menu(self):
        mb = self.menuBar()

        # --- 1. Общие меню (первыми, всегда видимы) -----------
        self._build_menu_file(mb)
        self._build_menu_settings(mb)
        self._build_menu_info(mb)

        # --- 2. Меню страниц (после общих, скрываются) --------
        self._build_menu_install(mb)
        self._build_menu_edit(mb)
        self._build_menu_data(mb)
        self._build_menu_analysis(mb)
        self._build_menu_publication(mb)

    # -------------------------------------------------- Общие меню
    def _build_menu_file(self, mb):
        self.menu_file = mb.addMenu("Файл")

        self.act_open_inst = QAction("Открыть установку (.ns)", self)
        self.act_open_inst.triggered.connect(self._on_open_installation)
        self.act_open_proj = QAction("Открыть проект (.hdf5)", self)
        self.act_open_proj.triggered.connect(self._on_open_project)

        self.act_save = QAction("Сохранить", self)
        self.act_save.setShortcut(QKeySequence.Save)
        self.act_save.triggered.connect(self._on_save)

        self.act_save_as = QAction("Сохранить как…", self)
        self.act_save_as.setShortcut(QKeySequence.SaveAs)
        self.act_save_as.triggered.connect(self._on_save_as)

        self.act_exit = QAction("Выход", self)
        self.act_exit.setShortcut(QKeySequence.Quit)
        self.act_exit.triggered.connect(self.close)

        self.menu_file.addActions([self.act_open_inst, self.act_open_proj])
        self.menu_file.addSeparator()
        self.menu_file.addActions([self.act_save, self.act_save_as])
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.act_exit)

    def _build_menu_settings(self, mb):
        self.menu_settings = mb.addMenu("Настройки")

        self.act_toggle_theme = QAction("Тёмная/светлая тема", self)
        self.act_toggle_theme.triggered.connect(self._on_toggle_theme)

        self.menu_language = self.menu_settings.addMenu("Язык")
        self.act_lang_ru = QAction("Русский", self)
        self.act_lang_ru.triggered.connect(
            lambda: self._on_change_language("RUS"))
        self.act_lang_en = QAction("English", self)
        self.act_lang_en.triggered.connect(
            lambda: self._on_change_language("ENG"))
        self.menu_language.addActions([self.act_lang_ru, self.act_lang_en])

        self.menu_settings.addAction(self.act_toggle_theme)

    def _build_menu_info(self, mb):
        self.menu_info = mb.addMenu("Инфо")

        self.act_instruction = QAction("Инструкция", self)
        self.act_instruction.triggered.connect(self._on_instruction)
        self.act_authors = QAction("Об авторах", self)
        self.act_authors.triggered.connect(self._on_authors)
        self.act_version = QAction("Версия приложения", self)
        self.act_version.triggered.connect(self._on_version)
        self.act_open_log = QAction("Открыть лог-файл", self)
        self.act_open_log.triggered.connect(self._on_open_log)

        self.menu_info.addActions(
            [self.act_instruction, self.act_authors, self.act_version])
        self.menu_info.addSeparator()
        self.menu_info.addAction(self.act_open_log)

    # --------------------------------------------- Меню страниц
    def _build_menu_install(self, mb):
        self.menu_install = mb.addMenu("Установка")

        self.act_exp_settings = QAction("Настройки эксперимента…", self)
        self.act_exp_settings.triggered.connect(self._on_exp_settings)

        self.act_add_device = QAction("Добавить прибор…", self)
        self.act_add_device.triggered.connect(self._on_add_device)

        # Режим разработчика: toggle-текст, не checkable QAction — текст
        # всегда берём из реального self._install_ctrl.is_debug, чтобы
        # состояние не рассинхронизировалось после неудачных попыток
        # переключения (например, во время эксперимента).
        self.act_develop_mode = QAction("Включить режим разработчика", self)
        self.act_develop_mode.setToolTip(
            "Включает is_debug: приборы не опрашиваются, вместо реальных "
            "измерений возвращаются заглушки. Переключение блокируется "
            "во время эксперимента.")
        self.act_develop_mode.triggered.connect(self._on_toggle_develop_mode)

        self.act_convert_buf = QAction(
            "Сохранить результаты из buf-файла…", self)
        self.act_convert_buf.setToolTip(
            "Ручное сохранение из файла буфера эксперимента "
            "(Installation_Controller/buf_files/*.txt)")
        self.act_convert_buf.triggered.connect(self._on_convert_buf)

        self.act_local_control = QAction(
            "Локальное управление приборами…", self)
        self.act_local_control.triggered.connect(self._on_local_control)

        self.act_test_commands = QAction("Тест команд…", self)
        self.act_test_commands.triggered.connect(self._on_test_commands)

        self.act_create_device = QAction("Создать прибор…", self)
        self.act_create_device.triggered.connect(self._on_create_device)

        self.menu_install.addAction(self.act_exp_settings)
        self.menu_install.addSeparator()
        self.menu_install.addAction(self.act_add_device)
        self.menu_install.addAction(self.act_convert_buf)
        self.menu_install.addSeparator()
        self.menu_install.addAction(self.act_develop_mode)
        self.menu_install.addSeparator()
        self.menu_install.addAction(self.act_local_control)
        self.menu_install.addAction(self.act_test_commands)
        self.menu_install.addAction(self.act_create_device)

    def _build_menu_edit(self, mb):
        self.menu_edit = mb.addMenu("Правка")

        self.act_undo = QAction("Отменить", self)
        self.act_undo.setShortcut(QKeySequence.Undo)
        self.act_undo.triggered.connect(self._on_undo)
        self.act_redo = QAction("Повторить", self)
        self.act_redo.setShortcut(QKeySequence.Redo)
        self.act_redo.triggered.connect(self._on_redo)
        self.act_rename_params = QAction(
            "Изменить имена параметров", self)
        self.act_rename_params.triggered.connect(self._on_rename_params)

        self.menu_edit.addActions([self.act_undo, self.act_redo])
        self.menu_edit.addSeparator()
        self.menu_edit.addAction(self.act_rename_params)

    def _build_menu_data(self, mb):
        self.menu_data = mb.addMenu("Данные")

        self.act_import_data = QAction("Импорт данных", self)
        self.act_import_data.triggered.connect(self._on_import_data)
        self.act_import_osc = QAction("Импорт осциллограмм", self)
        self.act_import_osc.triggered.connect(self._on_import_osc)
        self.act_save_excel = QAction(
            "Сохранить результаты в Excel", self)
        self.act_save_excel.triggered.connect(self._on_save_excel)

        self.act_live_demo = QAction("Демо: live-сессия", self)
        self.act_live_demo.triggered.connect(self._on_live_demo)
        self.act_static_demo = QAction("Демо: готовые данные", self)
        self.act_static_demo.triggered.connect(self._on_static_demo)

        self.menu_data.addActions(
            [self.act_import_data, self.act_import_osc])
        self.menu_data.addSeparator()
        self.menu_data.addAction(self.act_save_excel)
        self.menu_data.addSeparator()
        self.menu_data.addActions(
            [self.act_live_demo, self.act_static_demo])

    def _build_menu_analysis(self, mb):
        self.menu_analysis = mb.addMenu("Анализ")

        self.act_analysis_tools = QAction("Инструменты анализа", self)
        self.act_analysis_tools.setToolTip(
            "Интерполяция · поиск пиков · производная · интеграл · "
            "FFT · погрешности · пресеты")
        self.act_analysis_tools.triggered.connect(self._on_analysis_tools)
        self.menu_analysis.addAction(self.act_analysis_tools)

    def _build_menu_publication(self, mb):
        self.menu_publication = mb.addMenu("Публикация")

        self.act_validate = QAction("Валидировать", self)
        self.act_validate.triggered.connect(self._on_validate)

        self.act_export_pkg = QAction("Экспорт пакета", self)
        self.act_export_pkg.triggered.connect(self._on_export_pkg)

        self.act_journal_preset = QAction("Пресет журнала", self)
        self.act_journal_preset.triggered.connect(self._on_journal_preset)

        self.act_save_spec = QAction("Сохранить спецификацию…", self)
        self.act_save_spec.triggered.connect(self._on_save_pub_spec)

        self.act_load_spec = QAction("Загрузить спецификацию…", self)
        self.act_load_spec.triggered.connect(self._on_load_pub_spec)

        self.menu_publication.addActions(
            [self.act_validate, self.act_export_pkg, self.act_journal_preset])
        self.menu_publication.addSeparator()
        self.menu_publication.addActions([self.act_save_spec, self.act_load_spec])

    # ========================================================= Pages
    def _bootstrap_pages(self):
        from installation.Installation_class import installation_class

        self._install_ctrl = installation_class(
            settings_manager=self.settings_manager,
            version=self.version_app,
        )
        self._install_ctrl.device_selector = None

        self._install_ctrl.reconstruct_installation([], [])
        self._install_ctrl.start_resource_scanning()
        self._bind_pages_from_controllers()
        
    def _bind_pages_from_controllers(self):
        self._installation_page = self._install_ctrl.installation_window
        if hasattr(self._installation_page, "open_graph_button"):
            self._installation_page.open_graph_button.hide()
        self._hide_page_menu(self._installation_page)
        self.stack.insertWidget(self.PAGE_INSTALL, self._installation_page)

        self._session_ctrl = self._install_ctrl.graph_controller
        self._graphs_page = self._session_ctrl.graphics_win
        self._hide_page_menu(self._graphs_page)
        self.stack.insertWidget(self.PAGE_GRAPHS, self._graphs_page)

        # Публикация — только заглушка. Реальное окно создаётся при первом
        # переходе на страницу «Публикация».
        self._publication_placeholder = QWidget(self.stack)
        lay = QVBoxLayout(self._publication_placeholder)
        lay.setContentsMargins(20, 20, 20, 20)
        label = QLabel(
            "Страница публикации будет создана при первом открытии",
            self._publication_placeholder,
        )
        label.setAlignment(Qt.AlignCenter)
        lay.addWidget(label)
        self._publication_page = self._publication_placeholder
        self.stack.insertWidget(self.PAGE_PUBLICATION, self._publication_placeholder)

        if hasattr(self, "act_develop_mode"):
            self.act_develop_mode.setText(
                "Выключить режим разработчика"
                if self._install_ctrl.is_debug
                else "Включить режим разработчика"
            )
    
    def _hide_page_menu(self, window):
        """Скрыть менюбар встроенной страницы и обнулить ярлыки его действий.

        Без обнуления ярлыков Ctrl+S, Ctrl+Z и др. срабатывали бы дважды:
        и через действие главного окна, и через скрытое действие страницы,
        потому что страница остаётся частью иерархии виджетов QMainWindow.
        """
        if window is None or not hasattr(window, "menuBar"):
            return
        menu_bar = window.menuBar()
        if menu_bar is None:
            return
        menu_bar.hide()
        self._clear_menu_shortcuts(menu_bar)

    def _clear_menu_shortcuts(self, menu):
        """Рекурсивно обнулить ярлыки действий меню (включая подменю)."""
        if menu is None:
            return
        for action in menu.actions():
            action.setShortcut(QKeySequence())
            submenu = action.menu()
            if submenu is not None:
                self._clear_menu_shortcuts(submenu)

    def _rebind_after_reconstruction(self):
        for attr in ("_installation_page", "_graphs_page", "_publication_page"):
            old = getattr(self, attr, None)
            if old is None:
                continue
            idx = self.stack.indexOf(old)
            if idx >= 0:
                self.stack.removeWidget(old)
            try:
                old.hide()
                old.setParent(None)
                old.deleteLater()
            except Exception:
                logger.exception("delete old page failed")
            setattr(self, attr, None)

        self._publication_placeholder = None
        self._bind_pages_from_controllers()
        self.set_current_page(self.PAGE_INSTALL)

    def _on_save_pub_spec(self):
        w = self._pub_widget()
        if not w:
            QMessageBox.warning(self, "Ошибка", "Виджет публикации не готов")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить спецификацию публикации", "", "JSON (*.json)")
        if not path:
            return
        if not path.endswith(".json"):
            path += ".json"
        try:
            w.save_to_file(path)
        except Exception as e:
            logger.exception("save pub spec failed")
            QMessageBox.critical(self, "Ошибка сохранения", str(e))

    def _on_load_pub_spec(self):
        w = self._pub_widget()
        if not w:
            QMessageBox.warning(self, "Ошибка", "Виджет публикации не готов")
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Загрузить спецификацию публикации", "", "JSON (*.json)")
        if not path:
            return
        try:
            w.load_from_file(path)
        except Exception as e:
            logger.exception("load pub spec failed")
            QMessageBox.critical(self, "Ошибка загрузки", str(e))

    # ====================================================== Navigation
    def set_current_page(self, index):
        if index < 0 or index > self.PAGE_PUBLICATION:
            return
        self._ensure_bootstrapped()
        if index == self.PAGE_PUBLICATION:
            self._ensure_publication_page()
        if index >= self.stack.count():
            return
        self.stack.setCurrentIndex(index)
        self.sidebar.set_active(index)
        self._update_menu_visibility(index)
    
    def _update_menu_visibility(self, index):
        is_install = index == self.PAGE_INSTALL
        is_graphs  = index == self.PAGE_GRAPHS
        is_pub     = index == self.PAGE_PUBLICATION

        # Порядок меню в QMenuBar: [Файл][Настройки][Инфо] — всегда
        # на месте; скрываем только модульные, они идут после.
        self.menu_install.menuAction().setVisible(is_install)
        self.menu_edit.menuAction().setVisible(is_graphs)
        self.menu_data.menuAction().setVisible(is_graphs)
        self.menu_analysis.menuAction().setVisible(is_graphs)
        self.menu_publication.menuAction().setVisible(is_pub)

        # Синхронизировать актуальный текст «режим разработчика» —
        # состояние могло измениться при открытии .ns или программно.
        if is_install and self._install_ctrl and hasattr(self, "act_develop_mode"):
            self.act_develop_mode.setText(
                "Выключить режим разработчика"
                if self._install_ctrl.is_debug
                else "Включить режим разработчика")

        self.menuBar().update()

    def current_page(self):
        return self.stack.currentIndex()

    # ==================================================== Публичные API
    def open_installation_file(self, path):
        self._ensure_bootstrapped()
        if self._install_ctrl is None:
            return False

        self._install_ctrl.stop_scan_thread = True
        thread = getattr(self._install_ctrl, "thread_scan_resources", None)
        if thread is not None and thread.is_alive():
            thread.join(timeout=2.0)

        status, buffer = self._install_ctrl.extract_saved_installlation(
            fileName=path
        )
        if status:
            self._rebind_after_reconstruction()
            self.set_current_page(self.PAGE_INSTALL)
        return status

    def open_project_file(self, path):
        self._ensure_bootstrapped()
        if not self._session_ctrl:
            return False
        self._session_ctrl.load_project(path)
        self.set_current_page(self.PAGE_GRAPHS)
        return True
    # ========================================================== Файл
    def _on_open_installation(self):
        if not self._install_ctrl:
            return

        has_sessions = bool(getattr(self._session_ctrl, "graph_sessions", {}))
        if has_sessions:
            ans = QMessageBox.question(
                self, "Открыть установку",
                "Открытие установки пересоздаст графическую сессию.\n"
                "Текущие несохранённые графики будут закрыты. Продолжить?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if ans != QMessageBox.Yes:
                return

        file_name, _ = QFileDialog.getOpenFileName(
            self, "Открыть файл установки", "", "Installation (*.ns)")
        if not file_name:
            return
        try:
            self.open_installation_file(file_name)
        except Exception as e:
            logger.exception("open .ns from menu failed")
            QMessageBox.critical(self, "Ошибка открытия", str(e))

    def _ensure_publication_page(self):
        if self._session_ctrl is None:
            return
        if (self._publication_page is not None
                and self._publication_page is not self._publication_placeholder):
            return

        real_win = self._session_ctrl.get_publication_window()
        if real_win is None:
            return

        self._hide_page_menu(real_win)
        idx = self.stack.indexOf(self._publication_placeholder)
        if idx >= 0:
            self.stack.removeWidget(self._publication_placeholder)
            self._publication_placeholder.deleteLater()
        self.stack.insertWidget(self.PAGE_PUBLICATION, real_win)
        self._publication_page = real_win

    def _on_validate(self):
        w = self._pub_widget()
        if w:
            w._on_validate()

    def _on_export_pkg(self):
        w = self._pub_widget()
        if w:
            w._on_export()

    def _on_journal_preset(self):
        w = self._pub_widget()
        if w and hasattr(w, "_preset_combo"):
            w._preset_combo.showPopup()

    def _on_open_project(self):
        if not self._session_ctrl:
            return
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Открыть проект", "", "Installation (*.hdf5)")
        if not file_name:
            return
        try:
            self._session_ctrl.load_project(file_name)
            self.set_current_page(self.PAGE_GRAPHS)
        except Exception as e:
            logger.exception("open project from menu failed")
            QMessageBox.critical(self, "Ошибка открытия", str(e))

    def _on_save(self):
        page = self.current_page()
        if page == self.PAGE_INSTALL and self._install_ctrl:
            self._install_ctrl.push_button_save_installation()
        elif page == self.PAGE_GRAPHS and self._session_ctrl:
            self._session_ctrl.push_button_save_graph()
        elif page == self.PAGE_PUBLICATION and self._session_ctrl:
            # На странице публикации «Сохранить» = сохранить весь проект .hdf5,
            # а не спецификацию публикации (для неё — отдельный пункт).
            self._session_ctrl.push_button_save_graph()

    def _on_save_as(self):
        page = self.current_page()
        if page == self.PAGE_INSTALL and self._install_ctrl:
            self._install_ctrl.push_button_save_installation_as()
        elif page == self.PAGE_GRAPHS and self._session_ctrl:
            self._session_ctrl.push_button_save_graph_as()
        elif page == self.PAGE_PUBLICATION and self._session_ctrl:
            self._session_ctrl.push_button_save_graph_as()

    # ====================================================== Установка
    def _on_exp_settings(self):
        if self.settings_manager:
            self.settings_manager.ask_exp_settings()

    def _on_add_device(self):
        self._ensure_device_selector()
        self._install_ctrl.device_selector = self._device_selector
        self._install_ctrl.add_new_device()

    def _on_toggle_develop_mode(self):
        if not self._install_ctrl:
            return
        if self._install_ctrl.is_experiment_running():
            self.statusBar().showMessage(
                "Нельзя менять режим разработчика во время эксперимента", 3000)
            return
        self._install_ctrl.change_check_debug()
        self.act_develop_mode.setText(
            "Выключить режим разработчика"
            if self._install_ctrl.is_debug
            else "Включить режим разработчика")
    
    def _on_convert_buf(self):
        if not self._install_ctrl:
            return
        try:
            self._install_ctrl.convert_buf_file()
        except Exception as e:
            logger.exception("convert buf file failed")
            QMessageBox.warning(self, "Ошибка", str(e))

    def _ensure_device_selector(self):
        if self._device_selector is None:
            from device_selector import deviceSelector
            self._device_selector = deviceSelector(self.settings_manager)
        return self._device_selector

    def _on_local_control(self):
        from Devices.available_devices import local_device_class
        from localJSONControl import localDeviceControl

        selector = self._ensure_device_selector()
        device = selector.get_single_device()
        if not device:
            return

        if isinstance(device, str):
            key = device
            if key not in self._local_devices:
                self._local_devices[key] = local_device_class[key]()
            self._local_devices[key].show()
        else:
            key = device.name
            if key not in self._local_devices:
                self._local_devices[key] = localDeviceControl(device)
            self._local_devices[key].show()

    def _on_test_commands(self):
        from device_creator.run_commands import TestCommands
        if self._test_commands_win is None:
            self._test_commands_win = TestCommands()
        self._test_commands_win.show()
        self._test_commands_win.raise_()

    def _on_create_device(self):
        from device_creator.dev_creator import deviceCreator
        if self._device_creator is None:
            self._device_creator = deviceCreator()
            self._device_creator.cancel_click.connect(
                self._rebuild_device_creator)
        self._device_creator.show()
        self._device_creator.raise_()

    def _rebuild_device_creator(self):
        from device_creator.dev_creator import deviceCreator
        self._device_creator = deviceCreator()
        self._device_creator.cancel_click.connect(self._rebuild_device_creator)

    # ========================================================= Правка
    def _on_undo(self):
        if self._session_ctrl:
            self._session_ctrl._undo_current_session()

    def _on_redo(self):
        if self._session_ctrl:
            self._session_ctrl._redo_current_session()

    def _on_rename_params(self):
        if self._session_ctrl:
            self._session_ctrl.show_alias_dialog()

    # ========================================================= Данные

    def _on_save_excel(self):
        if not self._session_ctrl:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить как Excel", "", "Книга Excel (*.xlsx)")
        if not path:
            return
        if not path.endswith(".xlsx"):
            path += ".xlsx"
        try:
            self._session_ctrl._save_excel(path)
            self.statusBar().showMessage(f"Сохранение Excel запущено: {path}", 5000)
        except Exception as e:
            logger.exception("save excel failed")
            QMessageBox.warning(self, "Ошибка сохранения", str(e))

    def _on_import_data(self):
        if self._session_ctrl:
            self._session_ctrl.buttons_controller.handle_import_data()
            # handle_import_data() модальная — выполнится после закрытия диалогов,
            # к этому моменту новые сессии уже созданы.
            self.set_current_page(self.PAGE_GRAPHS)

    def _on_import_osc(self):
        if self._session_ctrl:
            self._session_ctrl.buttons_controller.handle_import_osc()
            self.set_current_page(self.PAGE_GRAPHS)

    def _on_live_demo(self):
        if self._session_ctrl:
            self._session_ctrl.start_live_demo_session()
            self.set_current_page(self.PAGE_GRAPHS)

    def _on_static_demo(self):
        if self._session_ctrl:
            self._session_ctrl.load_static_demo_session()
            self.set_current_page(self.PAGE_GRAPHS)

    # ========================================================= Анализ
    def _on_analysis_tools(self):
        if not self._session_ctrl:
            return
        sess = self._session_ctrl._current_session()
        if sess is not None and hasattr(sess, "inspector"):
            sess.inspector.curve_inspector.tabs.setCurrentWidget(
                sess.inspector.curve_inspector.tools_tab)

    # ===================================================== Публикация
    def _pub_widget(self):
        self._ensure_publication_page()
        if (self._publication_page is not None
                and self._publication_page is not self._publication_placeholder
                and hasattr(self._publication_page, "widget")):
            return self._publication_page.widget()
        return None
    

    # ======================================================= Настройки
    def _on_toggle_theme(self):
        import qdarktheme
        cur = os.environ.get("APP_THEME", "dark")
        new = "light" if cur == "dark" else "dark"
        qdarktheme.setup_theme(new, corner_shape="sharp")
        os.environ["APP_THEME"] = new

    def _on_change_language(self, lang):
        if self.settings_manager:
            self.settings_manager.save_settings({"language": lang})
        QMessageBox.information(
            self, "Язык",
            "Язык сохранён. Перезапустите приложение для применения.")

    # =========================================================== Инфо
    def _on_instruction(self):
        if self._install_ctrl:
            self._install_ctrl.show_instruction()

    def _on_authors(self):
        if self._install_ctrl:
            self._install_ctrl.show_about_autors()

    def _on_version(self):
        QMessageBox.information(
            self, "Версия", f"Версия приложения: {self.version_app}")

    def _on_open_log(self):
        folder = os.path.join(
            os.getenv("USERPROFILE", os.path.expanduser("~")),
            "AppData", "Local", "Installation_Controller")
        if os.path.isdir(folder):
            os.startfile(folder)

    # ========================================================= Закрытие
    def closeEvent(self, event):
        try:
            if self._install_ctrl:
                self._install_ctrl.stop_scan_thread = True
        except Exception:
            logger.exception("stop scan thread failed")

        try:
            if self._install_ctrl and self._install_ctrl.is_experiment_running():
                self._install_ctrl.action_stop_experiment()
        except Exception:
            logger.exception("stop experiment on close failed")

        try:
            if self._install_ctrl:
                self._install_ctrl.saving_controller.terminate_saving_processes()
        except Exception:
            logger.exception("terminate saving processes failed")

        try:
            if self._session_ctrl:
                self._session_ctrl.close()
        except Exception:
            logger.exception("session controller close failed")

        event.accept()