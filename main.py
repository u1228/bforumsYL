from flask import Flask, render_template, redirect, abort, request, jsonify, url_for
from flask_socketio import SocketIO, join_room, leave_room
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from flask_wtf import FlaskForm
from flask_restful import reqparse, Api, Resource
from flask_restful import abort as JSON_abort
from flask_mail import Mail
from flask_mail import Message as Msg
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField, DateTimeField
from wtforms.widgets import TextArea
from wtforms.validators import DataRequired
from wtforms.fields.html5 import DateTimeLocalField
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import literal
import markdown
import markdown.extensions.fenced_code
import markdown.extensions.codehilite
from pygments.formatters import HtmlFormatter
from datetime import datetime, timedelta
import requests
from itsdangerous import URLSafeTimedSerializer
from models import User, Forum, Message, Event, session_maker, Bots


session = session_maker()

app = Flask(__name__, template_folder="templates/")
app.config['SECRET_KEY'] = 'blin_is_not_a_pancake'
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["MAIL_SERVER"] = "smtp.yandex.ru"
app.config["MAIL_PORT"] = 465
app.config["MAIL_USE_SSL"] = True
app.config["MAIL_USERNAME"] = 'b.forums'
app.config["MAIL_PASSWORD"] = 'bf100010'
app.config["MAIL_DEFAULT_SENDER"] = "b.forums@yandex.ru"
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
login_manager = LoginManager()
login_manager.init_app(app)
api = Api(app)
socketio = SocketIO(app)
mail = Mail(app)

formatter = HtmlFormatter(style="monokai", full=True, cssclass="codehilite")
css_string = formatter.get_style_defs()
with open("static/css/code_highlight.css", "w") as f:
    f.write(css_string)


@app.context_processor
def inject_variables():
    return dict(format_message=format_message)

# ----------------------------------Классы------------------------------------


class RegisterForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    repeat_password = PasswordField(
        'Repeat assword', validators=[DataRequired()])
    nickname = StringField('Nickname', validators=[DataRequired()])

    submit = SubmitField('Зарегистрироваться')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember me')

    submit = SubmitField('Войти')


class ForumForm(FlaskForm):
    title = StringField('Название', validators=[DataRequired()])
    private = BooleanField('Приватный')
    editors = StringField('Никнеймы редакторов через ", "')

    submit = SubmitField('Создать')


class EventForm(FlaskForm):
    title = StringField('Название', validators=[DataRequired()])
    desc = StringField('Описание', widget=TextArea())
    address = StringField('Место проведения')
    datetime = DateTimeLocalField(
        'Дата проведения (в формате 01.01.2001)', format='%d.%m.%Y', validators=[DataRequired()])

    submit = SubmitField('Создать')


class SearchForm(FlaskForm):
    query = StringField('Запрос', validators=[DataRequired()])

    submit = SubmitField('Поиск')


class EmailForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])

    submit = SubmitField('Отправить')

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


# ----------------------------------Функции-----------------------------------

def check_title(title):
    only = "qwertyuiopasdfghjklzxcvbnmйцукенгшщзхъэждлорпавыфячсмитьбю"
    only += only.upper()
    only += "1234567890_-+=|/*:;.!?@№ "
    return (all([e in only for e in title])) and (not title[0].isdigit()) and (not (title[0] == " "))


def check_nick(nick):
    only = "qwertyuiopasdfghjklzxcvbnm"
    only += only.upper()
    only += "1234567890_-+=|/*@"
    return (all([e in only for e in nick])) and (not nick[0].isdigit())


