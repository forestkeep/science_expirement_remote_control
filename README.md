# Installation Controller

## Application Description
The application is a software suite for conducting automated experiments using external electronic devices controlled through various digital interfaces, processing received data, and constructing dependencies. It is developed in Python and is available for free. The application's interface is graphical, intuitive, and allows for convenient management of experimental processes, including device configuration and procedure building.
The application supports the possibility of flexible configuration of device interaction scenarios. The user can define the order of data collection, send control commands, and sequence the actions of devices. All settings of the experimental procedure are displayed as an interactive diagram, showing the signal flows and interactions between devices.
During the experiment, the results are available in the form of graphs. After the experiment is completed, the data can be processed using built-in filters and saved in various formats.

![Image alt](https://github.com/forestkeep/some_picture/blob/main/installation_controller/running_results.gif)

### Devices Configuration:
The application automatically scans available interfaces, eliminating the need for manual port search and entry.
When configuring devices, the analysis for collisions and errors in port assignments is conducted. The experiment is only possible after successful configuration completion.
A built-in module for creating new devices is available. The user can set up the command system of a new device and test it using a dialog interface. All necessary tools for this are integrated into the application.
Interaction and Control of Devices:
The working scenarios are based on the concept of signals: devices perform actions upon receiving the corresponding signal. Signals can come from timers or other devices.
The user can configure error handling for devices – for example, choose to continue the experiment in case of a failure or to interrupt it.
At any moment during the experiment, there is an option to pause it.

### Experiment Execution:
- The current status of the process is displayed in text format.
- A visual gauge shows the remaining time until the experiment's completion in minutes and percentages.
- Measured parameters are displayed in real-time on an interactive graph. The list of displayed data can be customized as desired.
- As operations are performed, diagrams with metadata about device actions are generated. If any device stops responding, the user is immediately notified.
- 
### Additional Features:
- A built-in mathematical toolkit allows for calculations and the construction of dependencies between parameters.
- The obtained data is automatically recorded in a file in case of power outages or computer malfunctions. This ensures the preservation of all information.
- Upon completing the experiment, the program will provide several options for data export: for example, they can be saved in Excel table format.
- 
### Miscellaneous
The application includes a built-in module for viewing and processing experiment results. Data obtained from devices can not only be recorded in a file but also analyzed within the program. Additionally, users can import their own data for analysis within the module. Configured experimental setups can be saved and loaded as needed, eliminating the need to reconfigure all similar experiments.
The application supports two languages: Russian and English. The user can select the appropriate language in the settings.

## Application Installation
## Windows:
1. Download the application installation file .exe;
2. Run the installation file. Double-click on the downloaded file to begin the installation process;
3. Follow the prompts of the installation wizard. During the installation process, you will be offered standard steps, including:
    - Accepting the license agreement
    - Choosing the installation directory
    - Installing additional components (if prompted)
4. Upon completion of the installation process, you will receive a notification about its successful completion. Now the application is ready for use.

## Описание приложения
Приложение представляет собой программный комплекс для проведения автоматизированных экспериментов с использованием внешних электронных приборов, управляемых через различные цифровые интерфейсы, обработки получаемых данных и построения зависимостей.
 Оно разработано на языке программирования Python и распространяется бесплатно. Интерфейс приложения является графическим, интуитивно понятным и позволяет удобно управлять процессами эксперимента, включая настройку приборов и построение процедур.
Приложение поддерживает возможность гибкой настройки сценариев взаимодействия приборов. Пользователь может определить порядок снятия данных, отправку команд управления и последовательность действий устройств. Все настройки процедуры эксперимента отображаются в виде интерактивной диаграммы, на которой показаны потоки сигналов и взаимодействия между приборами. Во время проведения эксперимента пользователю доступен вывод результатов в виде графиков. После окончания эксперимента данные можно обработать с помощью встроенных фильтров и сохранить в различных форматах.

### Настройка приборов:
- Приложение автоматически сканирует доступные интерфейсы, что устраняет необходимость ручного поиска и ввода портов.
- При задании конфигурации приборов проводится анализ на наличие коллизий и ошибок при назначении портов. Эксперимент возможен только после корректного завершения настройки.
- Встроен модуль для создания новых приборов. Пользователь с помощью диалогового интерфейса может настроить систему команд нового устройства и протестировать их. Все необходимые инструменты для этого интегрированы в приложение.
  
### Взаимодействие и управление приборами:
- Сценарии работы основываются на концепции сигналов: приборы выполняют действие при получении соответствующего сигнала. Сигналы могут поступать от таймеров или других приборов.
- Пользователь может настроить обработку ошибок приборов – например, выбрать, продолжать эксперимент при сбое или же прерывать его.
- В любой момент эксперимента есть возможность поставить его на паузу.
- 
### Ход выполнения эксперимента:
- Текущий статус процесса отображается в текстовом формате.
- Визуальная шкала показывает оставшееся время до завершения эксперимента в минутах и процентах.
- В реальном времени измеряемые параметры выводятся на интерактивный график. Перечень отображаемых данных можно настроить по желанию.
- По мере выполнения операций генерируются диаграммы с метаданными о действиях приборов. Если какое-либо устройство перестает отвечать, об этом немедленно уведомляется пользователь.

### Дополнительные функции:
- Встроенный математический аппарат позволяет выполнять расчеты и строить зависимости одних параметров от других.
- Полученные данные автоматически записываются в файл на случай отключения электричества или сбоя работы компьютера. Это обеспечивает сохранность всей информации.
- По завершении эксперимента программа предоставит несколько вариантов экспорта данных: например, их можно сохранить в формате таблиц Excel. 

### Прочее
Приложение включает встроенный модуль для просмотра и обработки результатов эксперимента. Данные, полученные от приборов, могут быть не только записаны в файл, но также проанализированы внутри программы. Дополнительно пользователь может импортировать собственные данные для работы с ними в модуле анализа. 
Настроенные конфигурации эксперимента можно сохранять и загружать по мере необходимости, что избавляет от необходимости повторной настройки всех аналогичных экспериментов.
Приложение поддерживает два языка: русский и английский. Пользователь может выбрать подходящий язык в настройках.

## Установка приложения 
### Windows:
1.	Скачайте установочный файл приложения .exe;
2.	Запустите установочный файл. Дважды щелкните на загруженный файл, чтобы начать процесс установки;
3.	Следуйте подсказкам мастера установки. В процессе установки вам будут предложены стандартные шаги, включая:
    - Принятие лицензионного соглашения
    - Выбор каталога установки
    - Установка дополнительных компонентов (если предлагается)
4.	После завершения процесса установки вы получите уведомление о его успешном завершении.
Теперь приложение готово к использованию.

# Скриншоты приложения

## Диаграмма взаимодействия приборов
![Image alt](https://github.com/forestkeep/some_picture/blob/main/installation_controller/diagram_devices.JPG)

## Отображения осциллограммы
![Image alt](https://github.com/forestkeep/some_picture/blob/main/installation_controller/oscillogramm.JPG)

## Предупреждение о том, что некоторые приборы не могут иметь один и тот же интерфейс подключения
![Image alt](https://github.com/forestkeep/some_picture/blob/main/installation_controller/warning%20settings.JPG)

## Этап создания нового прибора
![Image alt](https://github.com/forestkeep/some_picture/blob/main/installation_controller/creating_new_device.JPG)


