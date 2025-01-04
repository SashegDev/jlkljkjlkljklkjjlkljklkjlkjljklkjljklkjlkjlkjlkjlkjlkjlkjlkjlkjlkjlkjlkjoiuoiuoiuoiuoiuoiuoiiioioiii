import telebot

# Функция для регистрации команд
def register_commands(bot):
    """
    гдкиппер дей билайк:
    ТРЕПЕЩИ ПЕРРИ ХУЕСОС!!
    FishWithEggs.jpg
    """
    
    @bot.message_handler(commands=['hello'])
    def hello_command(message):
        bot.send_message(message.chat.id, "Привет! Как дела?")

    @bot.message_handler(commands=['help'])
    def help_command(message):
        bot.send_message(message.chat.id, "Доступные команды: /hello, /help, /pingall, /ping")