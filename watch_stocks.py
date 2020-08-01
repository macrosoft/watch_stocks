#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import requests
import time
import random
import sqlite3

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

alarm_txt_prev = ['Хорошая новость!', 'Плохая новость!', 'Ого!', 'Шевелись!', 'Аларм!', 'Внимание!', 'Полундра!', 'Срочно!', 'Бип-биб!', 'Как тебе такое?', 'Дожили!', 'Алло!', 'Ты здесь?', 'Тут такое дело...', 'Вот ты и дождался!']
USDTOD = 0

def help_command(update, context):
	update.message.reply_text('/help - вывести список команд (этот)\n/status - показать подписки\n/price - курс доллара')

def start(update, context):
	context.bot.send_message(chat_id=update.effective_chat.id, text="Привет!\nЯ бот, следящий за курсом акций и валют. Моё предназначение это оперативное оповещение о том, что стоимость ценных бумаг падает после роста (или растёт после падения). Сейчас я помогу тебе потерять все свои деньги.\nВот что я умею:")
	help_command(update, context)

def price_command(update, context):
	text = "USD: %.4f" % (USDTOD)
	text += "\n /sub_usd_fall - сообщить когда цена начнет падать"
	text += "\n /sub_usd_rise - сообщить когда цена начнет расти"
	update.message.reply_text(text)

def status_command(update, context):
	cursor.execute("SELECT t.name, direction, refval, t.value FROM subscribe s JOIN ticker t ON t.id = s.ticker WHERE uid = %d" % (update.effective_chat.id))
	rows = cursor.fetchall()
	text = "Действующих подписок нет :("
	if len(rows) > 0:
		text = "Твои подписки:\n"
		for row in rows:
			dir = "Рост" if row[1] else "Падение"
			tdir = ">" if row[1] else "<"
			t = row[2]*1.0025 if row[1] else row[2]*0.9975
			dirn = "rise" if row[1] else "fall"
			text += "%s %s: %.4f (%s%.4f)\nОтписаться: /unsub_%s_%s\n" % (dir, row[0], row[3], tdir, t, row[0].lower(), dirn)
	update.message.reply_text(text)

def subscribe_command(update, context):
	arg = update.message.text.replace('/sub_', '').split('_')
	if arg[0] != 'usd':
		return
	if arg[1] == 'rise':
		cursor.execute("INSERT OR REPLACE INTO subscribe (uid, ticker, direction, refval, dt) VALUES(%d, %d, %d, %f, DATETIME(CURRENT_TIMESTAMP, 'localtime'))" % (update.effective_chat.id, 1, 1, USDTOD))
		conn.commit()
		update.message.reply_text("Текущая стоимость USD: %.4f\nЯ сообщю, когда цена начнёт расти. Триггер: >%.4f" % (USDTOD, USDTOD*1.0025))
	if arg[1] == 'fall':
		cursor.execute("INSERT OR REPLACE INTO subscribe (uid, ticker, direction, refval, dt) VALUES(%d, %d, %d, %f, DATETIME(CURRENT_TIMESTAMP, 'localtime'))" % (update.effective_chat.id, 1, 0, USDTOD))
		conn.commit()
		update.message.reply_text("Текущая стоимость USD: %.4f\nЯ сообщю, когда цена начнёт падать. Триггер: <%.4f" % (USDTOD, USDTOD*0.9975))

def unsubscribe_command(update, context):
	arg = update.message.text.replace('/unsub_', '').split('_')
	if arg[0] != 'usd':
		return
	if arg[1] == 'rise':
		cursor.execute("DELETE FROM subscribe WHERE uid = %d AND ticker = 1 AND direction = 1" % (update.effective_chat.id))
		conn.commit()
		update.message.reply_text("Больше ни слова о росте USD")
	if arg[1] == 'fall':
		cursor.execute("DELETE FROM subscribe WHERE uid = %d AND ticker = 1 AND direction = 0" % (update.effective_chat.id))
		conn.commit()
		update.message.reply_text("Больше ни слова о падении USD")

def echo(update, context):
	help_command(update, context)

base_dir = os.path.dirname(__file__)
with open(os.path.join(base_dir, "config.json"), "r") as config_file:
	config = json.load(config_file)

conn = sqlite3.connect(os.path.join(base_dir, "data.db"), check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS ticker (id INTEGER PRIMARY KEY, name TEXT, value REAL, dt DATETIME)")
for t in config["tickers"]:
	cursor.execute("INSERT OR REPLACE INTO ticker (id, name) VALUES(%d, '%s')" % (t['id'], t['name']))
cursor.execute("CREATE TABLE IF NOT EXISTS subscribe (uid INTEGER, ticker INTEGER, direction BOOLEAN, refval REAL, dt DATETIME, UNIQUE(uid, ticker, direction))")
conn.commit()

updater = Updater(token=config['TOKEN'], use_context=True)
dp = updater.dispatcher
dp.add_handler(CommandHandler("start", start))
dp.add_handler(CommandHandler("help", help_command))
dp.add_handler(CommandHandler("price", price_command))
dp.add_handler(CommandHandler("status", status_command))
dp.add_handler(MessageHandler(Filters.regex(r'^/sub'), subscribe_command))
dp.add_handler(MessageHandler(Filters.regex(r'^/unsub'), unsubscribe_command))
dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
updater.start_polling()

url = "https://iss.moex.com/iss/engines/currency/markets/selt/securities.json?iss.meta=off&iss.only=securities%2Cmarketdata&securities=USD000000TOD"
while 1:
	r = requests.get(url=url)
	data = r.json()
	USDTOD = data['marketdata']['data'][0][8]
	cursor.execute("UPDATE ticker SET value = %f, dt = DATETIME(CURRENT_TIMESTAMP, 'localtime') WHERE id = 1" % (USDTOD))
	cursor.execute("UPDATE subscribe SET refval = %f WHERE ticker = 1 AND direction = 0 AND refval < %f" % (USDTOD, USDTOD))
	cursor.execute("UPDATE subscribe SET refval = %f WHERE ticker = 1 AND direction = 1 AND refval > %f" % (USDTOD, USDTOD))
	cursor.execute("SELECT uid, t.name, direction, refval, t.value, ticker FROM subscribe s JOIN ticker t ON t.id = s.ticker WHERE direction = 1 AND t.value > refval*1.0025 OR direction = 0 AND t.value < refval*0.9975")
	rows = cursor.fetchall()
	for row in rows:
		dir = "вырос" if row[2] else "упал"
		dirn = "rise" if row[2] else "fall"
		text = "%s %s %s с %.4f до %.4f. Продолжить наблюдение: /sub_%s_%s" % (random.choice(alarm_txt_prev), row[1], dir, row[3], row[4], row[1].lower(), dirn)
		updater.bot.send_message(chat_id=row[0], text=text)
		cursor.execute("DELETE FROM subscribe WHERE uid = %d AND ticker = %d AND direction = %d" % (row[0], row[5], row[2]))
	conn.commit()
	time.sleep(60)
