#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import requests
import time
import random
import sqlite3
from telegram import ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

alarm_txt_prev = ['Хорошая новость!', 'Плохая новость!', 'Ого!', 'Шевелись!', 'Аларм!', 'Внимание!', 'Полундра!', 'Срочно!', 'Бип-биб!', 'Как тебе такое?', 'Дожили!', 'Алло!', 'Ты здесь?', 'Тут такое дело...', 'Вот ты и дождался!', 'Тссс...!', 'Кхе-кхе...', 'Докладываю!', 'Breaking news!']
USDTOD = 0
EURTOD = 0

def help_command(update, context):
	update.message.reply_text('/status - показать подписки\n/currency - курс валют')

def start(update, context):
	text = "Привет!\nЯ бот, следящий за курсом акций и валют. Моё предназначение это оперативное оповещение о том, что стоимость ценных бумаг падает после роста (или растёт после падения). Сейчас я помогу тебе потерять все свои деньги.\nВот что я умею:"
	reply_markup = ReplyKeyboardMarkup([[KeyboardButton('/status'), KeyboardButton('/help')]],resize_keyboard = True)
	updater.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup)
	help_command(update, context)

def currency_command(update, context):
	text = "USD: %.4f" % (USDTOD)
	text += "\n /sub_usd_fall - сообщить когда цена начнёт падать \U0001F4C9"
	text += "\n /sub_usd_rise - сообщить когда цена начнёт расти \U0001F4C8"
	text += "\nEUR: %.4f" % (EURTOD)
	text += "\n /sub_eur_fall - сообщить когда цена начнёт падать \U0001F4C9"
	text += "\n /sub_eur_rise - сообщить когда цена начнёт расти \U0001F4C8"
	update.message.reply_text(text)

def status_command(update, context):
	cursor.execute("SELECT t.name, direction, refval, t.value FROM subscribe s JOIN ticker t ON t.id = s.ticker WHERE uid = %d" % (update.effective_chat.id))
	rows = cursor.fetchall()
	text = "Действующих подписок нет \U0001F610"
	if len(rows) > 0:
		text = "Твои подписки:\n"
		for row in rows:
			dir = "Рост \U0001F4C8" if row[1] else "Падение \U0001F4C9"
			tdir = ">" if row[1] else "<"
			t = row[2]*1.0025 if row[1] else row[2]*0.9975
			dirn = "rise" if row[1] else "fall"
			text += "%s %s: %.4f (%s%.4f)\nОтписаться: /unsub_%s_%s\n" % (dir, row[0], row[3], tdir, t, row[0].lower(), dirn)
	update.message.reply_text(text)

def subscribe_command(update, context):
	arg = update.message.text.replace('/sub_', '').split('_')
	cursor.execute("SELECT id, value FROM ticker WHERE name like '%s'" % (arg[0]))
	rows = cursor.fetchall()
	if len(rows) < 1:
		return
	ticker_id = rows[0][0]
	value = rows[0][1]
	dir = 1 if arg[1] == 'rise' else 0
	cursor.execute("INSERT OR REPLACE INTO subscribe (uid, ticker, direction, refval, dt) VALUES(%d, %d, %d, (SELECT value FROM ticker WHERE id = %d), DATETIME(CURRENT_TIMESTAMP, 'localtime'))" % (update.effective_chat.id, ticker_id, dir, ticker_id))
	conn.commit()
	dirtxt = "расти" if dir else "падать"
	dirtrg = ">" if dir else "<"
	k = 1.0025 if dir else 0.9975
	update.message.reply_text("Текущая стоимость %s: %.4f\nЯ сообщю, когда цена начнёт %s\U0001F60F Триггер: %s%.4f" % (arg[0].upper(), value, dirtxt, dirtrg, value*k))

