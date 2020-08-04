#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import re
import requests
import time
import random
import sqlite3
from telegram import ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

alarm_txt_prev = ['Хорошая новость!', 'Плохая новость!', 'Ого!', 'Шевелись!', 'Аларм!', 'Внимание!', 'Полундра!', 'Срочно!', 'Бип-биб!', 'Как тебе такое?', 'Дожили!', 'Алло!', 'Ты здесь?', 'Тут такое дело...', 'Вот ты и дождался!', 'Тссс...!', 'Кхе-кхе...', 'Докладываю!', 'Breaking news!', 'Ку-ку!', 'Короче, ']
USDTOD = 0
EURTOD = 0

def help_command(update, context):
	update.message.reply_text('Напиши название ценной бумаги для того чтобы найти её.\n/status - показать подписки\n/currency - курс валют')

def start(update, context):
	text = "Привет!\nЯ бот, следящий за курсом акций и валют. Моё предназначение это оперативное оповещение о том, что стоимость ценных бумаг падает после роста (или растёт после падения). Сейчас я помогу тебе потерять все свои деньги.\nВот что я умею:"
	reply_markup = ReplyKeyboardMarkup([[KeyboardButton('/status'), KeyboardButton('/help')]],resize_keyboard = True)
	updater.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup)
	help_command(update, context)

def currency_command(update, context):
	text = "USD: %.4f" % (USDTOD)
	text += "\n/sub_usd_fall - сообщить когда цена начнёт падать \U0001F4C9"
	text += "\n/sub_usd_rise - сообщить когда цена начнёт расти \U0001F4C8"
	text += "\nEUR: %.4f" % (EURTOD)
	text += "\n/sub_eur_fall - сообщить когда цена начнёт падать \U0001F4C9"
	text += "\n/sub_eur_rise - сообщить когда цена начнёт расти \U0001F4C8"
	update.message.reply_text(text)

def status_command(update, context):
	cursor.execute("SELECT t.code, type, refval, t.value FROM subscribe s JOIN ticker t ON t.id = s.ticker WHERE uid = %d ORDER BY class, t.code" % (update.effective_chat.id))
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
	cursor.execute("SELECT id, value FROM ticker WHERE code like '%s'" % (arg[0]))
	rows = cursor.fetchall()
	if len(rows) < 1:
		return
	ticker_id = rows[0][0]
	value = rows[0][1]
	dir = 1 if arg[1] == 'rise' else 0
	cursor.execute("INSERT OR REPLACE INTO subscribe (uid, ticker, type, refval, dt) VALUES(%d, %d, %d, (SELECT value FROM ticker WHERE id = %d), DATETIME(CURRENT_TIMESTAMP, 'localtime'))" % (update.effective_chat.id, ticker_id, dir, ticker_id))
	conn.commit()
	dirtxt = "расти" if dir else "падать"
	dirtrg = ">" if dir else "<"
	k = 1.0025 if dir else 0.9975
	update.message.reply_text("Текущая стоимость %s: %.4f\nЯ сообщю, когда цена начнёт %s\U0001F60F Триггер: %s%.4f" % (arg[0].upper(), value, dirtxt, dirtrg, value*k))

def unsubscribe_command(update, context):
	arg = update.message.text.replace('/unsub_', '').split('_')
	emoji = ['\U0001F910','\U0001F928','\U0001F610','\U0001F611','\U0001F636','\U0001F60F','\U0001F612','\U0001F644','\U0001F62C','\U0001F925','\U0001F637','\U0001F44C','\U0001F926']
	if arg[1] == 'rise':
		cursor.execute("DELETE FROM subscribe WHERE uid = %d AND ticker = (SELECT id FROM ticker WHERE code like '%s') AND type = 1" % (update.effective_chat.id, arg[0]))
		conn.commit()
		update.message.reply_text("Больше ни слова о росте %s %s" % (arg[0].upper(), random.choice(emoji)))
	if arg[1] == 'fall':
		cursor.execute("DELETE FROM subscribe WHERE uid = %d AND ticker = (SELECT id FROM ticker WHERE code like '%s') AND type = 0" % (update.effective_chat.id, arg[0]))
		conn.commit()
		update.message.reply_text("Больше ни слова о падении %s %s" % (arg[0].upper(), random.choice(emoji)))

