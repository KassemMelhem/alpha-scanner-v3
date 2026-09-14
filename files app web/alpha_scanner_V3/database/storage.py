# -*- coding: utf-8 -*-
"""
Created on Fri Jul 24 15:01:24 2026

@author: kassem.melhem
"""

import sqlite3
from config import DATABASE_PATH



def save_results(df):

    conn=sqlite3.connect(
        DATABASE_PATH
    )


    df.to_sql(
        "alpha_scores",
        conn,
        if_exists="append",
        index=False
    )


    conn.close()