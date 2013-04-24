# coding=utf-8

from google.appengine.ext import db

class Batch(db.Model):
    """ Represents a batch of sign-ups gathered at a particular event and
    entered by a particular staff person."""
    staff_name = db.StringProperty(required = True)
    staff_email = db.Email(required = True)
    event_name = db.StringProperty()
    event_date = db.DateProperty()
    event_location = db.StringProperty()
    created = db.DateTimeProperty(required = True, auto_now_add = True)

class BatchChange(db.Model):
    """ Represents an evolution of a batch"""
    cur_batch = db.ReferenceProperty(Batch, required = True)
    prev_batch = db.ReferenceProperty(Batch, required = True)

class Person(db.Model):
    """ A person who signed up during an event, along with captured information
    about that person."""
    email = db.Email(required = True)
    first_name = db.StringProperty(required = True)
    last_name = db.StringProperty(required = True)
    full_name = db.StringProperty(required = True)
    neighborhood = db.StringProperty()
    street_address  = db.StringProperty()
    city = db.StringProperty()
    state = db.StringProperty()
    zip_code = db.StringProperty()
    phone = db.PhoneNumber()
    forums = db.StringListProperty()
    # Demographics
    stated_race = db.StringProperty()
    census_race = db.StringProperty()
    year_born = db.StringProperty()
    born_out_of_us = db.BooleanProperty()
    born_where = db.StringProperty()
    parents_born_out_of_us = db.BooleanProperty()
    parents_born_where = db.StringProperty()
    gender = db.StringProperty()
    num_in_house = db.IntegerProperty()
    yearly_income = db.IntegerProperty()
    source_batch = db.ReferenceProperty(Batch, required = True)

class PersonChange(db.Model):
    """ Represents an evolution of person"""
    cur_person = db.ReferenceProperty(Person, required = True)
    prev_person = db.ReferenceProperty(Person, required = True)

class BatchSpreadsheet(db.Model):
    """ Indicates connections between Google Spreadsheets and Batches """
    gsid = db.StringProperty(required = True)
    batch = db.ReferenceProperty(Batch, required = True)

class OptOutToken(db.Model):
    """ The tokens used to associate an opt-out request with a person and 
    batch"""
    token = db.StringProperty(required = True)
    person = db.ReferenceProperty(Person, required = True)
    batch = db.ReferenceProperty(Batch, required = True)

class OptOut(db.Model):
    """ Record of a person opting out"""
    person = db.ReferenceProperty(Person, required = True)
    batch = db.ReferenceProperty(Batch, required = True)
    reason = db.Text()
    occurred = db.DateTimeProperty()

class Bounce(db.Model):
    """ Record of a bounce"""
    person = db.ReferenceProperty(Person, required = True)
    message = db.Text()
    occurred = db.DateTimeProperty()
