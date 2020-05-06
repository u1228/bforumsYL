# (Документация) по API BForums

## Вход

Для некоторых действий нужен обязательный вход. Для входа на свою страницу нужно отправить post-запрос с JSON аргументами email и password на адрес `/api/v1/login`. Пример входа на python:

```python
from requests import Session


s = Session()
json = {"email": "your-email", "password": "your-password"}
s.post("http://bforums.herokuapp.com/api/v1/login", json=json)
```

В примере используется Session для того, чтобы не выходить из текущей сессии.

## Получение списка пользователей

Весь список пользователей в формате JSON можно получить по адресу `/api/v1/users`. В списке будут указаны id, nickname и personal_forum. Больше информации можно получить, воспользовавшись получением отдельно каждого пользователя. Авторизация не обязательна. **Добавить новых пользователей через API нельзя.** Пример на python:

```python
s.get("http://bforums.herokuapp.com/api/v1/users")
```

## Получение информации об отдельном пользователе

Получить информацию об отдельном пользователе по id можно по адресу `/api/v1/user/<id>`. Если вы вошли как этот пользователь, то вам также будут доступны private_forums и email. В остальных ситуациях вы получите только personal_forum, followed и nickname. Пример на python:

```python
s.get("http://bforums.herokuapp.com/api/v1/user/2")
```

## Получение мероприятий

Вы должны быть авторизованы. При получении мероприятий вы увидите только мероприятия с форумов, которые вы отслеживаете. Адрес для получения - `/api/v1/events`. Пример на python:

```python
s.get("http://bforums.herokuapp.com/api/v1/events")
```

## Получение списка форумов

Все публичные форумы будут отображены по адресу `/api/v1/forums`. Авторизация необязательна. Пример на python:

```python
s.get("http://bforums.herokuapp.com/api/v1/forums")
```

## Получение информации об отдельном форуме

О приватных форумах можно получить информацию только если вы администратор или состоите в списке редакторов этого форума. В остальных случаях можно получить информацию только о публичных форумах. Адрес: `/api/v1/forum/<id>` Пример на python:

```python
s.get("http://bforums.herokuapp.com/api/v1/forum/1")
```

## Создание форума

Создать форум можно отправив post-запрос на адрес `/api/v1/forums` с аргументами title, private и editors в формате JSON. Все также, как и в графическом интерфейсе: title - строка, private - true или false, и editors - список никнеймов редакторов через ", ". Пример на python:

```python
json = {"title": "Forum-Title", "private": True, "editors": ""}
s.post("http://bforums.herokuapp.com/api/v1/forums", json=json)
```

## Получение всех сообщений с какого-либо форума

Авторизация обязательна. Адрес: `/api/v1/messages/<id>`. В ответе будет JSON список с user_id, message и datetime. Пример на python:

```python
s.get("http://bforums.herokuapp.com/api/v1/messages/1")
```

## Отправка сообщений в какой-либо форум

Естественно, авторизация обязательна. Для отправки сообщений надо послать post-запрос на адрес `/api/v1/messages/<id>`. В посылаемом JSON должно быть одно поле: message. Пример на python:

```python
json = {'message': "Something"}
s.post("http://bforums.herokuapp.com/api/v1/messages/2", json=json)
```

## Создание бота (на языке python)

У бота должен быть свой аккаунт, поэтому выходите из аккаунта и регистрируйте новый. Муторно, но   все против спама. На форумах, в которых должен работать бот, нажмите на "отслеживать". Далее, при помощи Flask создайте какую-нибудь страницу, на которую будут посылаться сообщения. Для примера можно взять хоть "/". Укажите ей метод post. Далее получаем аргументы от запроса с помощью request от flask:

```python
args = request.get_json()
```

Теперь проверяем, есть ли среди аргументов аргумент message. (Ну вообще, по идее, BForums должен его, но проверка никогда не помешает.) Если аргумент присутствует, мы можем взять текст из него. Для дополнительной информации вместе с аргументом message должны быть аргументы forum_id, user_id и datetime. Использовать их все, очевидно, не обязательно. Далее мы обрабатываем полученный текст и возвращаем ответ через return. Если выслать пустые кавычки, то это будет засчитано как отсутствие сообщения. Вот пример простой страницы для переворачивания текста по команде "переверни ...":

```python
@app.route("/", methods=["POST"])
def main():
    args = request.get_json()
    if "message" in args.keys():
        message = args["message"].lower()
        ms = message.split(' ')
        if ms[0] == "переверни":
            return ' '.join(ms[1:])[::-1]
    return ""
```

Далее в этом же скрипте надо войти в аккаунт через API. Для того, чтобы BForums знал, куда обращаться, после авторизации надо отправить post-запрос на адрес `/api/v1/callback` с указанием аргумента server. В этот аргумент, что логично, надо записать адрес сервера нашего бота. Так как я делаю бота для примера, воспользуемся ngrok. Для этого его нужно скачать с [официального сайта](https://ngrok.com/download). После этого запускаем временный туннель на порт нашего бота (стандартный порт - 5000) через команду ` ngrok http <port>`. Теперь по адресу "http://localhost:4040/api/tunnels" будет JSON, в котором можно найти название нашего временного сервера ngrok. Его мы и посылаем в качестве аргумента server. Запускаем бота. Теперь, если вы все сделали правильно, то при отправке сообщения в отслеживаемый ботом форум с текстом "переверни ...", должно мгновенно прийти сообщение от бота с перевернутым текстом после "переверни". Итоговый код:

```python
from requests import Session
from flask import Flask, request, jsonify, abort


s = Session()
app = Flask(__name__)

EMAIL = "your-bot-email"
PASSWORD = "your-bot-password"

LOGIN_URL = "http://bforums.herokuapp.com/api/v1/login"
CALLBACK_URL = "http://bforums.herokuapp.com/api/v1/callback"

@app.route("/", methods=["POST"])
def main():
    args = request.get_json()
    if "message" in args.keys():
        message = args["message"].lower()
        ms = message.split(' ')
        if ms[0] == "переверни":
            return ' '.join(ms[1:])[::-1]
    return ""

def get_ngrok_server():
    return s.get("http://localhost:4040/api/tunnels").json()['tunnels'][0]['public_url']

response = s.post(LOGIN_URL, json={"email": EMAIL, "password": PASSWORD})
if response.ok:
    response = s.post(CALLBACK_URL, json={"server": get_ngrok_server()})

if __name__ == "__main__":
    app.run()
```

В базе данных ботов на каждого бота приходится один сервер, и при повторной отправке сервера на сайт предыдущий заменится на настоящий.

Удачи вам, и используйте полученную информацию на что-то полезное!

