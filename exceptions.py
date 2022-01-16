class MissingEnvironmentVariable(Exception):
    """Отсутствует переменная окружения."""


class NotOKStatusResponse(Exception):
    """Статус ответа сервера отличный от `OК`."""
