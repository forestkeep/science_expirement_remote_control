def read_session_file(filename):
    with h5py.File(filename, 'r') as f:
        # Читаем мета-информацию
        print(f"Формат файла: {f.attrs['file_format']}")
        print(f"Создан: {f.attrs['created']}")
        
        # Перебираем все сессии
        for session_name in f:
            if not isinstance(f[session_name], h5py.Group):
                continue
                
            session = f[session_name]
            print(f"\n--- {session_name} ---")
            
            # Параметры сессии
            params = session["Parameters"]
            print(f"Название: {params.attrs['name']}")
            print(f"Описание: {params.attrs['description']}")
            
            # Настройки полей
            field_settings = session["FieldSettings"]
            plot_field = field_settings["PlotField"]
            print(f"Цвет поля графиков: {plot_field.attrs['background_color']}")
            
            # Сырые данные
            raw_data = session["RawData"]
            print(f"\nСырые данные ({len(raw_data)} массивов):")
            for ds_name in raw_data:
                dataset = raw_data[ds_name]
                print(f"  - {ds_name}: {len(dataset)} значений")
            
            # Пользовательские графики
            user_plots = session["UserPlots"]
            print(f"\nГрафики ({len(user_plots)}):")
            
            for plot_name in user_plots:
                plot = user_plots[plot_name]
                print(f"\n  График: {plot.attrs['name']}")
                
                # Данные графика
                data_group = plot["Data"]
                print("  Данные:")
                for ds_name in data_group:
                    dataset = data_group[ds_name]
                    print(f"    - {ds_name}: {len(dataset)} значений")
                
                # Стиль
                style = plot["Style"]
                print(f"  Стиль: цвет={style.attrs['color']}, толщина={style.attrs['толщина']}")
                
                # Статистика
                stats = plot["Статистические данные"]
                print(f"  Статистика: среднее={stats.attrs['среднее']:.4f}")
                
                # История изменений
                history = plot["История изменений"]
                print("  История изменений:")
                for attr_name in history.attrs:
                    record = json.loads(history.attrs[attr_name])
                    print(f"    - {attr_name}: {record['action']} в {record['timestamp']}")

# Читаем файл
read_session_file("session.ns")