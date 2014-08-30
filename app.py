# -*- coding:utf8 -*-
import setting
from flask import Flask

app = Flask(__name__)
app.secret_key = setting.SESSION_KEY

@app.route('/')
def home():
    return u'Hello world'
