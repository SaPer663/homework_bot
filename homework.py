import logging
import os
import sys
import time

from logging import StreamHandler

import requests
import telegram

from dotenv import load_dotenv

import constants

from exceptions import MissingEnvironmentVariable, ResponseStatusIsNotOK

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


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
        bot.send_message(chat_id=constants.TELEGRAM_CHAT_ID, text=message)
    except Exception as e:
        logger.error(f'Неудалось отправить сообщение, ошибка: {e}')
    else:
        logger.info('Сообщение отправлено в чат')


def get_api_answer(current_timestamp: int) -> dict:
    """Делает запрос к API сервиса Практикум.Домашка."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        hw_status = requests.get(
            constants.ENDPOINT,
            headers=constants.HEADERS,
            params=params
        )
    except Exception as e:
        logger.error(f'Неудалось получить ответ от API {e}')
    else:
        if hw_status.status_code != 200:
            raise ResponseStatusIsNotOK(
                f'Статус код ответа от API {hw_status.status_code}'
            )
        try:
            return hw_status.json()
        except Exception as e:
            logger.error(f'Неудалось декодировать в json ответ от API {e}')
            return {}


def check_response(response: dict) -> list:
    """Проверяет ответ API на корректность."""
    if not response or type(response) != dict:
        raise TypeError('Недокументированный ответ от API')
    homeworks = response.get('homeworks')
    current_date = response.get('current_date')
    if not homeworks or not current_date:
        raise TypeError('Недокументированный ответ от API')
    if type(homeworks) != list or type(current_date) != int:
        raise TypeError('Недокументированный ответ от API')
    return homeworks


def parse_status(homework: dict) -> str:
    """Извлекает из информации(homework: dict) статус работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in constants.HOMEWORK_STATUSES:
        raise KeyError(
            f'{homework_status} - недокументированный или отсутствует '
            'статус домашней работы '
        )
    verdict = constants.HOMEWORK_STATUSES.get(homework_status)
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
        raise MissingEnvironmentVariable

    logger.info('Программа работает')

    bot = telegram.Bot(token=constants.TELEGRAM_TOKEN)
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
            time.sleep(constants.RETRY_TIME)
        else:
            if current_homeworks != homeworks:
                message = parse_status(current_homeworks[0])
                send_message(bot=bot, message=message)
                homeworks = current_homeworks
            else:
                logger.debug('Статус не обновился')
            current_timestamp = response['current_date']
            time.sleep(constants.RETRY_TIME)
            message_cache.clear()


if __name__ == '__main__':
    main()
