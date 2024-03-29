import telebot
from telebot import types
from requests import get
import json
from PIL import ImageDraw, Image

bot = telebot.TeleBot("6325848689:AAEK_VjDa2zVp3p-vycNft5wdj1zkfixBpE")

API_KEY = "2c08d217e8519012256028a1f119b4c2"

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


def give_current_weather(res):
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


@bot.message_handler(commands=['start'])
def start_bot(message):
    welcome_text = "Some welcome text"
    bot.send_message(message.chat.id, welcome_text)


@bot.message_handler(content_types=["text"])
def user_message(message):
    url = f"https://api.openweathermap.org/data/2.5/weather?q={message.text}&appid={API_KEY}&units=metric"
    response = get(url).json()

    if response["cod"] == 200:
        current_weather = give_current_weather(response)
        bot.send_photo(message.chat.id, current_weather)

    else:
        error_message = "Some error text"
        bot.send_message(message.chat.id, error_message)


bot.infinity_polling()
