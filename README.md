# DPI Penguin [YouTube + Discord]

![Логотип DPI Penguin](resources/icon/newicon.ico)

**DPI Penguin** — это графическое приложение на Python, разработанное для обхода сетевых ограничений, таких как глубокий анализ пакетов (DPI). Приложение предоставляет интуитивно понятный интерфейс для управления скриптами, позволяющими получать доступ к платформам таким как YouTube и Discord. Работа приложения основана на интеграции с [Zapret](https://github.com/bol-van/zapret) и [GoodbyeDPI](https://github.com/ValdikSS/GoodbyeDPI). Загрузить `exe` можно c [Releases](https://github.com/zhivem/DPI-Penguin/releases)

![image](https://github.com/user-attachments/assets/c431c993-0f60-46d7-bcc9-bd75a4479e4f)
![image](https://github.com/user-attachments/assets/7568e004-110f-4168-b231-cd4ee4679efc)

## Особенности

- **Удобный интерфейс:** Создан с использованием PyQt6 для отзывчивого и интуитивно понятного взаимодействия.
- **Управление процессами:** Легко запускать, останавливать и управлять скриптами для обхода сетевых ограничений.
- **Интеграция с системным треем:** Свертывайте приложение в системный трей для бесперебойной фоновой работы.
- **Настройка автозапуска:** Опция автоматического запуска приложения при старте системы.
- **Мониторинг статуса сайтов:** Отслеживайте доступность ключевых веб-сайтов, таких как YouTube и Discord.
- **Управление конфигурацией:** Обновляйте и перезагружайте файлы конфигурации непосредственно из интерфейса.
- **Поддержка тем:** Переключение между светлой и тёмной темами в соответствии с вашими предпочтениями.
- **Автоматические обновления:** Проверка и применение обновлений для обеспечения наличия последних функций и патчей безопасности.
- **Логирование:** Полное логирование для помощи в устранении неполадок и мониторинге поведения приложения.

## Конфигурация настройки

Приложение использует файл `default.ini`, расположенный в директории `config`. Этот файл содержит настройки для различных скриптов и параметров работы приложения. Вы можете редактировать этот файл вручную и добавлять свои конфигурации. Пример на основе `DiscordFix`:

### Путь к исполняемым файлам должны оставаться как есть 

```py
{ZAPRET_FOLDER}\winws.exe
{BASE_FOLDER}\bin\{architecture}\goodbyedpi.exe
{ZAPRET_FOLDER}\quic_initial_www_google_com.bin 
{ZAPRET_FOLDER}\tls_clienthello_www_google_com.bin
```
### Путь к черным спискам должны оставаться как есть 

```py
 "russia-blacklist.txt" - {BLACKLIST_FILES_0}
 "russia-youtube.txt" - {BLACKLIST_FILES_1}
 "discord-blacklist.txt" -{BLACKLIST_FILES_2}
 "disk-youtube.txt" - {BLACKLIST_FILES_3}
```
### Пример конфига DiscordFix

```py
[DiscordFix]  | Название секции, называйте как хотите
executable = {ZAPRET_FOLDER}\winws.exe либо goodbyedpi.exe  | Путь к исполняемому файлу для обхода блокировок
args = 
    --wf-tcp=443;  | Открыть порт TCP 443 (HTTPS)
    --wf-udp=443,50000-65535;  | Открыть порты UDP 443 и диапазон 50000-65535 для использования
    --filter-udp=443; | Фильтрация по UDP-порту 443
    --hostlist={BLACKLIST_FILES_1};  | Список заблокированных доменов {BLACKLIST_FILES_1}
    --dpi-desync=fake;  | Использование метода подделки для обхода DPI
    --dpi-desync-udplen-increment=10;  | Увеличение длины UDP-пакетов на 10 байт
    --dpi-desync-repeats=6;  | Повторить процесс десинхронизации 6 раз
    --dpi-desync-udplen-pattern=0xDEADBEEF;  | Шаблон для изменения длины UDP-пакетов
    --dpi-desync-fake-quic={ZAPRET_FOLDER}\quic_initial_www_google_com.bin;  | Использование поддельного трафика QUIC
    --filter-udp=50000-65535;  | Фильтрация по UDP-портам в диапазоне 50000-65535
    --dpi-desync=fake;  | Повторное использование метода подделки для обхода DPI
    --dpi-desync-any-protocol; | Применение метода десинхронизации ко всем протоколам
    --dpi-desync-cutoff=d3;  | Обрезка данных для дополнительного обхода DPI
    --dpi-desync-repeats=6;  | Повторить десинхронизацию 6 раз
    --dpi-desync-fake-quic={ZAPRET_FOLDER}\quic_initial_www_google_com.bin;  | Повторное использование поддельного QUIC трафика
    --new;  | Начать новый сеанс
    --filter-tcp=443;  | Фильтрация по TCP-порту 443
    --hostlist={BLACKLIST_FILES_1};  | Список заблокированных доменов {BLACKLIST_FILES_1}
    --dpi-desync=fake,split; | Метод подделки и разбиения пакетов для обхода DPI
    --dpi-desync-autottl=2;  | Автоматическое управление TTL (Time to Live)
    --dpi-desync-repeats=6;  | Повторить процесс десинхронизации 6 раз
    --dpi-desync-fooling=badseq; | Обман DPI с помощью неправильной последовательности пакетов
    --dpi-desync-fake-tls={ZAPRET_FOLDER}\tls_clienthello_www_google_com.bin;  // Использование поддельного TLS трафика
```
### Дополнительные файлы конфигурации
```ini
    Default.ini — основной конфигурационный файл. 
    DiscordFix(MGTS).ini — фикс для работы Discord с провайдером МГТС.
    FixDisc+YouTube (Билайн, Ростелеком, Инфолинк).ini — фикс для Discord и YouTube для провайдеров Билайн, Ростелеком, Инфолинк.
    YouTube-new-Fix.ini — дополнительный фикс для YouTube.
```
### Возможные ошибки

- Если не нажимается кнопка запустить, значит ошибка в конфигурации, в текстовом поле должна отобразиться ошибка.
- Одинаковые названия для конфигураций не доспустимы, иначе программа выдаст ошибку.

## Использование тем
Можете редактировать в папке `.._internal\resources\styles` файлы с расширением `.qss` под свои нужды, если кому не нравится стандартный интерфейс программы.
```py
dark_theme.qss - темный интерфейс
light_theme.qss - светлый интерфейс
```

## Установка

Для тех кто не хочет собирать свой проект и вносить в него изменения можете загрузить архив с вкладки [Releases](https://github.com/zhivem/DPI-Penguin/releases), а кто хочет собраться свой:

1. Клонируйте репозиторий:

    ```bash
    git clone https://github.com/zhivem/DPI-Penguin.git 
    ```

2. Установите зависимости:

    ```bash
    pip install -r requirements.txt
    ```

3. Запустите программу:

    ```bash
    python main.py
    ```

## Благодарности
- **GoodbyeDPI:** Основа для работы YouTube. Разработчик: ValdikSS. [Репозиторий](https://github.com/ValdikSS/GoodbyeDPI)
- **Zapret:** Основа для работы Discord и YouTube. Разработчик: bol-van. [Репозиторий](https://github.com/bol-van/zapret)

## Лицензия 
Этот проект лицензирован под [Apache License, Version 2.0.](https://raw.githubusercontent.com/zhivem/DPI-Penguin/refs/heads/main/LICENSE)