def load_securities_from_moex(url, c):
	r = requests.get(url=url)
	data = r.json()
	q = ""
	for row in data['securities']['data']:
		if len(q) > 0:
			q += ', '
		r1 = row[1].replace('\'','\'\'')
		r2 = row[2].replace('\'','\'\'')
		q += "('%s','%s','%s','%s','%s', %d)" % (row[0], r1, r2, r1.upper(), r2.upper(), c)
	if len(q) > 0:
		q = "INSERT OR IGNORE INTO ticker (code, shortname, fullname, uc_shortname, uc_fullname, class) VALUES" + q
		cursor.execute(q)
	cursor.execute("CREATE TABLE IF NOT EXISTS subscribe (uid INTEGER, ticker INTEGER, type INTEGER, refval REAL, rate REAL, dt DATETIME, UNIQUE(uid, ticker, type))")
	conn.commit()

def update_prices(url):
	r = requests.get(url=url)
	data = r.json()
	for row in data['marketdata']['data']:
		if row[1] is not None:
			cursor.execute("UPDATE ticker SET value = %f, dt = DATETIME(CURRENT_TIMESTAMP, 'localtime') WHERE code = '%s'" % (row[1], row[0]))
	conn.commit()

def search(update, context):
	t = update.message.text
	if len(t) <= 3:
		fingers = ['\U0001F595', '\U0001F448 ', '\U0001F449 ', '\U0001F446 ', '\U0001F447 ', '\U0000261D ', '\U0001F44D ', '\U0001F44E']
		text = "Для поиска нужно минимум 4 символа! Считай: "
		for i in range(0, 4):
			text += random.choice(fingers)
		update.message.reply_text(text)
		return
	text = ""
	t = "%%" + t.upper() + "%%"
	cursor.execute("SELECT code, fullname, value FROM ticker WHERE code like ? OR uc_shortname like ? OR uc_fullname like ? AND value NOT NULL", (t, t, t))
	rows = cursor.fetchall()
	for row in rows:
		text += "%s: %.4f\n%s\n" % (row[0], row[2], row[1])
		text += "/sub_%s_fall - сообщить когда цена начнёт падать \U0001F4C9\n" % (row[0].lower())
		text += "/sub_%s_rise - сообщить когда цена начнёт расти \U0001F4C8\n\n" % (row[0].lower())
	if len(text) > 0:
		update.message.reply_text(text)
	else:
		update.message.reply_text("Увы, ничего не найдено! \U00000034\U0000FE0F\U000020E3\U0001F631\U00000034\U0000FE0F\U000020E3")

base_dir = os.path.dirname(__file__)
with open(os.path.join(base_dir, "config.json"), "r") as config_file:
	config = json.load(config_file)

