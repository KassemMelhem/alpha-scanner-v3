# -*- coding: utf-8 -*-
"""
Created on Fri Jul 24 14:12:47 2026

@author: kassem.melhem
"""

import requests
from config import FMP_API_KEY


BASE_URL="https://financialmodelingprep.com/api"


def get_profile(symbol):

    url = (
        f"{BASE_URL}/v3/profile/"
        f"{symbol}"
        f"?apikey={FMP_API_KEY}"
    )


    r=requests.get(url)

    if r.status_code != 200:
        return {}


    data=r.json()

    if len(data)==0:
        return {}


    return data[0]



def get_news(symbol):

    url=(
        f"{BASE_URL}/v3/stock_news"
        f"?tickers={symbol}"
        f"&limit=10"
        f"&apikey={FMP_API_KEY}"
    )


    r=requests.get(url)

    if r.status_code!=200:
        return []


    return r.json()