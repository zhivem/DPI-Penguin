# DPI Penguin [YouTube + Discord]

<img src="https://github.com/zhivem/DPI-Penguin/blob/main/resources/icon/newicon.ico" width=10% height=10%>

[![en](https://img.shields.io/badge/lang-en-red.svg)](./README.EN.md)
[![ru](https://img.shields.io/badge/lang-ru-green.svg)](./README.md)

**DPI Penguin** — это графическое приложение на Python, разработанное для обхода сетевых ограничений, таких как глубокий анализ пакетов (DPI). Приложение предоставляет интуитивно понятный интерфейс для управления скриптами, позволяющими получать доступ к платформам таким как YouTube и Discord. Работа приложения основана на интеграции с [Zapret](https://github.com/bol-van/zapret). Загрузить `exe` можно c [Releases](https://github.com/zhivem/DPI-Penguin/releases). Посмотреть исходный код загрузчика обновлений `->` [LoaderPenguin
](https://github.com/zhivem/LoaderPenguin)

> [!NOTE]
>Также доступна альтернативная версия — [TrayPenguinDPI](https://github.com/zhivem/TrayPenguinDPI), написанная на `C#` для Windows. Она работает из системного трея, поддерживает тёмную и светлую темы и обеспечивает удобный способ обхода DPI-фильтрации.

## Интерфейс
![image](https://github.com/user-attachments/assets/7dc2072c-fcd7-4c86-b362-2bd4ebed6ac6)

## Особенности

- **Удобный интерфейс:** Создан с использованием PyQt6 для отзывчивого и интуитивно понятного взаимодействия.
- **Управление процессами:** Легко запускать, останавливать и управлять скриптами для обхода сетевых ограничений.
- **Интеграция с системным треем:** Свертывайте приложение в системный трей для бесперебойной фоновой работы.
- **Настройка автозапуска:** Опция автоматического запуска приложения при старте системы.
- **Управление конфигурацией:** Обновляйте и перезагружайте файлы конфигурации непосредственно из интерфейса.
- **Поддержка тем:** Переключение между светлой и тёмной темами в соответствии с вашими предпочтениями.
- **Автоматические обновления:** Проверка и применение обновлений для обеспечения наличия последних функций.
- **Логирование:** Полное логирование для помощи в устранении неполадок и мониторинге поведения приложения.
- **DNS и Прокси:**
  - **Прокси:** Приложение позволяет настроить, проверить и применить прокси-серверы (`HTTP`, `HTTPS`, `SOCKS4`, `SOCKS5`) для всей системы. Также можно сбросить настройки прокси.
  - **DNS:** Поддержка популярных публичных DNS-серверов (`Google`, `Cloudflare`, `AdGuard`, `Comss`). Пользователь может выбрать интерфейс и применить выбранный DNS для улучшения скорости или безопасности интернета.
  - **Преимущества:** Изменение прокси и DNS помогает обходить блокировки, ускоряет соединение и повышает безопасность.

## Конфигурация настройки

Приложение использует файл `default.ini`, расположенный в папке `config`. Этот файл содержит настройки для различных скриптов и параметров работы приложения. Вы можете редактировать этот файл вручную и добавлять свои конфигурации.

### Путь к исполняемым файлам должны оставаться как есть 

```py
{ZAPRET_FOLDER}\winws.exe
{ZAPRET_FOLDER}\quic_initial_www_google_com.bin 
{ZAPRET_FOLDER}\tls_clienthello_www_google_com.bin
{ZAPRET_FOLDER}\tls_clienthello_iana_org.bin
```

### Путь к черным спискам должны оставаться как есть 

```py
 "russia-blacklist.txt" - {BLACKLIST_FILES_0}
 "disk-youtube-blacklist.txt" - {BLACKLIST_FILES_1}
 "universal.txt" - {BLACKLIST_FILES_2}
 "ipset-discord.txt" - {BLACKLIST_FOLDER}\ipset-discord.txt
 "autohostlist.txt" - {BLACKLIST_FOLDER}\autohostlist.txt 
 "{GAME_FILTER}" - игровой фильтр
```
### Пример конфига DiscordFix

```py
[Пример названия]
executable = {ZAPRET_FOLDER}\winws.exe
args =
    --wf-tcp=80,443,{GAME_FILTER};
    --wf-udp=443,50000-50100,{GAME_FILTER};
    --filter-udp=443;
    --hostlist={BLACKLIST_FILES_2};
    --dpi-desync=fake;
    --dpi-desync-repeats=11;
    --dpi-desync-fake-quic={ZAPRET_FOLDER}\quic_initial_www_google_com.bin;
    --new;
    --filter-udp=50000-50100;
    --filter-l7=discord,stun;
    --dpi-desync=fake;
    --dpi-desync-repeats=6;
    --new;
    --filter-tcp=80;
    --hostlist={BLACKLIST_FILES_2};
    --dpi-desync=fake,fakedsplit;
    --dpi-desync-autottl=2;
    --dpi-desync-fooling=md5sig;
    --new;
    --filter-tcp=443;
    --hostlist={BLACKLIST_FILES_2};
    --dpi-desync=fake,fakedsplit;
    --dpi-desync-split-pos=1;
    --dpi-desync-autottl;
    --dpi-desync-fooling=badseq;
    --dpi-desync-repeats=8;
    --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com;
    --new;
    --filter-udp=443;
    --ipset={BLACKLIST_FOLDER}\ipset-discord.txt;
    --dpi-desync=fake;
    --dpi-desync-repeats=11;
    --dpi-desync-fake-quic={ZAPRET_FOLDER}\quic_initial_www_google_com.bin;
    --new;
    --filter-tcp=80;
    --ipset={BLACKLIST_FOLDER}\ipset-discord.txt;
    --dpi-desync=fake,fakedsplit;
    --dpi-desync-autottl=2;
    --dpi-desync-fooling=md5sig;
    --new;
    --filter-tcp=443,{GAME_FILTER};
    --ipset={BLACKLIST_FOLDER}\ipset-discord.txt;
    --dpi-desync=fake,fakedsplit;
    --dpi-desync-split-pos=1;
    --dpi-desync-autottl;
    --dpi-desync-fooling=badseq;
    --dpi-desync-repeats=8;
    --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com;
    --new;
    --filter-udp={GAME_FILTER};
    --ipset={BLACKLIST_FOLDER}\ipset-discord.txt;
    --dpi-desync=fake;
    --dpi-desync-autottl=2;
    --dpi-desync-repeats=10;
    --dpi-desync-any-protocol=1;
    --dpi-desync-fake-unknown-udp={ZAPRET_FOLDER}\quic_initial_www_google_com.bin;
    --dpi-desync-cutoff=n2;
```
### Дополнительные файлы конфигурации

В архиве с программой лежат конфигурации которые вы можете использовать вместо обычных `default.ini`. Чтобы открыть папку с конфигурациями нажмите кнопку `Открыть configs`.

### Возможные ошибки

- Если не нажимается кнопка запустить, значит ошибка в конфигурации, в текстовом поле должна отобразиться ошибка.
- Одинаковые названия для конфигураций не допустимы, иначе программа выдаст ошибку.

## Использование тем

Можете редактировать в папке `.._internal\resources\styles` файлы с расширением `.qss` под свои нужды, если кому не нравится стандартный интерфейс программы.
```py
dark_theme.qss - темный интерфейс
light_theme.qss - светлый интерфейс
```

## Установка

Для тех кто не хочет собирать свой проект и вносить в него изменения можете загрузить архив с вкладки [Releases](https://github.com/zhivem/DPI-Penguin/releases), а кто хочет собрать свой:

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
- **Flowseal:** Сборка для работы Discord и YouTube. Разработчик: Flowseal. [Репозиторий](https://github.com/Flowseal/zapret-discord-youtube)

## Лицензия 

MIT License. Подробнее в файле [LICENSE](https://github.com/zhivem/DPI-Penguin/raw/refs/heads/main/LICENSE).

