import telebot
from telebot import types
from parser2 import pars_allnews, pars_news
from aiogram import Bot, Dispatcher
from aiogram.types import Message
import config
from PIL import Image
import httplib2
from io import BytesIO

# создаем экземпляр бота в aiogram
BOT = Bot(config.token)
dp = Dispatcher()

# Создаем экземпляр бота в telebot
bot = telebot.TeleBot(config.token)
active_users = {}


def gen_markup(list_btns):
    """Создает ряды кнопок по 4 в ряд"""
    n = len(list_btns)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if n > 4:
        markup.row_width = n // 2
        list_b = [types.KeyboardButton(btn) for btn in list_btns]
        half_list_b = list_b[:len(list_b) // 2 + 1]
        markup.add(*half_list_b)
        markup.add(*list_b[len(list_b) // 2 + 1:])
    else:
        markup.row_width = n
        list_b = [types.KeyboardButton(btn) for btn in list_btns]
        markup.add(*list_b)
    return markup


def send_start_menu(m):
    """Возможность переделать на подменю для новостей и сообщений"""
    markup = gen_markup(["Новости", "Сообщение"])
    bot.send_message(m.chat.id, "Что сделать?", reply_markup=markup)


def send_news_menu(message):
    msg = 'Вы подписаны на новости.' + "".join(
        ["\n" + s for s in config.subscribes.values()])
    bot.send_message(message.chat.id, msg)
    markup = gen_markup(config.subscribes.keys())
    bot.send_message(message.chat.id,
                     "Что показать? Или любое сообщение в чат", reply_markup=markup)


# Функция, обрабатывающая команду /start
@bot.message_handler(commands=["start", 'button'])
def start(m, res=False):
    print(m.chat.id, m.text)
    if m.chat.id in config.users:
        msg = 'Помощник готов к работе))\nВсе сообщения не из меню отправлю в чат'
        bot.send_message(m.chat.id, msg)
        send_news_menu(m)
    else:
        bot.send_message(m.chat.id, "Доступ к данному бот-сервису запрещен!")


def send_news(msg):
    url = config.subscribes.get(msg.text)
    answer = pars_allnews(url)[:2]
    for news in answer:
        bot.send_message(msg.chat.id, "<b>" + news.title + "</b>\n", parse_mode="Html")
        content = pars_news(news)
        for el in content:
            if el.startswith("http"):
                h = httplib2.Http('.cache')  # использует кеширование для ускорения загрузки
                response, cont = h.request(el)
                img = Image.open(BytesIO(cont))  # есть возможность обрабатывать изображения, уменьшать размер
                # response = requests.get(el)  # второй вариант без кеширования
                # img = Image.open(BytesIO(response.content))
                bot.send_photo(msg.chat.id, img)
            elif el:
                bot.send_message(msg.chat.id, el + "\n")
        if news != answer[-1]:
            bot.send_message(msg.chat.id, "---- next news ----" + "\n")


# Получение сообщений от юзера, здесь используем aiogram,
# так как в telebot я не нашел аналог message.html_text
@dp.message()
async def message_reply(message: Message):
    # печатаем для проверки номер id чата, текст с форматированием и тип содержимого апдейта
    print(message.chat.id, message.html_text, message.content_type)
    # если номер чата совпадает с номером в файле config
    if message.chat.id in config.users:
        # если текст апдейта совпадает с подписками
        if message.text in config.subscribes:
            # вызываем функцию send_news()
            send_news(message)
        # если нет, то проверяем апдейт, если в нем фото, то отправляем фото, если текст, то отпрвляем
        # на канал текст
        else:
            if message.content_type == 'photo':
                # ловим текст из caption с его форматированием
                a = message.html_text
                # отправляем картинку с caption
                await BOT.send_photo(config.chat_id, message.photo[0].file_id, caption=a, parse_mode='HTML')
            else:
                await BOT.send_message(config.chat_id, message.html_text, parse_mode='HTML')
    else:
        msg = "Доступ к данному бот-сервису запрещен!"
        # для удаления кнопок
        reply_markup = types.ReplyKeyboardRemove()
        bot.send_message(message.chat.id, msg, reply_markup=reply_markup)


# Запускаем бота
if __name__ == '__main__':
    dp.run_polling(BOT)
    bot.polling(none_stop=True, timeout=123)
