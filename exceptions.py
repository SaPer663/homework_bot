class ResponseStatusIsNotOK(Exception):
    """Статус ответа сервера отличный от `OК`."""


class MissingEnvironmentVariable(Exception):
    """Отсутствует переменная окружения."""