conn = sqlite3.connect(os.path.join(base_dir, "data.db"), check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS ticker (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT, shortname TEXT, fullname TEXT, uc_shortname TEXT, uc_fullname TEXT, value REAL, class INTEGER, dt DATETIME, UNIQUE(code))")
cursor.execute("INSERT OR IGNORE INTO ticker (code, shortname, fullname, uc_shortname, uc_fullname, class) VALUES('USD', 'Dollar', 'Доллар США', 'DOLLAR', 'ДОЛЛАР США', 1)")
cursor.execute("INSERT OR IGNORE INTO ticker (code, shortname, fullname, uc_shortname, uc_fullname, class) VALUES('EUR', 'Euro', 'Евро', 'EURO', 'ЕВРО', 1)")
url = "https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities.json?iss.meta=off&iss.only=securities&securities.columns=SECID,SHORTNAME,SECNAME"
load_securities_from_moex(url, 2)
url = "https://iss.moex.com/iss/engines/stock/markets/bonds/boards/TQOB/securities.json?iss.meta=off&iss.only=securities&securities.columns=SECID,SHORTNAME,SECNAME"
load_securities_from_moex(url, 3)
url = "https://iss.moex.com/iss/engines/stock/markets/bonds/boards/TQCB/securities.json?iss.meta=off&iss.only=securities&securities.columns=SECID,SHORTNAME,SECNAME"
load_securities_from_moex(url, 3)

updater = Updater(token=config['TOKEN'], use_context=True)
dp = updater.dispatcher
dp.add_handler(CommandHandler("start", start))
dp.add_handler(CommandHandler("help", help_command))
dp.add_handler(CommandHandler("currency", currency_command))
dp.add_handler(CommandHandler("status", status_command))
dp.add_handler(MessageHandler(Filters.regex(r'^/sub'), subscribe_command))
dp.add_handler(MessageHandler(Filters.regex(r'^/unsub'), unsubscribe_command))
dp.add_handler(MessageHandler(Filters.text & ~Filters.command, search))
updater.start_polling()

url_currency = "https://iss.moex.com/iss/engines/currency/markets/selt/boards/CETS/securities.json?iss.meta=off&iss.only=marketdata&securities=USD000000TOD%2CEUR_RUB__TOD&marketdata.columns=SECID,LAST"
url_stocks = "https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities.json?iss.meta=off&iss.only=marketdata&marketdata.columns=SECID,LAST"
emoji = ['\U0001F600', '\U0001F603', '\U0001F604', '\U0001F601', '\U0001F606', '\U0001F605', '\U0001F923', '\U0001F602', '\U0001F642', '\U0001F643', '\U0001F609', '\U0001F60A', '\U0001F607', '\U0001F60B', '\U0001F61B', '\U0001F61C', '\U0001F92A', '\U0001F61D', '\U0001F911', '\U0001F92D', '\U0001F92B', '\U0001F914', '\U0001F922', '\U0001F92E', '\U0001F92E', '\U0001F927', '\U0001F975', '\U0001F976', '\U0001F974', '\U0001F635', '\U0001F92F', '\U0001F973', '\U0001F60E', '\U0001F4A9', '\U0001F648', '\U0001F649', '\U0001F64A', '\U0001F90F', '\U0001F91F', '\U0001F595', '\U0001F44D', '\U0001F44E', '\U0001F4AA', '\U0001F9E8', '\U0001F910','\U0001F928','\U0001F610','\U0001F611','\U0001F636','\U0001F60F','\U0001F612','\U0001F644','\U0001F62C','\U0001F925','\U0001F637','\U0001F44C','\U0001F926']
url_bonds_TQOB = "https://iss.moex.com/iss/engines/stock/markets/bonds/boards/TQOB/securities.json?iss.meta=off&iss.only=marketdata&marketdata.columns=SECID,LAST"
url_bonds_TQCB = "https://iss.moex.com/iss/engines/stock/markets/bonds/boards/TQCB/securities.json?iss.meta=off&iss.only=marketdata&marketdata.columns=SECID,LAST"
while 1:
	r = requests.get(url=url_currency)
	data = r.json()
	for row in data['marketdata']['data']:
		if row[0] == 'USD000000TOD' and row[1] is not None:
			USDTOD = row[1]
			cursor.execute("UPDATE ticker SET value = %f, dt = DATETIME(CURRENT_TIMESTAMP, 'localtime') WHERE code = 'USD'" % (USDTOD))
		if row[0] == 'EUR_RUB__TOD' and row[1] is not None:
			EURTOD = row[1]
			cursor.execute("UPDATE ticker SET value = %f, dt = DATETIME(CURRENT_TIMESTAMP, 'localtime') WHERE code = 'EUR'" % (EURTOD))
	update_prices(url_stocks)
	update_prices(url_bonds_TQOB)
	update_prices(url_bonds_TQCB)
	cursor.execute("UPDATE subscribe SET refval = (SELECT value FROM ticker WHERE id = subscribe.ticker) WHERE ticker = 1 AND type = 0 AND refval < (SELECT value FROM ticker WHERE id = subscribe.ticker)")
	cursor.execute("UPDATE subscribe SET refval = (SELECT value FROM ticker WHERE id = subscribe.ticker) WHERE ticker = 1 AND type = 1 AND refval > (SELECT value FROM ticker WHERE id = subscribe.ticker)")
	conn.commit()
	cursor.execute("SELECT uid, t.code, type, refval, t.value, ticker FROM subscribe s JOIN ticker t ON t.id = s.ticker WHERE type = 1 AND t.value > refval*1.0025 OR type = 0 AND t.value < refval*0.9975")
	rows = cursor.fetchall()
	for row in rows:
		dir = "вырос \U0001F4C8" if row[2] else "упал \U0001F4C9"
		dirn = "rise" if row[2] else "fall"
		text = "%s %s %s с %.4f до %.4f. %s Продолжить наблюдение: /sub_%s_%s" % (random.choice(alarm_txt_prev), row[1], dir, row[3], row[4], random.choice(emoji), row[1].lower(), dirn)
		updater.bot.send_message(chat_id=row[0], text=text)
		cursor.execute("DELETE FROM subscribe WHERE uid = %d AND ticker = %d AND type = %d" % (row[0], row[5], row[2]))
	conn.commit()
	time.sleep(60)
