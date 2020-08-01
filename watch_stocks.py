#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import requests
import time

from telegram.ext import Updater, CommandHandler,  MessageHandler, Filters
USDTOD = 0

def help_command(update, context):
	update.message.reply_text('/price - текущая цена')

def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Привет! Я бот следящий за курсом акций и валют. Вот что я умею (или скоро научусь):")
    help_command(update, context)

def price_command(update, context):
    update.message.reply_text("USD: %.4f" % (USDTOD))

def echo(update, context):
    help_command(update, context)

base_dir = os.path.dirname(__file__)
with open(os.path.join(base_dir, "config.json"), "r") as config_file:
    config = json.load(config_file)

updater = Updater(token=config['TOKEN'], use_context=True)
dp = updater.dispatcher
dp.add_handler(CommandHandler("start", start))
dp.add_handler(CommandHandler("help", help_command))
dp.add_handler(CommandHandler("price", price_command))
dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
updater.start_polling()

url = "https://iss.moex.com/iss/engines/currency/markets/selt/securities.json?iss.meta=off&iss.only=securities%2Cmarketdata&securities=USD000000TOD"
while 1:
	r = requests.get(url=url)
	data = r.json()
	USDTOD = data['marketdata']['data'][0][8]
	time.sleep(60)
