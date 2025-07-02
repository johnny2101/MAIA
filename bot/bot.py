import json
import os
import traceback

import telebot
from core.message_broker import MessageConsumer, MessagePublisher
import threading

#BOT_TOKEN = os.environ.get('TELEGRAM_BOT')
BOT_TOKEN = "7154713347:AAG2MzuvFwT0JUNlvaOEVZ9bosj0ZWwEP4U"

input_topic = "user.message.new"
output_topic = "user.message.processed"
stop_event = threading.Event()
listener_thread = None

bot = telebot.TeleBot(BOT_TOKEN)
config = {
    'host': 'localhost',
    'port': 5672,
    'username': 'admin',
    'password': 'password',
    'virtual_host': '/'
}
message_publisher = MessagePublisher(config)
message_consumer = MessageConsumer(config)
if not message_publisher.connect() or not message_consumer.connect():
    print("Failed to connect to RabbitMQ")
    exit(1)
    
    
def listen_to_user_messages():
    """
    Sottoscrive ai messaggi utente e gestisce i messaggi ricevuti.
    """

    def user_message_callback(**kwargs):
        try:
            ch, method, properties, body = kwargs['ch'], kwargs['method'], kwargs['properties'], kwargs['body']
        except KeyError as e:
            message_publisher.publish("Bot.log.error", f"[Bot] Error unpacking message: {e}")
            return
        
        if stop_event.is_set():
            ch.stop_consuming()
            return
        payload = body
        message_publisher.publish("Bot.log.info", payload)
        chat_id = payload.get("chat_id")
        response_text = payload.get("text", "no message found")
        
        
        bot.send_message(chat_id, response_text)

    try:
        message_consumer.subscribe("user.message.processed", user_message_callback)
    except Exception as e:
        message_publisher.publish("Bot.log.error", f"[Bot] Error while listening to messages: {e}")
        
            
def stop_listening():
    """
    Ferma l'ascolto dei messaggi utente.
    """
    global listener_thread
    stop_event.set()
    message_consumer.disconnect()
    message_publisher.disconnect()

@bot.message_handler(commands=['start', 'hello'])
def send_welcome(message):
    bot.reply_to(message, "Howdy, how are you doing?")

@bot.message_handler(func=lambda msg: True, content_types=['text'])
def handle_text_message(message):
    payload = {
        'chat_id': message.chat.id,
        'text': message.text
    }
    message_publisher.publish("Bot.log.info", payload)
    message_publisher.publish(input_topic, payload)
    #message_publisher.publish("Bot.log.info", json.dumps(payload))
    

try:
    listen_to_user_messages()
    print("Listening... Press Ctrl+C to stop.")
    bot.infinity_polling()
except KeyboardInterrupt:
    print("Interrupted. Shutting down cleanly...")
    stop_listening()
    exit(0)