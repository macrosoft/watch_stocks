#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import re
import requests
import time
import threading
import random
import sqlite3
from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters

alarm_txt_prev = ['Хорошая новость!', 'Плохая новость!', 'Ого!', 'Шевелись!', 'Аларм!', 'Внимание!', 'Полундра!', 'Срочно!', 'Бип-биб!', 'Как тебе такое?', 'Дожили!', 'Алло!', 'Ты здесь?', 'Тут такое дело...', 'Вот ты и дождался!', 'Тссс...!', 'Кхе-кхе...', 'Докладываю!', 'Breaking news!', 'Ку-ку!', 'Короче,', 'Ты этого хотел?', 'Shit happens!', 'Ты сейчас умрёшь!']
emoji = ['\U0001F600', '\U0001F603', '\U0001F604', '\U0001F601', '\U0001F606', '\U0001F605', '\U0001F923', '\U0001F602', '\U0001F642', '\U0001F643', '\U0001F609', '\U0001F60A', '\U0001F607', '\U0001F60B', '\U0001F61B', '\U0001F61C', '\U0001F92A', '\U0001F61D', '\U0001F911', '\U0001F92D', '\U0001F92B', '\U0001F914', '\U0001F922', '\U0001F92E', '\U0001F92E', '\U0001F927', '\U0001F975', '\U0001F976', '\U0001F974', '\U0001F635', '\U0001F92F', '\U0001F973', '\U0001F60E', '\U0001F4A9', '\U0001F648', '\U0001F649', '\U0001F64A', '\U0001F90F', '\U0001F91F', '\U0001F595', '\U0001F44D', '\U0001F44E', '\U0001F4AA', '\U0001F9E8', '\U0001F910','\U0001F928','\U0001F610','\U0001F611','\U0001F636','\U0001F60F','\U0001F612','\U0001F644','\U0001F62C','\U0001F925','\U0001F637','\U0001F44C','\U0001F926']
USDTOD = 0
EURTOD = 0
lock = threading.Lock()

def select(q):
	try:
		lock.acquire(True)
		cursor.execute(q)
	finally:
		lock.release()
	return cursor.fetchall()

def help_command(update, context):
	update.message.reply_text('Напиши название ценной бумаги для того чтобы найти её.\n/status - показать подписки\n/currency - курс валют')

def start(update, context):
	text = "Привет!\nЯ бот, следящий за курсом акций и валют. Моё предназначение это оперативное оповещение о том, что стоимость ценных бумаг падает после роста (или растёт после падения). Сейчас я помогу тебе потерять все свои деньги.\nВот что я умею:"
	reply_markup = ReplyKeyboardMarkup([[KeyboardButton('/status'), KeyboardButton('/help')]],resize_keyboard = True)
	updater.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup)
	help_command(update, context)

def currency_command(update, context):
	text = "USD: %.4f" % (USDTOD)
	text += "\n/show_usd - подробнее"
	text += "\nEUR: %.4f" % (EURTOD)
	text += "\n/show_eur - подробнее"
	update.message.reply_text(text)

def status_command(update, context):
	rows = select("SELECT t.code, type, refval, t.value FROM subscribe s JOIN ticker t ON t.id = s.ticker WHERE uid = %d ORDER BY class, t.code" % (update.effective_chat.id))
	text = "Действующих подписок нет \U0001F610"
	if len(rows) > 0:
		text = "Твои подписки:\n"
		for row in rows:
			dir = "Рост \U0001F4C8" if row[1] else "Падение \U0001F4C9"
			tdir = ">" if row[1] else "<"
			t = row[2]*1.0025 if row[1] else row[2]*0.9975
			text += "%s %s: %.4f (%s%.4f)\nПодробнее: /show_%s\n" % (dir, row[0], row[3], tdir, t, row[0].lower())
	else:
		rows = select("SELECT code, fullname FROM ticker  WHERE value NOT NULL ORDER BY random() LIMIT 1")
		for row in rows:
			text += "\n\nМогу предложить подписаться на:\n"
			text += "%s %s\n" % (row[1], random.choice(emoji))
			text += "/show_%s - подробнее\n\n" % (row[0].lower())
	update.message.reply_text(text)

