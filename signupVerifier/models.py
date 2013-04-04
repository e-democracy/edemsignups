# coding=utf-8

from google.appengine.ext import db

class EmailReference(db.Model):
    address = db.StringProperty(required = True)
    spreadsheet = db.StringProperty(required = True)
    worksheet = db.StringProperty(required = True)
    created = db.DateTimeProperty(required = True, auto_now_add = True)