def get_coordinates(address):
    try:
        response = requests.get(
            f"http://geocode-maps.yandex.ru/1.x/?apikey=40d1649f-0493-4b70-98ba-98533de7710b&geocode={address}&format=json")
        if response:
            json = response.json()
            return json["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]["Point"]["pos"]
    except Exception:
        return False


def get_spn(address):
    try:
        response = requests.get(
            f"http://geocode-maps.yandex.ru/1.x/?apikey=40d1649f-0493-4b70-98ba-98533de7710b&geocode={address}&format=json")
        if response:
            json = response.json()[
                "response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]["boundedBy"]["Envelope"]
            lowerCorner = json["lowerCorner"].split()
            upperCorner = json["upperCorner"].split()
            spn1 = str(
                round(abs(float(lowerCorner[0]) - float(upperCorner[0])), 6))
            spn2 = str(
                round(abs(float(lowerCorner[1]) - float(upperCorner[1])), 6))
            return spn1 + ',' + spn2
    except Exception:
        return False


def render_markdown(string):
    if '```' in string:
        s = string.split('```')
        for i in range(len(s) - 1):
            if i % 2 == 1:
                s[i] = s[i].replace("&lt;", "<").replace(
                    "&quot;", '"').replace("&apos;", "'").replace("&amp;", "&")
        string = '```'.join(s)
    md = markdown.markdown(string, extensions=["fenced_code", "codehilite"]).replace(
        "</pre></div>\n\n", "</pre></div>")

    return md


def check_server_connection(url):
    if url:
        response = requests.post(url, json={"test_connection": 0})
        if response.ok:
            return True
    return False


def check_email(email):
    if "@" not in email:
        return False
    em = email.split("@")
    if len(em) != 2:
        return False
    if '.' not in em[1]:
        return False
    return True


def check_password(password):
    if len(password) < 8:
        return False
    if all([e.isdigit() or e.isascii() or e in "_.!#$%^&*-+=" for e in password]):
        return True
    return False


def format_message(mess):
    message = ""
    for e in mess:
        if e == "<":
            message += "&lt;"
        elif e == '"':
            message += "&quot;"
        elif e == "'":
            message += "&apos;"
        elif e == "&":
            message += "&amp;"
        else:
            message += e
    return render_markdown(message)

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


# ---------------------------Управление-пользователями------------------------

@login_manager.user_loader
def load_user(user_id):
    return session.query(User).get(user_id)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = session.query(User).filter(
            User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/news")
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login.html', title='Авторизация', form=form, message="")


@app.route('/register/<token>', methods=['GET', 'POST'])
def register(token):
    form = RegisterForm()
    try:
        email = serializer.loads(
            token, salt="email_confirmation", max_age=3600)
    except Exception:
        return render_template('register.html', title='Регистрация', form=form, message="Время вышло. Попробуйте зарегистрироваться еще раз.")
    if session.query(User).filter(User.email == email).first():
        return render_template('register.html', title='Регистрация',
                               form=form,
                               message="Такая электронная почта уже есть", email=email)
    if form.validate_on_submit():
        if form.password.data != form.repeat_password.data:
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Пароли не совпадают", email=email)
        if not check_password(form.password.data):
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Пароль должен быть больше 7 символов, и состоять только из цифр, букв латинского алфавита и символов _.!#$%^&*-+=", email=email)
        if not check_nick(form.nickname.data):
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Никнейм содержит недопустимые символы", email=email)
        if session.query(User).filter(User.nickname == form.nickname.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть", email=email)
        user = User()
        user.nickname = form.nickname.data
        user.email = email
        user.set_password(form.password.data)
        session.add(user)
        session.commit()
        forum = Forum()
        forum.title = form.nickname.data
        forum.personal = True
        forum.admin_id = session.query(
            User).order_by(User.id.desc()).first().id
        forum.editors = f"{forum.admin_id},"
        session.add(forum)
        session.commit()
        user = session.query(User).filter(User.id == forum.admin_id).first()
        user.forum_id = session.query(Forum).order_by(
            Forum.id.desc()).first().id
        user.follow = f"{user.forum_id},"
        session.commit()
        return redirect('/login')
    return render_template('register.html', title='Регистрация', form=form, message="", email=email)


@app.route("/register", methods=['GET', 'POST'])
def register_send():
    form = EmailForm()
    if form.validate_on_submit():
        if session.query(User).filter(User.email == form.email.data).first():
            return render_template('email.html', title='Регистрация',
                                   form=form,
                                   message="Такая электронная почта уже есть")
        if not check_email(form.email.data):
            return render_template('email.html', title='Регистрация',
                                   form=form,
                                   message="Почта записана неправильно")
        token = serializer.dumps(form.email.data, salt="email_confirmation")
        message = Msg("Подтверждение почты на BForums",
                      recipients=[form.email.data])
        message.body = "Вы получили это письмо, так как эта почта была указана при регистрации на BForums. Если Вы нигде не указывали эту почту, проигнорируйте это письмо.\n\n"
        message.body += "Ссылка для продолжения регистрации:" + \
            str(url_for("register", token=token, _external=True))
        mail.send(message)
        return render_template('email.html', title='Регистрация', form=form, message=f"Письмо было отправлено на почту {form.email.data}. Срок действия ссылки истечет через час.")
    return render_template('email.html', title='Регистрация', form=form, message="")


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


# ----------------------------------Форумы------------------------------------

@app.route("/forums")
@login_required
def forums():
    follows = session.query(Forum).filter(Forum.id.in_(
        current_user.follow.split(",")), Forum.admin_id != current_user.id).all()
    created = session.query(Forum).filter(
        Forum.admin_id == current_user.id).all()
    return render_template("forums.html", title="Форумы", follows=follows, created=created)


@app.route("/createforum", methods=["GET", "POST"])
@login_required
def create_forum():
    form = ForumForm()
    if form.validate_on_submit():
        if not check_title(form.title.data):
            return render_template('create_forum.html', title='Создать форум', form=form, message=f"Название содержит недопустимые символы.")
        editors = ""
        if form.editors.data:
            for nickname in form.editors.data.split(", "):
                user = session.query(User).filter(
                    User.nickname == nickname).first()
                if not user:
                    return render_template('create_forum.html', title='Создать форум', form=form, message=f"Пользователя с ником {nickname} не существует.")
                editors += str(user.id) + ","
        forum = Forum()
        forum.title = form.title.data
        forum.private = form.private.data
        forum.editors = editors
        forum.admin_id = current_user.id
        session.add(forum)
        session.commit()
        current_user.follow += str(session.query(
            Forum).order_by(Forum.id.desc()).first().id) + ","
        session.commit()
        return redirect('/forums')
    return render_template('create_forum.html', title='Создать форум', form=form, message="")


@app.route("/editforum/<int:forum_id>", methods=["GET", "POST"])
@login_required
def edit_forum(forum_id):
    forum = session.query(Forum).filter(Forum.id == forum_id).first()
    if forum:
        if forum.personal or current_user.id != forum.admin_id:
            return abort(403)
        form = ForumForm()
        if form.validate_on_submit():
            if not check_title(form.title.data):
                return render_template('edit_forum.html', title=f'Редактировать {forum.title}', form=form, message=f"Название содержит недопустимые символы.")
            editors = ""
            if form.editors.data:
                for nickname in form.editors.data.split(", "):
                    user = session.query(User).filter(
                        User.nickname == nickname).first()
                    if not user:
                        return render_template('edit_forum.html', title=f'Редактировать {forum.title}', form=form, message=f"Пользователя с ником {nickname} не существует.")
                    editors += str(user.id) + ","
            forum.title = form.title.data
            forum.editors = editors
            session.add(forum)
            session.commit()
            return redirect(f'/f/{forum_id}')

        editors = ""
        if forum.editors:
            for id in forum.editors.split(","):
                if id:
                    user = session.query(User).filter(User.id == id).first()
                    editors += str(user.nickname) + ", "
        form.title.data = forum.title
        form.editors.data = editors.strip(', ')
        return render_template('edit_forum.html', title=f'Редактировать {forum.title}', form=form, message="")
    return abort(404)


@app.route("/f/<int:forum_id>")
@login_required
def forum(forum_id):
    forum = session.query(Forum).filter(Forum.id == forum_id).first()
    if forum:
        p = {"title": forum.title,
             "id": forum.id,
             "editors": session.query(User).filter(User.id.in_(forum.editors.split(","))).all(),
             "admin": session.query(User).filter(User.id == forum.admin_id).first(),
             "private": forum.private,
             "personal": forum.personal,
             "messages": session.query(Message).filter(Message.forum_id == forum_id).all(),
             "users": session.query(User),
             "User": User,
             "str": str,
             }
        if p["editors"]:
            if not (any([current_user.id == e.id for e in p["editors"]]) or current_user.id == forum.admin_id):
                if forum.private:
                    return abort(403)
                p["can_write"] = False
            else:
                p["can_write"] = True
        else:
            p["can_write"] = True

        return render_template("forum.html", **p)
    else:
        return abort(404)


@app.route("/follow/<forum_id>")
@login_required
def follow(forum_id):
    forum = session.query(Forum).filter(Forum.id == forum_id).first()
    if forum:
        user = session.query(User).filter(current_user.id == User.id).first()
        if forum_id in user.follow.split(','):
            user.follow = ",".join(
                [e for e in user.follow.split(',') if e != forum_id])
        else:
            user.follow = ",".join([forum_id] + user.follow.split(','))
        session.add(user)
        session.commit()
        return redirect(f"/f/{forum_id}")
    return abort(404)


@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    form = SearchForm()
    if form.validate_on_submit():
        return redirect(f"/search?q={'+'.join(form.query.data.split())}")
    query = request.args.get("q")
    if query:
        query = " ".join(query.split("+"))
        form.query.data = query
        forums = session.query(Forum).filter(((Forum.id.in_(query)) | (Forum.title.ilike(
            f"%{query}%"))) & ((~Forum.private) | (Forum.editors.like(f"%{current_user.id},%"))))
        return render_template("search.html", title="Поиск", forums=forums, form=form)
    return render_template("search.html", title="Поиск", forums=[], form=form)

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


# -----------------------------Мероприятия------------------------------------

@app.route("/createevent/<forum_id>", methods=["GET", "POST"])
@login_required
def create_event(forum_id):
    forum = session.query(Forum).filter(Forum.id == forum_id).first()
    if not forum:
        return abort(404)
    if current_user.id != forum.admin_id or forum.personal:
        return abort(403)

    form = EventForm()
    if form.validate_on_submit():
        if not check_title(form.title.data):
            return render_template('create_event.html', title='Создать мероприятие', form=form, message=f"Название содержит недопустимые символы.")
        if form.address.data:
            if not get_coordinates(form.address.data):
                return render_template('create_event.html', title='Создать мероприятие', form=form, message=f"Не удается найти указанный адрес.")
        event = Event()
        event.forum_id = forum_id
        event.title = form.title.data
        event.desc = form.desc.data
        event.geo_point = form.address.data
        event.datetime = form.datetime.data
        session.add(event)
        session.commit()
        return redirect("/events")
    return render_template('create_event.html', title='Создать мероприятие', form=form, message="")


@app.route("/editevent/<event_id>", methods=["GET", "POST"])
@login_required
def edit_event(event_id):
    event = session.query(Event).filter(event_id == Event.id).first()
    if not event:
        return abort(404)
    forum_id = event.forum_id
    forum = session.query(Forum).filter(Forum.id == forum_id).first()
    if not forum:
        return abort(404)
    if current_user.id != forum.admin_id or forum.personal:
        return abort(403)

    form = EventForm()
    if form.validate_on_submit():
        if not check_title(form.title.data):
            return render_template('create_event.html', title='Редактировать мероприятие', form=form, message=f"Название содержит недопустимые символы.")
        if form.address.data:
            if not get_coordinates(form.address.data):
                return render_template('create_event.html', title='Редактировать мероприятие', form=form, message=f"Не удается найти указанный адрес.")
        event.forum_id = forum_id
        event.title = form.title.data
        event.desc = form.desc.data
        event.geo_point = form.address.data
        event.datetime = form.datetime.data
        session.add(event)
        session.commit()
        return redirect("/events")
    form.title.data = event.title
    form.desc.data = event.desc
    form.address.data = event.geo_point
    form.datetime.data = event.datetime
    return render_template('create_event.html', title='Редактировать мероприятие', form=form, message="")


@app.route("/events")
@login_required
def events():
    follow = [e.id for e in session.query(Forum).filter(
        (Forum.id.in_(current_user.follow.split(","))) & (~Forum.private)).all()]
    events = session.query(Event).filter(Event.forum_id.in_(follow)).all()
    events = [e for e in reversed(events) if e]
    return render_template('events.html', title="Мероприятия", events=events)


@app.route('/e/<int:event_id>')
@login_required
def event(event_id):
    event = session.query(Event).filter(Event.id == event_id).first()
    if event:
        if not event.forum.private:
            return render_template('event.html', title=event.title, event=event, get=requests.get, get_coordinates=get_coordinates, get_spn=get_spn)
        if event.forum.editors != "":
            if str(current_user.id) in event.forum.editors.split(",") or current_user.id == event.forum.admin_id:
                return render_template('event.html', title=event.title, event=event, get=requests.get, get_coordinates=get_coordinates, get_spn=get_spn)
            return abort(403)
        return render_template('event.html', title=event.title, event=event, get=requests.get, get_coordinates=get_coordinates, get_spn=get_spn)
    return abort(404)


@app.route('/deleteevent/<int:event_id>')
@login_required
def delete_event(event_id):
    event = session.query(Event).filter(Event.id == event_id).first()
    if event:
        if current_user.id == event.forum.admin_id:
            session.delete(event)
            session.commit()
            return redirect('/events')
        return abort(403)
    return abort(404)

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


# ----------------------------Другие-страницы---------------------------------

@app.errorhandler(400)
def bad_request(error):
    return render_template('error.html', title="Ошибка 400", code=400), 400


@app.errorhandler(401)
def unauthorized(error):
    return redirect("/login"), 401


@app.errorhandler(403)
def forbidden(error):
    return render_template('error.html', title="Ошибка 403", code=403), 403


@app.errorhandler(404)
def page_not_found(error):
    return render_template('error.html', title="Ошибка 404", code=404), 404


@app.errorhandler(500)
def internal_server_error(error):
    return render_template('error.html', title="Ошибка 500", code=500), 500


@app.route("/400")
def test_error400():
    return abort(400)


@app.route("/401")
def test_error401():
    return abort(401)


@app.route("/403")
def test_error403():
    return abort(403)


@app.route("/404")
def test_error404():
    return abort(404)


@app.route("/500")
def test_error500():
    return abort(500)


@app.route('/')
def main():
    if current_user.is_authenticated:
        return redirect("/news")
    return redirect("/login")


@app.route('/news')
@login_required
def news():
    follow = [e.id for e in session.query(Forum).filter(
        (Forum.id.in_(current_user.follow.split(","))) & (~Forum.private)).all()]
    messages = session.query(Message).filter((Message.forum_id.in_(follow)) & (
        Message.datetime > (datetime.now() - timedelta(days=1)))).all()
    m = [e for e in reversed(messages) if e]
    return render_template('news.html', title='Новости', messages=m, session=session, User=User, Forum=Forum)


@app.route('/u/<int:user_id>')
def user_page(user_id):
    user = session.query(User).filter(User.id == user_id).first()
    if user:
        forums = session.query(Forum).filter(
            (Forum.id.in_(user.follow.split(","))) & (~Forum.private)).all()
        private = session.query(Forum).filter(
            (Forum.id.in_(user.follow.split(","))) & (Forum.private)).all()
        personal = session.query(Forum).filter(
            Forum.id == user.forum_id).first()
        return render_template('user.html', title=user.nickname, user=user, forums=forums, personal=personal, private=private)
    return abort(404)

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


# ------------------------------SocketIO--------------------------------------

@socketio.on('new_message')
def handle_new_message(json, methods=['GET', 'POST']):
    if "user_id" in json.keys():
        json["message"] = json["message"].strip()
        if json["message"]:
            message = Message()
            message.user_id = json["user_id"]
            message.message = json["message"]
            message.forum_id = json["forum_id"]
            message.datetime = datetime.now()
            session.add(message)
            session.commit()
            json["format_message"] = format_message(json["message"])
            json["datetime"] = message.datetime.strftime("%d.%m.%Y %H:%M")
            socketio.emit('recieve_response', json, room=str(json["forum_id"]))

            responses = bots_callback(
                json["forum_id"], json["message"], json["user_id"], json["datetime"])
            for bot, response in responses:
                if response.strip():
                    message = Message()
                    message.user_id = bot.user_id
                    message.message = response
                    message.forum_id = json["forum_id"]
                    message.datetime = datetime.now()
                    session.add(message)
                    session.commit()
                    res = {}
                    res["forum_id"] = message.forum_id
                    res["user_id"] = message.user_id
                    res["format_message"] = format_message(message.message)
                    res["user_nickname"] = bot.user.nickname
                    res["datetime"] = message.datetime.strftime(
                        "%d.%m.%Y %H:%M")
                    socketio.emit('recieve_response', res,
                                  room=str(res["forum_id"]))


@socketio.on('join')
def on_join(room):
    join_room(room)


@socketio.on('leave')
def on_leave(room):
    leave_room(room)


def bots_callback(forum_id, message, user_id, dt):
    bots = session.query(Bots).all()
    responses = []
    for bot in bots:
        if str(forum_id) in bot.user.follow.split(','):
            server = bot.server
            json = {
                "message": message,
                "forum_id": forum_id,
                'user_id': user_id,
                'datetime': dt
            }
            responses.append((bot, requests.post(server, json=json).text))
    return responses


# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


# ---------------------------------API----------------------------------------

class LoginResource(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('email', required=True, type=str)
    parser.add_argument('password', required=True, type=str)

    def post(self):
        args = self.parser.parse_args()
        user = session.query(User).filter(User.email == args['email']).first()
        if user and user.check_password(args['password']):
            login_user(user)
            return jsonify({'success': 'OK'})
        else:
            JSON_abort(404, message="Wrong email or password")


class UserResource(Resource):
    def get(self, user_id):
        if not user_id.isdigit():
            return JSON_abort(404, message="User not found")
        user_id = int(user_id)
        user = session.query(User).filter(User.id == user_id).first()
        if user:
            res = {}
            forums = session.query(Forum.id).filter(
                (Forum.id.in_(user.follow.split(","))) & (~Forum.private)).all()
            private = session.query(Forum.id).filter(
                (Forum.id.in_(user.follow.split(","))) & (Forum.private)).all()
            if current_user.is_authenticated:
                if current_user.id == user_id:
                    res["private_forums"] = private
                    res["email"] = user.email
            res["personal_forum"] = user.forum_id
            res["followed"] = forums
            res["nickname"] = user.nickname
            return jsonify({"user": res})
        return JSON_abort(404, message="User not found")


class UsersResource(Resource):
    def get(self):
        res = {}
        users = session.query(User).all()
        res['users'] = []
        for user in users:
            res['users'].append(
                {"id": user.id, "nickname": user.nickname, "personal_forum": user.forum_id})
        return jsonify(res)


class EventsResource(Resource):
    def get(self):
        if not current_user.is_authenticated:
            return JSON_abort(401, message="You should login first.")
        follow = [e.id for e in session.query(Forum).filter(
            (Forum.id.in_(current_user.follow.split(","))) & (~Forum.private)).all()]
        events = session.query(Event).filter(Event.forum_id.in_(follow)).all()
        res = {}
        res['events'] = []
        for event in events:
            if event:
                res['events'].append({"id": event.id,
                                      "forum_id": event.forum_id,
                                      "title": event.title,
                                      "description": event.desc,
                                      "address": event.geo_point,
                                      "date": event.datetime})
        return jsonify(res)


class ForumResource(Resource):
    def get(self, forum_id):
        if not forum_id.isdigit():
            return JSON_abort(404, message="Forum not found")
        forum_id = int(forum_id)
        forum = session.query(Forum).filter(Forum.id == forum_id).first()
        if not forum:
            return JSON_abort(404, message="Forum not found")
        res = {}
        if forum.private:
            if current_user.is_authenticated:
                if (not current_user.id == forum.admin_id) and (not str(current_user.id) in forum.editors.split(',')):
                    return JSON_abort(403, message="Forbidden")
            else:
                return JSON_abort(401, message="You should login first.")
        res["title"] = forum.title
        res["private"] = forum.private
        res["personal"] = forum.personal
        res["admin_id"] = forum.admin_id
        res["editors"] = forum.editors.split(',')[:-1]
        return jsonify({"forum": res})


class ForumsResource(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('title', required=True, type=str)
    parser.add_argument('private', required=True, type=bool)
    parser.add_argument('editors', required=True, type=str)

    def get(self):
        forums = session.query(Forum).filter(~Forum.private).all()
        return jsonify({"forums": [{"title": e.title, "admin_id": e.admin_id, 'personal': e.personal, "id": e.id} for e in forums]})

    def post(self):
        args = self.parser.parse_args()
        if not current_user.is_authenticated:
            return JSON_abort(401, message="You should login first.")
        if not check_title(args["title"]):
            return JSON_abort(400, message="Forbidden symbols")
        editors = ""
        if args["editors"]:
            for nickname in args["editors"].split(", "):
                user = session.query(User).filter(
                    User.nickname == nickname).first()
                if not user:
                    return JSON_abort(400, message=f"Nickname {nickname} not exist.")
                editors += str(user.id) + ","
        forum = Forum()
        forum.title = args["title"]
        forum.private = args["private"]
        forum.editors = editors
        forum.admin_id = current_user.id
        session.add(forum)
        session.commit()
        current_user.follow += str(session.query(
            Forum).order_by(Forum.id.desc()).first().id) + ","
        session.commit()
        return jsonify({'success': 'OK'})


class MessagesResource(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('message', required=True, type=str)

    def get(self, forum_id):
        if not forum_id.isdigit():
            return JSON_abort(404, message="Forum not found")
        forum_id = int(forum_id)
        if not current_user.is_authenticated:
            return JSON_abort(401, message="You should login first.")
        forum = session.query(Forum).get(forum_id)
        if not forum:
            return JSON_abort(404, message="Forum not found")
        if forum.private and ((not current_user.id == forum.admin_id) and (not str(current_user.id) in forum.editors.split(','))):
            return JSON_abort(403, message="Forbidden")
        messages = session.query(Message).filter(
            Message.forum_id == forum_id).all()
        return jsonify({"messages": [{"user_id": e.user_id, "message": e.message, "datetime": e.datetime} for e in messages]})

    def post(self, forum_id):
        if not forum_id.isdigit():
            return JSON_abort(404, message="Forum not found")
        forum_id = int(forum_id)
        if not current_user.is_authenticated:
            return JSON_abort(401, message="You should login first.")
        forum = session.query(Forum).get(forum_id)
        if not forum:
            return JSON_abort(404, message="Forum not found")
        if forum.private and ((not current_user.id == forum.admin_id) and (not str(current_user.id) in forum.editors.split(','))):
            return JSON_abort(403, message="Forbidden")
        args = self.parser.parse_args()
        if not args["message"].strip():
            return JSON_abort(400, message="Message is empty")
        json = {}
        json['user_id'] = current_user.id
        json['forum_id'] = forum_id
        json['message'] = args["message"].strip()
        json['datetime'] = datetime.now()
        json['user_nickname'] = current_user.nickname
        handle_new_message(json)
        return jsonify({'success': 'OK'})


class CallbackResource(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('server', required=True, type=str)

    def post(self):
        if not current_user.is_authenticated:
            return JSON_abort(401, message="You should login first.")
        server = self.parser.parse_args()["server"].strip()
        if session.query(Bots).filter(Bots.server == server).first():
            return JSON_abort(400, message="This server is already in use")
        bot = session.query(Bots).filter(
            Bots.user_id == current_user.id).first()
        if bot:
            bot.server = server
        else:
            bot = Bots()
            bot.user_id = current_user.id
            bot.server = server
        session.add(bot)
        session.commit()
        return jsonify({"success": "OK"})

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


if __name__ == '__main__':
    api.add_resource(LoginResource, '/api/v1/login')
    api.add_resource(UserResource, '/api/v1/user/<user_id>')
    api.add_resource(UsersResource, '/api/v1/users')
    api.add_resource(EventsResource, '/api/v1/events')
    api.add_resource(ForumResource, '/api/v1/forum/<forum_id>')
    api.add_resource(ForumsResource, '/api/v1/forums')
    api.add_resource(MessagesResource, '/api/v1/messages/<forum_id>')
    api.add_resource(CallbackResource, "/api/v1/callback")
    print("Running.")
    socketio.run(app, debug=True)
