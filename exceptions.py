class MissingEnvironmentVariable(Exception):
    """Отсутствует переменная окружения."""


class ResponseStatusIsNotOK(Exception):
    """Статус ответа сервера отличный от `OК`."""
