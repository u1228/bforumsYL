from requests import Session
from pprint import pprint


s = Session()

URL = "http://bforums.herokuapp.com"

EMAIL = "api-test@email.com"
PASSWORD = "apitestapi"

LOGIN_URL = "/api/v1/login"
LOGIN_DATA = {"email": EMAIL, "password": PASSWORD}
LOGIN_WRONG_LOGIN = {"email": "sdfsdf@dsdf.sdf", "password": "sdfsdfsdf"}
LOGIN_TOO_FEW = {"email": 1}

USER_ME_URL = "/api/v1/user/2"
USER_URL = "/api/v1/user/1"
USER_WRONG_URL = "/api/v1/user/999"
USER_WRONG_STRING_URL = "/api/v1/user/string"

USERS_URL = "/api/v1/users"

EVENTS_URL = "/api/v1/events"

FORUM_URL = "/api/v1/forum/1"
FORUM_WRONG_URL = "/api/v1/forum/999"
FORUM_WRONG_STRING_URL = "/api/v1/forum/string"

FORUMS_URL = "/api/v1/forums"
FORUMS_DATA = {"title": "ApITesT", "private": True, "editors": ""}
FORUMS_TOO_FEW = {"title": False}
FORUMS_WRONG_NICKNAME = {"title": "ApITesT", "private": True, "editors": "sdfsdf"}

MESSAGE_URL = "/api/v1/messages/1"
MESSAGES_URL = "/api/v1/messages/2"
MESSAGES_WRONG_URL = "/api/v1/messages/999"
MESSAGES_WRONG_STRING_URL = "/api/v1/messages/string"
MESSAGES_DATA = {"message": "**test** message."}
MESSAGES_EMPTY = {}
MESSAGES_SECURITY = {"message": '<script>alert("a")</script>'}


def print_response_post(title, url, body):
    print(title)
    result = s.post(URL + url, json=body)
    print("POST", result.url, result.status_code)
    print("Body:")
    pprint(body)
    print("Response:")
    pprint(result.json())
    print("-----------------------------------------")
    print()

def print_response_get(title, url):
    print(title)
    result = s.get(URL + url)
    print("GET", result.url, result.status_code)
    print("Response:")
    pprint(result.json())
    print("-----------------------------------------")
    print()


# Авторизация

print_response_post("Авторизация с неправильным логином и/или паролем:", LOGIN_URL, LOGIN_WRONG_LOGIN)
print_response_post("Авторизация с слишком малым количеством данных:", LOGIN_URL, LOGIN_TOO_FEW)
print_response_post("Авторизация:", LOGIN_URL, LOGIN_DATA)

# Пользователи

print_response_get("Получение информации о нас по индексу:", USER_ME_URL)
print_response_get("Получение информации о другом пользователе по индексу:", USER_URL)
print_response_get("Получение информации о другом пользователе по несуществующему индексу:", USER_WRONG_URL)
print_response_get("Получение информации о другом пользователе по индексу-строке:", USER_WRONG_STRING_URL)

print_response_get("Получение информации о всех пользователях:", USERS_URL)

# Мероприятия

print_response_get("Получение информации о наших мероприятиях:", EVENTS_URL)

# Форумы

print_response_get("Получение информации о форуме по индексу:", FORUM_URL)
print_response_get("Получение информации о форуме по несуществующему индексу:", FORUM_WRONG_URL)
print_response_get("Получение информации о форуме по индексу-строке:", FORUM_WRONG_STRING_URL)

print_response_get("Получение информации о всех публичных форумах:", FORUMS_URL)

# Создание форума

print_response_post("Создание форума с неправильным никнеймом:", FORUMS_URL, FORUMS_WRONG_NICKNAME)
print_response_post("Создание форума с неполными данными:", FORUMS_URL, FORUMS_TOO_FEW)
print_response_post("Создание форума:", FORUMS_URL, FORUMS_DATA)

# Сообщения

print_response_get("Получение всех сообщений из форума по индексу:", MESSAGE_URL)
print_response_get("Получение всех сообщений из форума по несуществующему индексу:", MESSAGES_WRONG_URL)
print_response_get("Получение всех сообщений из форума по индексу-строке:", MESSAGES_WRONG_STRING_URL)

print_response_post("Отправка пустого сообщения:", MESSAGES_URL, MESSAGES_EMPTY)
print_response_post("Отправка сообщения:", MESSAGES_URL, MESSAGES_DATA)
print_response_post("Отправка сообщения с возможным риском опасности для пользователей:", MESSAGES_URL, MESSAGES_SECURITY)