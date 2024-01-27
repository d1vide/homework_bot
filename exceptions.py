class WrongAnswerFromEndpointError(Exception):
    """Исключение вызываемое когда ответ от эндпоинта неверный."""

    pass


class RequestException(Exception):
    """Исключение вызываемое при сбое запроса к эндпоинту."""

    pass
