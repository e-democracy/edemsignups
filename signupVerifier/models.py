# coding=utf-8

from google.appengine.ext import db

# Batch 
#   bid
#   staff_name
#   staff_email
#   event_name
#   event_date
#   event_location
#   created - datetime

# Batch Change
#   bid
#   prev_bid

# Person
#   pid
#   Various Fields
#   source_gsid

# Person Change
#   pid
#   prev_pid

# Batch Spreadsheet
#   gsid
#   bid

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
