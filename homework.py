import logging
import os
import time

from typing import Optional

import requests
import telegram

from dotenv import load_dotenv

from exceptions import MissingEnvironmentVariable

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot: telegram.Bot, message: str) -> None:
    """Отправляет сообщение в телеграм чат."""
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)


def get_api_answer(current_timestamp: int) -> Optional[dict]:
    """Делает запрос к API сервиса Практикум.Домашка."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        hw_status = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if hw_status.status_code == 200:
            return hw_status.json()
    except Exception as e:
        pass


def check_response(response: dict) -> list:
    """Проверяет ответ API на корректность."""
    if response is None:
        return []
    return response.get('homeworks')


def parse_status(homework: dict) -> str:
    """Извлекает из информации(homework: dict) статус работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """Проверяет доступность переменных окружения, которые необходимы
    для работы программы. Если отсутствует хотя бы одна
    переменная окружения — функция должна вернуть False, иначе — True.
    """
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def main() -> None:
    """Основная логика работы бота."""
    if not check_tokens():
        raise MissingEnvironmentVariable

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    homeworks = []
    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_homeworks = check_response(response=response)
            if current_homeworks != homeworks:
                bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID,
                    text=parse_status(current_homeworks[0])
                )
            homeworks = current_homeworks
            current_timestamp += RETRY_TIME
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            print(message)
            time.sleep(RETRY_TIME)
        else:
            pass


if __name__ == '__main__':
    main()