def subscribe(ticker, type, update):
	rows = select("SELECT id, value FROM ticker WHERE code like '%s'" % (ticker))
	if len(rows) < 1:
		return
	ticker_id = rows[0][0]
	value = rows[0][1]
	dir = 1 if type == 'rise' else 0
	try:
		lock.acquire(True)
		cursor.execute("INSERT OR REPLACE INTO subscribe (uid, ticker, type, refval, dt) VALUES(%d, %d, %d, (SELECT value FROM ticker WHERE id = %d), DATETIME(CURRENT_TIMESTAMP, 'localtime'))" % (update.effective_chat.id, ticker_id, dir, ticker_id))
		conn.commit()
	finally:
		lock.release()
	dirtxt = "расти" if dir else "падать"
	dirtrg = ">" if dir else "<"
	k = 1.0025 if dir else 0.9975
	updater.bot.send_message(update.effective_chat.id, text="Текущая стоимость %s: %.4f\nЯ сообщю, когда цена начнёт %s\U0001F60F Триггер: %s%.4f" % (ticker.upper(), value, dirtxt, dirtrg, value*k))

def subscribe_command(update, context):
	arg = update.message.text.replace('/sub_', '').split('_')
	subscribe(arg[0], arg[1], update)

def unsubscribe_command(update, context):
	arg = update.message.text.replace('/unsub_', '').split('_')
	emoji = ['\U0001F910','\U0001F928','\U0001F610','\U0001F611','\U0001F636','\U0001F60F','\U0001F612','\U0001F644','\U0001F62C','\U0001F925','\U0001F637','\U0001F44C','\U0001F926']
	try:
		lock.acquire(True)
		if arg[1] == 'rise':
			cursor.execute("DELETE FROM subscribe WHERE uid = %d AND ticker = (SELECT id FROM ticker WHERE code like '%s') AND type = 1" % (update.effective_chat.id, arg[0]))
			conn.commit()
			update.message.reply_text("Больше ни слова о росте %s %s" % (arg[0].upper(), random.choice(emoji)))
		if arg[1] == 'fall':
			cursor.execute("DELETE FROM subscribe WHERE uid = %d AND ticker = (SELECT id FROM ticker WHERE code like '%s') AND type = 0" % (update.effective_chat.id, arg[0]))
			conn.commit()
			update.message.reply_text("Больше ни слова о падении %s %s" % (arg[0].upper(), random.choice(emoji)))
	finally:
		lock.release()

def show_command(update, context):
	arg = update.message.text.replace('/show_', '').split('_')
	rows = select("SELECT id, code, fullname, value, class FROM ticker WHERE code like '%s'" % (arg[0]))
	if len(rows) < 1:
		return
	row = rows[0]
	id = row[0]
	ticker = row[1]
	c = ['','валюта', 'акция', 'облигация'][row[4]]
	text = "%s (%s): %.4f\n%s\n" % (row[1], c, row[3], row[2])
	rows = select("SELECT t, type FROM (SELECT 1 t UNION SELECT 0) tt LEFT JOIN subscribe s ON s.type = tt.t AND uid = %d AND ticker = %d ORDER BY t" % (update.effective_chat.id, id))
	for row in rows:
		if row[0] == 0:
			if row[1] is None:
				text += "/sub_%s_fall - сообщить когда цена начнёт падать \U0001F4C9\n" % (ticker.lower())
			else:
				text += "/unsub_%s_fall - не следить за падением цены \U0001F4C9\n" % (ticker.lower())
		else:
			if row[1] is None:
				text += "/sub_%s_rise - сообщить когда цена начнёт расти \U0001F4C8\n" % (ticker.lower())
			else:
				text += "/unsub_%s_rise - не следить за ростом цены \U0001F4C8\n" % (ticker.lower())
	update.message.reply_text(text)

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
	try:
		lock.acquire(True)
		cursor.execute("SELECT code, fullname, value FROM ticker WHERE code like ? OR uc_shortname like ? OR uc_fullname like ? AND value NOT NULL LIMIT 5", (t, t, t))
		rows = cursor.fetchall()
	finally:
		lock.release()
	for row in rows:
		text += "%s: %.4f\n%s\n" % (row[0], row[2], row[1])
		text += "/show_%s - подробнее\n\n" % (row[0].lower())
	if len(text) > 0:
		update.message.reply_text(text)
	else:
		update.message.reply_text("Увы, ничего не найдено! \U00000034\U0000FE0F\U000020E3\U0001F631\U00000034\U0000FE0F\U000020E3")

