import datetime
import logging
import sys
import time

from logging import StreamHandler
from typing import Dict, List, Optional, Union

import pytz
import requests
import telegram

from requests import exceptions

import constants

from exceptions import MissingEnvironmentVariable, ResponseStatusIsNotOK


def get_logger():
    """Возвращает настроенный логгер."""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    handler = StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )
    logging.Formatter.converter = (
        lambda *args: datetime.datetime.now(
            tz=pytz.timezone(constants.TIMEZONE)
        ).timetuple()
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


logger = get_logger()


def send_message(bot: telegram.Bot, message: str) -> None:
    """Отправляет сообщение в телеграм чат."""
    try:
        bot.send_message(chat_id=constants.TELEGRAM_CHAT_ID, text=message)
        logger.info('Сообщение отправлено в чат')
    except Exception as e:
        logger.error(f'Неудалось отправить сообщение, ошибка: {e}')


def get_api_answer(current_timestamp: int) -> Dict[str, Union(list, int)]:
    """Делает запрос к API сервиса Практикум.Домашка."""
    timestamp: int = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        hw_status = requests.get(
            constants.ENDPOINT,
            headers=constants.HEADERS,
            params=params
        )
        if hw_status.status_code != 200:
            raise ResponseStatusIsNotOK(
                f'Статус код ответа от API {hw_status.status_code}'
            )
        return hw_status.json()
    except ResponseStatusIsNotOK:
        logger.error(f'Статус код ответа от API {hw_status.status_code}')
        raise ResponseStatusIsNotOK(
            f'Статус код ответа от API {hw_status.status_code}'
        )
    except exceptions.JSONDecodeError:
        logger.error('Не удалось декодировать в json.')
        raise exceptions.JSONDecodeError('Не удалось декодировать в json.')
    except requests.exceptions.HTTPError as HTTPError:
        status_code = hw_status.status_code
        logger.error(f'Эндпоинт недоступен, ошибка: {HTTPError} {status_code}')
        raise HTTPError(
            f'Эндпоинт недоступен, ошибка: {HTTPError} {status_code}'
        )
    except exceptions.ConnectionError as ConnectionError:
        logger.error(f'Эндпоинт недоступен, ошибка: {ConnectionError}')
        raise ConnectionError(
            f'Эндпоинт недоступен, ошибка: {ConnectionError}'
        )
    except exceptions.RequestException as RequestException:
        logger.error(f'Эндпоинт недоступен, ошибка: {RequestException}')
        raise RequestException(
            f'Эндпоинт недоступен, ошибка: {RequestException}'
        )


def check_response(
    response: Dict[str, Union(list, int)]
) -> List[Dict[str, Union(list, int)]]:
    """Проверяет ответ API на корректность."""
    if not response or isinstance(response, dict):
        raise TypeError('В ответе API ничего нет или это не словарь')
    homeworks: Optional(list) = response.get('homeworks')
    current_date: Optional(int) = response.get('current_date')
    if homeworks is None or current_date is None:
        raise TypeError('В ответе API нет ключей `homeworks` и `current_date`')
    if isinstance(homeworks, list) or isinstance(current_date, int):
        raise TypeError(
            'В ответе API не ожидаемые типы значений '
            'ключей `homeworks` и `current_date`'
        )
    return homeworks


def parse_status(homework: Dict[str, Union(list, int)]) -> str:
    """Извлекает из информации(homework: dict) статус работы."""
    homework_name: Optional(str) = homework.get('homework_name')
    homework_status: Optional(str) = homework.get('status')
    if homework_status not in constants.HOMEWORK_STATUSES:
        raise KeyError(
            f'{homework_status} - недокументированный или отсутствует '
            'статус домашней работы '
        )
    verdict: Optional(str) = constants.HOMEWORK_STATUSES.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """Проверяет доступность необходимых переменных окружения.
    Если отсутствует хотя бы одна переменная окружения — функция должна
    вернуть False, иначе — True.
    """
    variables: Dict[str, Union(str, int)] = {
        'PRACTICUM_TOKEN': constants.PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': constants.TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': constants.TELEGRAM_CHAT_ID
    }
    for key, value in variables.items():
        if value is None:
            logger.critical(
                f'Отсутствует обязательная переменная окружения: {key}')
    return all(variables.values())


def main() -> None:
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical(
            'Отсутствуют обязательные переменные окружения. '
            'Программа принудительно остановлена.')
        raise MissingEnvironmentVariable

    logger.info('Программа работает')

    bot = telegram.Bot(token=constants.TELEGRAM_TOKEN)
    current_timestamp: int = int(time.time())
    submitted_error: str = ''
    while True:
        try:
            type_response = Dict[str, Union(list, int)]
            response: type_response = get_api_answer(current_timestamp)
            current_homeworks: list = check_response(response=response)

            if current_homeworks:
                homework_status: str = parse_status(current_homeworks[0])
            if current_homeworks:
                send_message(bot=bot, message=homework_status)
            else:
                logger.debug('Статус не обновился')
            current_timestamp = response['current_date']
            submitted_error = ''

        except Exception as error:
            message: str = f'Сбой в работе программы: {error}'
            logger.error(message)
            if message != submitted_error:
                send_message(bot=bot, message=message)
                submitted_error = message
        finally:
            time.sleep(constants.RETRY_TIME)


if __name__ == '__main__':
    main()
