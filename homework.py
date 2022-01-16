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
logger.setLevel(logging.DEBUG)
handler = StreamHandler(sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def send_message(bot: telegram.Bot, message: str) -> None:
    """Отправляет сообщение в телеграм чат."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as e:
        logger.error(f'Неудалось отправить сообщение, ошибка: {e}')
    else:
        logger.info('Сообщение отправлено в чат')


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
    """Проверяет доступность необходимых переменных окружения.
    Если отсутствует хотя бы одна переменная окружения — функция должна
    вернуть False, иначе — True.
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
    if not check_tokens():
        return

    logger.info('Программа работает')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    homeworks = []
    message_cache = []
    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_homeworks = check_response(response=response)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if message not in message_cache:
                send_message(bot=bot, message=message)
                message_cache.append(message)
            time.sleep(RETRY_TIME)
        else:
            if current_homeworks != homeworks:
                message = parse_status(current_homeworks[0])
                send_message(bot=bot, message=message)
                homeworks = current_homeworks
            else:
                logger.debug('Статус не обновился')
            current_timestamp = response['current_date']
            time.sleep(RETRY_TIME)
            message_cache.clear()


if __name__ == '__main__':
    main()
