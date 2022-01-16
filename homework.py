import logging
import os
import sys
import time

from logging import StreamHandler

import requests
import telegram

from dotenv import load_dotenv

from exceptions import ResponseStatusIsNotOK

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

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = StreamHandler(sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def send_message(bot: telegram.Bot, message: str) -> None:
    """Отправляет сообщение в телеграм чат."""
    logger.info(f'Сообщение отправлено в чат {TELEGRAM_CHAT_ID}')
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)


def get_api_answer(current_timestamp: int) -> dict:
    """Делает запрос к API сервиса Практикум.Домашка."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        hw_status = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception as e:
        logger.error(f'Неудалось получить ответ от API {e}')
    else:
        if hw_status.status_code != 200:
            raise ResponseStatusIsNotOK(
                f'Статус код ответа от API {hw_status.status_code}'
            )
        return hw_status.json()


def check_response(response: dict) -> list:
    """Проверяет ответ API на корректность."""
    homeworks = response['homeworks']
    current_date = response['current_date']
    if type(homeworks) != list or type(current_date) != int:
        raise TypeError('Недокументированный ответ от API')
    if homeworks:
        if type(homeworks[0]) != dict:
            raise TypeError('Недокументированный ответ от API')
        for item in ('id', 'status',
                     'homework_name', 'reviewer_comment',
                     'date_updated', 'lesson_name'):
            if item not in homeworks[0]:
                raise TypeError('Недокументированный ответ от API')
    return homeworks


def parse_status(homework: dict) -> str:
    """Извлекает из информации(homework: dict) статус работы."""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        raise KeyError(
            f'{homework_status} - недокументированный или отсутствует '
            'статус домашней работы '
        )
    verdict = HOMEWORK_STATUSES.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """Проверяет доступность переменных окружения, которые необходимы
    для работы программы. Если отсутствует хотя бы одна
    переменная окружения — функция должна вернуть False, иначе — True.
    """
    variables = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    missing = []
    for key, value in variables.items():
        if not value:
            missing.append(key)
    if missing:
        logger.critical(
            'Отсутствуют обязательные переменные окружения: '
            f'{missing}. Программа принудительно остановлена.')
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def main() -> None:
    """Основная логика работы бота."""
    logger.info('Программа работает')
    if not check_tokens():
        return

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    homeworks = []
    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_homeworks = check_response(response=response)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            time.sleep(RETRY_TIME)
        else:
            if current_homeworks != homeworks:
                bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID,
                    text=parse_status(current_homeworks[0])
                )
                homeworks = current_homeworks
            current_timestamp += RETRY_TIME
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
