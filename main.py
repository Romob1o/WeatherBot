import telebot
from datetime import datetime
from requests import get
from data import db_session
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


@bot.message_handler(commands=['start'])
def start_bot(message):
    welcome_text = "Some welcome text"
    bot.send_message(message.chat.id, welcome_text)

    try:
        user = User()
        user.username = message.from_user.username
        user.user_tg_id = message.chat.id
        db_sess = db_session.create_session()
        db_sess.add(user)
        db_sess.commit()
        print("note in users")

    except sqlalchemy.exc.IntegrityError:
        pass


@bot.message_handler(commands=['subscriptions'])
def send_subscriptions(message):
    subscriptions = my_subscriptions(message.chat.id)

    sub_list = subscriptions.values()
    sub_res = []
    for item in sub_list:
        sub_res.append(f"{item[0]}. {item[1]} / {item[2]}")
    sub_str = "\n".join(sub_res)

    subs_message = f"Your current subscriptions:\n" \
                   f"\n" \
                   f"{sub_str}"

    bot.send_message(message.chat.id, subs_message)
    return subscriptions


@bot.message_handler(commands=['delete'])
def delete_subscriptions_beginning(message):
    subscriptions = send_subscriptions(message)

    delete_text = "Some delete text"
    bot.send_message(message.chat.id, delete_text)

    bot.register_next_step_handler(message, delete_subscriptions, subscriptions)


def delete_subscriptions(message, subscriptions):
    nums = message.text.split(",")
    print(subscriptions)

    for num in nums:
        list_for_id = subscriptions[int(num)]

        task_id = f"{message.chat.id}{list_for_id[1]}{list_for_id[2]}"

        db_sess = db_session.create_session()
        task = db_sess.query(Task).filter(Task.user_tg_id == message.chat.id, Task.city == list_for_id[1],
                                          Task.time == list_for_id[2]).first()
        db_sess.delete(task)
        db_sess.commit()

        scheduler.remove_job(task_id)


@bot.message_handler(commands=['set'])
def city_selection(message):
    city_text = "select some city"
    bot.send_message(message.chat.id, city_text)
    bot.register_next_step_handler(message, time_selection)


def time_selection(message):
    city = message.text

    if check_city(city):
        time_text = "select your time"
        bot.send_message(message.chat.id, time_text)
        bot.register_next_step_handler(message, set_notifications, city)

    else:
        error_text = "error city"
        bot.send_message(message.chat.id, error_text)
        bot.register_next_step_handler(message, time_selection)


def set_notifications(message, city):
    time = message.text
    split_time = time.split(":")
    print(split_time)
    if (":" not in time) or len(time) != 5 or not time[0].isdigit() or not time[1].isdigit() or not time[
        3].isdigit() or not time[4].isdigit() or not (0 <= int(split_time[0]) <= 23) or not (
            0 <= int(split_time[1]) <= 59):
        error_text = "error time"
        bot.send_message(message.chat.id, error_text)
        bot.register_next_step_handler(message, set_notifications, city)

    else:
        success_text = "success"
        bot.send_message(message.chat.id, success_text)

        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
        res = get(url).json()

        city = res["name"]
        print(city, time)

        hour = time.split(":")[0]
        minute = time.split(":")[1]

        task = Task()
        task.city = city
        task.time = time
        task.user_tg_id = message.chat.id
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
        print(f"{message.chat.id}{city}{time}")


@bot.message_handler(content_types=["text"])
def user_message(message):
    if check_city(message.text):
        send_weather(message.text, message.chat.id)

    else:
        error_message = "Some error text"
        bot.send_message(message.chat.id, error_message)


bot.infinity_polling()
