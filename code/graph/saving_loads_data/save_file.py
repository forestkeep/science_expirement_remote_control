import h5py
import numpy as np
import json

def create_session_file(filename):
    with h5py.File(filename, 'w') as f:
        # Мета-информация о формате
        f.attrs["file_format"] = "NS Session v1.0"
        f.attrs["created"] = "2025-07-24T12:00:00Z"
        
        # Создаем несколько сессий
        for session_idx in range(1, 4):  # 3 сессии для примера
            session_name = f"Session{session_idx}"
            session = f.create_group(session_name)
            
            # Параметры сессии (динамические атрибуты)
            params = session.create_group("Parameters")
            params.attrs["name"] = f"Сессия {session_idx}"
            params.attrs["description"] = f"Тестовая сессия #{session_idx}"
            params.attrs["author"] = "Пользователь"
            # ... можно добавить любые другие параметры
            
            # Настройки полей
            field_settings = session.create_group("FieldSettings")
            
            # Группа для поля графиков
            plot_field = field_settings.create_group("PlotField")
            plot_field.attrs["background_color"] = "#FFFFFF"
            plot_field.attrs["grid_enabled"] = True
            plot_field.attrs["grid_color"] = "#CCCCCC"
            # ... другие настройки
            
            # Группа для поля осциллограмм
            osc_field = field_settings.create_group("OscilloscopeField")
            osc_field.attrs["background_color"] = "#000000"
            osc_field.attrs["grid_enabled"] = False
            # ... другие настройки
            
            # Сырые данные
            raw_data = session.create_group("RawData")
            for i in range(3):  # 3 массива для примера
                data = np.random.rand(100) * session_idx  # Пример данных
                raw_data.create_dataset(f"Массив{i+1}", data=data)
                raw_data[f"Массив{i+1}"].attrs["description"] = f"Сырые данные #{i+1}"
            
            # Пользовательские графики
            user_plots = session.create_group("UserPlots")
            
            for plot_idx in range(1, 4):  # 3 графика для примера
                plot_name = f"График{plot_idx}"
                plot = user_plots.create_group(plot_name)
                
                # Основные параметры графика
                plot.attrs["name"] = f"График {session_idx}-{plot_idx}"
                plot.attrs["description"] = f"Описание графика {plot_idx}"
                plot.attrs["status"] = "active"
                
                # Данные графика
                data_group = plot.create_group("Data")
                data_group.create_dataset("Массив сырых значений х", data=np.arange(100))
                data_group.create_dataset("Массив сырых значений у", data=np.random.rand(100))
                data_group.create_dataset("Массив актуальных значений х", data=np.linspace(0, 10, 100))
                data_group.create_dataset("Массив актуальных значений у", data=np.sin(np.linspace(0, 10, 100)))
                
                # Стиль графика
                style = plot.create_group("Style")
                style.attrs["color"] = "#FF0000"
                style.attrs["толщина"] = 2.0
                style.attrs["прозрачность"] = 0.8
                style.attrs["значок"] = "circle"
                # ... другие стилевые параметры
                
                # Статистические данные
                stats = plot.create_group("Статистические данные")
                stats.attrs["среднее"] = np.mean(data_group["Массив актуальных значений у"][:])
                stats.attrs["медиана"] = np.median(data_group["Массив актуальных значений у"][:])
                stats.attrs["область определения"] = "[0, 10]"
                stats.attrs["область значений"] = "[-1, 1]"
                # ... другие статистические параметры
                
                # История изменений
                history = plot.create_group("История изменений")
                for hist_idx in range(1, 4):  # 3 записи истории
                    history.attrs[f"Запись{hist_idx}"] = json.dumps({
                        "timestamp": f"2025-07-24T{hist_idx}:00:00Z",
                        "action": f"Действие {hist_idx}",
                        "user": "Имя пользователя"
                    })

# Создаем файл
create_session_file("session.ns")