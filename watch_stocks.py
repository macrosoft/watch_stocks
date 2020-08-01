#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import requests
import time

base_dir = os.path.dirname(__file__)
with open(os.path.join(base_dir, "config.json"), "r") as config_file:
    config = json.load(config_file)

url = "https://iss.moex.com/iss/engines/currency/markets/selt/securities.json?iss.meta=off&iss.only=securities%2Cmarketdata&securities=USD000000TOD"
while 1:
	r = requests.get(url=url)
	data = r.json()
	print(data['marketdata']['data'][0][8])
	time.sleep(5)
