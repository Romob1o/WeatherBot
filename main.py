import telebot
from datetime import datetime
from requests import get
from data import db_session
from data.messages import CONST_MSGS
from data.users import User
from data.tasks import Task
from PIL import ImageDraw, Image
import sqlalchemy
from apscheduler.schedulers.background import BackgroundScheduler

bot = telebot.TeleBot("6325848689:AAEK_VjDa2zVp3p-vycNft5wdj1zkfixBpE")

API_KEY = "2c08d217e8519012256028a1f119b4c2"

db_session.global_init("db/weather_bot.db")

scheduler = BackgroundScheduler()
scheduler.start()

WIDTH = 1686
HEIGHT = 3000

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

PICTURES_OF_WEATHER = {
    "01": "01",
    "02": "02",
    "03": "03",
    "04": "03",
    "09": "04",
    "10": "04",
    "11": "04",
    "13": "04",
    "50": "03"
}

commands = {"/start": "start_bot",
            "/set": "city_selection",
            "/subscriptions": "send_subscriptions",
            "/delete": "delete_subscriptions_beginning"}


def check_city(city):
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
    res = get(url).json()
    ans = False

    if res["cod"] == 200:
        ans = True

    return ans


def give_current_weather(city):
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
    res = get(url).json()

    print(res)

    city = res["name"]
    condition = res["weather"][0]["main"]
    pic = res["weather"][0]["icon"]
    temperature = res["main"]["temp"]
    max_temperature = res["main"]["temp_max"]
    min_temperature = res["main"]["temp_min"]
    feels_like = res["main"]["feels_like"]
    humidity = res["main"]["humidity"]
    wind_speed = res["wind"]["speed"]

    image = Image.open(f"pictures/{PICTURES_OF_WEATHER[pic[:2]]}{pic[2]}.png")

    draw = ImageDraw.Draw(image)

    draw.text((WIDTH // 2, 350),
              f"{city}",
              font_size=150,
              fill=WHITE,
              anchor="mm")

    draw.text((WIDTH // 2, 650),
              f"{round(temperature)}°",
              font_size=400,
              fill=WHITE,
              anchor="mm")

    draw.text((WIDTH // 2, 950),
              f"Feels like {round(feels_like)}°",
              font_size=110,
              fill=WHITE,
              anchor="mm")

    draw.text((WIDTH // 2, 1100),
              f"H: {round(max_temperature)}° L: {round(min_temperature)}°",
              font_size=110,
              fill=WHITE,
              anchor="mm")

    draw.text((WIDTH // 2, 1600),
              f"{condition}",
              font_size=110,
              fill=WHITE,
              anchor="mm")

    draw.text((WIDTH // 2, 1800),
              f"Humidity: {humidity}%",
              font_size=110,
              fill=WHITE,
              anchor="mm")

    draw.text((WIDTH // 2, 2000),
              f"Wind speed: {round(wind_speed)}m/s",
              font_size=110,
              fill=WHITE,
              anchor="mm")

    return image


def send_weather(city, chat_id):
    current_weather = give_current_weather(city)
    bot.send_photo(chat_id, current_weather)


def my_subscriptions(chat_id):
    db_sess = db_session.create_session()
    result = {}
    count = 1

    for task in db_sess.query(Task).filter(Task.user_tg_id == chat_id).order_by(Task.city):
        result[count] = [count, task.city, task.time]
        count += 1

    return result


def check_cmd_and_run(text):
    if text in commands.keys():
        return True


db_sess = db_session.create_session()
for task in db_sess.query(Task).all():
    scheduler.add_job(send_weather,
                      trigger="cron",
                      hour=task.time.split(":")[0],
                      minute=task.time.split(":")[1],
                      start_date=datetime.now(),
                      kwargs={"city": task.city, "chat_id": task.user_tg_id},
                      id=f"{task.user_tg_id}{task.city}{task.time}")

print(scheduler.get_jobs())


@bot.message_handler(commands=['start'])
def start_bot(message):
    bot.send_message(message.chat.id, CONST_MSGS["greeting_text"])

    try:
        user = User()
        user.username = message.from_user.username
        user.user_tg_id = message.chat.id
        db_sess = db_session.create_session()
        db_sess.add(user)
        db_sess.commit()

    except sqlalchemy.exc.IntegrityError:
        return


@bot.message_handler(commands=['subscriptions'])
def send_subscriptions(message):
    subscriptions = my_subscriptions(message.chat.id)

    sub_list = subscriptions.values()
    sub_res = []
    for item in sub_list:
        sub_res.append(f"{item[0]}. {item[1]} / {item[2]}")
    sub_str = "\n".join(sub_res)

    if len(sub_list) == 0:
        bot.send_message(message.chat.id, CONST_MSGS["no_subs_text"])

    else:
        subs_text = f"Your current subscriptions:\n" \
                    f"\n" \
                    f"{sub_str}"
        bot.send_message(message.chat.id, subs_text)

    return subscriptions


@bot.message_handler(commands=['delete'])
def delete_subscriptions_beginning(message):
    subscriptions = send_subscriptions(message)

    if len(subscriptions.values()) == 0:
        return

    bot.send_message(message.chat.id, CONST_MSGS["deletion_text"])

    bot.register_next_step_handler(message, delete_subscriptions, subscriptions)


def delete_subscriptions(message, subscriptions):
    if check_cmd_and_run(message.text.split()[0]):
        func = globals()[commands[message.text.split()[0]]]
        func(message)
        return

    try:
        list_for_id = subscriptions[int(message.text)]

    except ValueError:
        bot.send_message(message.chat.id, CONST_MSGS["deletion_value_error_text"])
        bot.register_next_step_handler(message, delete_subscriptions, subscriptions)
        return

    except KeyError:
        bot.send_message(message.chat.id, CONST_MSGS["deletion_num_error_text"])
        bot.register_next_step_handler(message, delete_subscriptions, subscriptions)
        return

    task_id = f"{message.chat.id}{list_for_id[1]}{list_for_id[2]}"

    db_sess = db_session.create_session()
    task = db_sess.query(Task).filter(Task.user_tg_id == message.chat.id, Task.city == list_for_id[1],
                                      Task.time == list_for_id[2]).first()
    db_sess.delete(task)
    db_sess.commit()

    scheduler.remove_job(task_id)

    bot.send_message(message.chat.id, CONST_MSGS["deletion_success_text"])


@bot.message_handler(commands=['set'])
def city_selection(message):
    bot.send_message(message.chat.id, CONST_MSGS["city_selection_text"])
    bot.register_next_step_handler(message, time_selection)


def time_selection(message):
    if check_cmd_and_run(message.text.split()[0]):
        func = globals()[commands[message.text.split()[0]]]
        func(message)
        return

    city = message.text

    if check_city(city):
        bot.send_message(message.chat.id, CONST_MSGS["time_selection_text"])
        bot.register_next_step_handler(message, set_notifications, city)

    else:
        bot.send_message(message.chat.id, CONST_MSGS["city_selection_error_text"])
        bot.register_next_step_handler(message, time_selection)


def set_notifications(message, city):
    if check_cmd_and_run(message.text.split()[0]):
        func = globals()[commands[message.text.split()[0]]]
        func(message)
        return

    time = message.text
    split_time = time.split(":")

    if (":" not in time) or len(time) != 5 or not time[0].isdigit() or not time[1].isdigit() or not time[
        3].isdigit() or not time[4].isdigit() or not (0 <= int(split_time[0]) <= 23) or not (
            0 <= int(split_time[1]) <= 59):

        bot.send_message(message.chat.id, CONST_MSGS["time_selection_error_text"])
        bot.register_next_step_handler(message, set_notifications, city)

    else:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
        res = get(url).json()
        city = res["name"]

        hour = time.split(":")[0]
        minute = time.split(":")[1]

        task = Task()
        task.city = city
        task.time = time
        task.user_tg_id = message.chat.id

        try:
            db_sess = db_session.create_session()
            db_sess.add(task)
            db_sess.commit()

            scheduler.add_job(send_weather,
                              trigger="cron",
                              hour=hour,
                              minute=minute,
                              start_date=datetime.now(),
                              kwargs={"city": city, "chat_id": message.chat.id},
                              id=f"{message.chat.id}{city}{time}")

            bot.send_message(message.chat.id, CONST_MSGS["set_success_text"])

        except sqlalchemy.exc.IntegrityError:
            bot.send_message(message.chat.id, CONST_MSGS["set_error_text"])


@bot.message_handler(content_types=["text"])
def user_message(message):
    if check_city(message.text):
        send_weather(message.text, message.chat.id)

    else:
        bot.send_message(message.chat.id, CONST_MSGS["city_selection_error_text"])


bot.infinity_polling()
