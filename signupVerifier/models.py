# coding=utf-8

from google.appengine.ext import db

# Spreadsheet
#   gsid
#   staff_name
#   staff_email
#   event_name
#   event_date
#   event_location
#   scanned - datetime

# Spreadsheet Change
#   gsid
#   prev_gsid

# Person
#   pid
#   Various Fields
#   source_gsid

# Person Change
#   pid
#   prev_pid

# Opt-Out Token
#   token
#   pid

# Bounce
#   pid
#   occurred - datetime

class EmailReference(db.Model):
    address = db.StringProperty(required = True)
    spreadsheet = db.StringProperty(required = True)
    worksheet = db.StringProperty(required = True)
    created = db.DateTimeProperty(required = True, auto_now_add = True)
