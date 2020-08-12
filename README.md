#Pay for say bot

## Установка python
Для корректной работы работы бота необходимо установить python3.7 и несколько модулей с помощью pip 

Установим python версии 3.7 и pip

```bash
sudo apt update
sudo apt install python3.7
sudo apt-get install python3-setuptools
sudo apt install python3-pip
```

Далее установим необходимые библиотеки

```bash
pip3 install aiogram mysql-connector gspread oauth2client
```

##Настройка
В файле bot.py в переменную API_TOKEN записываем токен бота

Бот использует Google API для работы с Google таблицами и Google диском. Соответственно, вам необходимо в [гугл косоли](https://console.cloud.google.com/home/dashboard) создать новый проект, включить ему Google Sheets API и Google Drive API и получить json файл. В файле будет строка с почтой "client_email": "<имя пользователя>@<имя проекта>.iam.gserviceaccount.com". На эту почту необходимо дать доступ к таблицам PayForSay_Database и logs как редактор. 

В файле functions/work_with_google.py переменные DATABASE_TABLE, LOGS_TABLE и ERROR_LOGS_TABLE это имена документов в которые/из который будет производиться запись. Перепенные host, user. passwd, database, charset отвечают за подключение к бд. В переменную PATH_TO_JSON_FILE необходимо вставить полный путь к json файлу, который вы аолучили от Google. 

В файле functions/sql.py перепенные host, user. passwd, database, charset отвечают за подключение к бд. Переменная HOW_MANY_SCROLLS отвечает за кол-во выводимых на экран событий(по-умолчанию равна 10).

##Запуск

Переходим к настройке systemd. Для этого переходим в его директорию:
```bash
cd /etc/systemd/system
```
И создаём файл bot.service:
```bash
sudo nano bot.service
```
Вписываем в открывшиеся окно следующее:
```bash
[Unit]
Description=Telegram bot 'Pay for say bot'
After=syslog.target
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/название пользователя/название папки в которой лежит бот
ExecStart=/usr/bin/python3 /home/название пользователя/название папки в которой лежит бот/main.py

RestartSec=10
Restart=always

[Install]
WantedBy=multi-user.target
```
Закрываем и соханяем файл. После этого вводим команды:
```bash
sudo systemctl daemon-reload
sudo systemctl enable bot
sudo systemctl start bot
sudo systemctl status bot
```
Теперь бот работает самостоятельно.