def button_press(update, context):
	query = update.callback_query
	arg = query.data.replace('sub_', '').split('_')
	subscribe(arg[0], arg[1], update)
	query.answer()

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
cursor.execute("CREATE TABLE IF NOT EXISTS subscribe (uid INTEGER, ticker INTEGER, type INTEGER, refval REAL, rate REAL, dt DATETIME, UNIQUE(uid, ticker, type))")
conn.commit()

updater = Updater(token=config['TOKEN'], use_context=True)
dp = updater.dispatcher
dp.add_handler(CommandHandler("start", start))
dp.add_handler(CommandHandler("help", help_command))
dp.add_handler(CommandHandler("currency", currency_command))
dp.add_handler(CommandHandler("status", status_command))
dp.add_handler(MessageHandler(Filters.regex(r'^/sub'), subscribe_command))
dp.add_handler(MessageHandler(Filters.regex(r'^/unsub'), unsubscribe_command))
dp.add_handler(MessageHandler(Filters.regex(r'^/show'), show_command))
dp.add_handler(MessageHandler(Filters.text & ~Filters.command, search))
updater.dispatcher.add_handler(CallbackQueryHandler(button_press))
updater.start_polling()

url_currency = "https://iss.moex.com/iss/engines/currency/markets/selt/boards/CETS/securities.json?iss.meta=off&iss.only=marketdata&securities=USD000000TOD%2CEUR_RUB__TOD&marketdata.columns=SECID,LAST"
url_stocks = "https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities.json?iss.meta=off&iss.only=marketdata&marketdata.columns=SECID,LAST"
url_bonds_TQOB = "https://iss.moex.com/iss/engines/stock/markets/bonds/boards/TQOB/securities.json?iss.meta=off&iss.only=marketdata&marketdata.columns=SECID,LAST"
url_bonds_TQCB = "https://iss.moex.com/iss/engines/stock/markets/bonds/boards/TQCB/securities.json?iss.meta=off&iss.only=marketdata&marketdata.columns=SECID,LAST"
while 1:
	r = requests.get(url=url_currency)
	data = r.json()
	try:
		lock.acquire(True)
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
		cursor.execute("UPDATE subscribe SET refval = (SELECT value FROM ticker WHERE id = subscribe.ticker) WHERE type = 0 AND refval < (SELECT value FROM ticker WHERE id = subscribe.ticker)")
		cursor.execute("UPDATE subscribe SET refval = (SELECT value FROM ticker WHERE id = subscribe.ticker) WHERE type = 1 AND refval > (SELECT value FROM ticker WHERE id = subscribe.ticker)")
		conn.commit()
		cursor.execute("SELECT uid, t.code, type, refval, t.value, ticker FROM subscribe s JOIN ticker t ON t.id = s.ticker WHERE type = 1 AND t.value > refval*1.0025 OR type = 0 AND t.value < refval*0.9975")
		rows = cursor.fetchall()
		for row in rows:
			dir = "вырос \U0001F4C8" if row[2] else "упал \U0001F4C9"
			dirn = "rise" if row[2] else "fall"
			text = "%s %s %s с %.4f до %.4f. %s" % (random.choice(alarm_txt_prev), row[1], dir, row[3], row[4], random.choice(emoji))
			keyboard = [[InlineKeyboardButton("Продолжить наблюдение \U0001F575", callback_data="sub_%s_%s" % (row[1].lower(), dirn))]]
			reply_markup = InlineKeyboardMarkup(keyboard)
			updater.bot.send_message(chat_id=row[0], text=text, reply_markup=reply_markup)
			cursor.execute("DELETE FROM subscribe WHERE uid = %d AND ticker = %d AND type = %d" % (row[0], row[5], row[2]))
		conn.commit()
	finally:
		lock.release()
	time.sleep(60)
