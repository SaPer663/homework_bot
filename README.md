
# Телеграм бот на Python
### Описание
Это учебный проект, сдланный для знакомства с работой API.
- программа делает запрос к API сервиса Практикум.Домашка и проверяет статус отправленной на ревью домашней работы;
- при обновлении статуса анализирует ответ API и отправляет соответствующее уведомление в Telegram;
### Технологии
- [`python-telegram-bot`](https://github.com/python-telegram-bot/python-telegram-bot) для отправления уведомлений в телеграм чат
- [`poetry`](https://github.com/python-poetry/poetry) для управления зависимостями
- [`mypy`](https://mypy.readthedocs.io) для статической типизации
- [`pytest`](https://pytest.org/)  для юнит тестов
- [`flake8`](http://flake8.pycqa.org/en/latest/) линтер
### Запуск проекта в dev-режиме
- установите и активируйте виртуальное окружение
- установите зависимости из файла requirements.txt
```
pip install -r requirements.txt
``` 
- или в poetry 
```
poetry install
```
- в корневой директории выполните команду:
```
python homework.py
``` 
### Авторы
Александр @saper663 