def unsubscribe_command(update, context):
	arg = update.message.text.replace('/unsub_', '').split('_')
	emoji = ['\U0001F910','\U0001F928','\U0001F610','\U0001F611','\U0001F636','\U0001F60F','\U0001F612','\U0001F644','\U0001F62C','\U0001F925','\U0001F637','\U0001F44C','\U0001F926']
	if arg[1] == 'rise':
		cursor.execute("DELETE FROM subscribe WHERE uid = %d AND ticker = (SELECT id FROM ticker WHERE name like '%s') AND direction = 1" % (update.effective_chat.id, arg[0]))
		conn.commit()
		update.message.reply_text("Больше ни слова о росте %s %s" % (arg[0].upper(), random.choice(emoji)))
	if arg[1] == 'fall':
		cursor.execute("DELETE FROM subscribe WHERE uid = %d AND ticker = (SELECT id FROM ticker WHERE name like '%s') AND direction = 0" % (update.effective_chat.id, arg[0]))
		conn.commit()
		update.message.reply_text("Больше ни слова о падении %s %s" % (arg[0].upper(), random.choice(emoji)))

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
dp.add_handler(CommandHandler("currency", currency_command))
dp.add_handler(CommandHandler("status", status_command))
dp.add_handler(MessageHandler(Filters.regex(r'^/sub'), subscribe_command))
dp.add_handler(MessageHandler(Filters.regex(r'^/unsub'), unsubscribe_command))
dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
updater.start_polling()

url = "https://iss.moex.com/iss/engines/currency/markets/selt/securities.json?iss.meta=off&iss.only=securities%2Cmarketdata&securities=USD000000TOD%2CEUR_RUB__TOD"
emoji = ['\U0001F600', '\U0001F603', '\U0001F604', '\U0001F601', '\U0001F606', '\U0001F605', '\U0001F923', '\U0001F602', '\U0001F642', '\U0001F643', '\U0001F609', '\U0001F60A', '\U0001F607', '\U0001F60B', '\U0001F61B', '\U0001F61C', '\U0001F92A', '\U0001F61D', '\U0001F911', '\U0001F92D', '\U0001F92B', '\U0001F914', '\U0001F922', '\U0001F92E', '\U0001F92E', '\U0001F927', '\U0001F975', '\U0001F976', '\U0001F974', '\U0001F635', '\U0001F92F', '\U0001F973', '\U0001F60E', '\U0001F4A9', '\U0001F648', '\U0001F649', '\U0001F64A', '\U0001F90F', '\U0001F91F', '\U0001F595', '\U0001F44D', '\U0001F44E', '\U0001F4AA', '\U0001F9E8', '\U0001F910','\U0001F928','\U0001F610','\U0001F611','\U0001F636','\U0001F60F','\U0001F612','\U0001F644','\U0001F62C','\U0001F925','\U0001F637','\U0001F44C','\U0001F926']
while 1:
	r = requests.get(url=url)
	data = r.json()
	EURTOD = data['marketdata']['data'][0][8]
	USDTOD = data['marketdata']['data'][1][8]
	cursor.execute("UPDATE ticker SET value = %f, dt = DATETIME(CURRENT_TIMESTAMP, 'localtime') WHERE id = 1" % (USDTOD))
	cursor.execute("UPDATE ticker SET value = %f, dt = DATETIME(CURRENT_TIMESTAMP, 'localtime') WHERE id = 2" % (EURTOD))
	cursor.execute("UPDATE subscribe SET refval = %f WHERE ticker = 1 AND direction = 0 AND refval < %f" % (USDTOD, USDTOD))
	cursor.execute("UPDATE subscribe SET refval = %f WHERE ticker = 1 AND direction = 1 AND refval > %f" % (USDTOD, USDTOD))
	cursor.execute("SELECT uid, t.name, direction, refval, t.value, ticker FROM subscribe s JOIN ticker t ON t.id = s.ticker WHERE direction = 1 AND t.value > refval*1.0025 OR direction = 0 AND t.value < refval*0.9975")
	rows = cursor.fetchall()
	for row in rows:
		dir = "вырос \U0001F4C8" if row[2] else "упал \U0001F4C9"
		dirn = "rise" if row[2] else "fall"
		text = "%s %s %s с %.4f до %.4f. %s Продолжить наблюдение: /sub_%s_%s" % (random.choice(alarm_txt_prev), row[1], dir, row[3], row[4], random.choice(emoji), row[1].lower(), dirn)
		updater.bot.send_message(chat_id=row[0], text=text)
		cursor.execute("DELETE FROM subscribe WHERE uid = %d AND ticker = %d AND direction = %d" % (row[0], row[5], row[2]))
	conn.commit()
	time.sleep(60)
