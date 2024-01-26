import os
import time
import logging
import sys

import requests
import telegram
from dotenv import load_dotenv
from http import HTTPStatus

from exceptions import NoAnswerFromEndpointError

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность переменных окружения."""
    error_msg = None
    if not PRACTICUM_TOKEN:
        error_msg = 'Отсутствует переменная окружения PRACTICUM_TOKEN'
    if not TELEGRAM_TOKEN:
        error_msg = 'Отсутствует переменная окружения TELEGRAM_TOKEN'
    if not TELEGRAM_CHAT_ID:
        error_msg = 'Отсутствует переменная окружения TELEGRAM_CHAT_ID'
    if error_msg:
        logging.critical(error_msg)
        sys.exit()


def send_message(bot, message):
    """Отправляет сообщение в телеграмм чат с ID из переменной окружения."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug('Сообщение успешно отправлено')
    except telegram.TelegramError:
        logging.error('Ошибка при отправке сообщения')


def get_api_answer(timestamp):
    """Запрос к API сервиса Практикум.Домашка."""
    payload = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(url=ENDPOINT,
                                         headers=HEADERS,
                                         params=payload,)
    except requests.RequestException:
        logging.error('Сбой при запросе к эндпоинту')
    if homework_statuses.status_code == HTTPStatus.OK:
        return homework_statuses.json()
    else:
        logging.error('Нет ответа от эндпоинта')
        raise NoAnswerFromEndpointError


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        error_msg = 'Ответ не являтся словарем'
        logging.error(error_msg)
        raise TypeError(error_msg)
    if 'homeworks' not in response:
        error_msg = 'Ответ не содержит в себе ключ homeworks'
        logging.error(error_msg)
        raise KeyError(error_msg)
    if 'current_date' not in response:
        error_msg = 'Ответ не содержит в себе ключ current_date'
        logging.error(error_msg)
        raise KeyError(error_msg)
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        error_msg = 'Значение под ключом homeworks не является списком'
        logging.error(error_msg)
        raise TypeError(error_msg)
    return True


def parse_status(homework):
    """Извлекает из словаря конкретной домашней работы статус этой работы."""
    if 'status' not in homework:
        error_msg = 'Ответ не содержит в себе ключ status'
        logging.error(error_msg)
        raise KeyError(error_msg)
    if 'homework_name' not in homework:
        error_msg = 'Ответ не содержит в себе ключ homework_name'
        logging.error(error_msg)
        raise KeyError(error_msg)
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        error_msg = 'Недокументированный статус домашней работы'
        logging.error(error_msg)
        raise ValueError(error_msg)
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    check_tokens()
    homeworks = []
    while True:
        try:
            response = get_api_answer(timestamp)
            if check_response(response):
                new_homeworks = response.get('homeworks')
                if new_homeworks != homeworks:
                    send_message(bot, parse_status(new_homeworks[0]))
                    homeworks = new_homeworks
                else:
                    logging.debug('Изменений в статусе дз нет')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,
                        encoding='utf-8',
                        format='%(asctime)s, %(levelname)s, %(message)s',
                        handlers=[logging.StreamHandler(sys.stdout)])
    main()
