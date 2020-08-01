#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import requests
import time

url = "https://iss.moex.com/iss/engines/currency/markets/selt/securities.json?iss.meta=off&iss.only=securities%2Cmarketdata&securities=USD000000TOD"
while 1:
	r = requests.get(url=url)
	data = r.json()
	print(data['marketdata']['data'][0][8])
	time.sleep(5)
