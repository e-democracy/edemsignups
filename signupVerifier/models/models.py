# coding=utf-8

from google.appengine.ext import db

class Batch(db.Model):
    """ Represents a batch of sign-ups gathered at a particular event and
    entered by a particular staff person."""
    staff_name = db.StringProperty(required = True)
    staff_email = db.EmailProperty(required = True)
    event_name = db.StringProperty()
    event_date = db.DateProperty()
    event_location = db.StringProperty()
    created = db.DateTimeProperty(required = True, auto_now_add = True)

    @classmethod
    def verifyOrGet(cls, batch):
        """
            Verifies that the provided batch refers in some way to an actual
            Batch instance, and returns the Batch instance it refers to. If
            batch is a Batch instance, than it will simply be returned. If
            batch is a string, then the method will assume it is a key and
            attempt to retrieve the Batch instance associated with it.

            Input: batch - Either a Batch instance, or a string that is the key
                            of a Batch instance.
            Output: A Batch instance
            Throws: TypeError if batch is not a string or Batch
                    LookupError if batch can not be found
        """
        if isinstance(batch, Batch):
            return batch

        if isinstance(batch, basestring):
            batch_key = batch
            batch = Batch.get(batch_key)
            if not (batch and isinstance(batch, Batch)):
                raise LookupError('provided batch could not be found: %s' %
                                    batch_key)
            return batch
        else:
            raise TypeError('batch must be either string or Batch')
    

class BatchChange(db.Model):
    """ Represents an evolution of a batch"""
    cur_batch = db.ReferenceProperty(Batch, required = True,
                collection_name="previous_changes")
    prev_batch = db.ReferenceProperty(Batch, required = True,
                collection_name="next_changes")

class Person(db.Model):
    """ A person who signed up during an event, along with captured information
    about that person."""
    email = db.EmailProperty(required = True)
    first_name = db.StringProperty(required = True)
    last_name = db.StringProperty(required = True)
    full_name = db.StringProperty(required = True)
    neighborhood = db.StringProperty()
    street_address  = db.StringProperty()
    city = db.StringProperty()
    state = db.StringProperty()
    zip_code = db.StringProperty()
    phone = db.PhoneNumberProperty()
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
    yrly_income = db.IntegerProperty()
    source_batch = db.ReferenceProperty(Batch, collection_name = 'persons', 
                                        required = True)

    def asDict(self):
        """ Returns the instance of Person as a dict"""
        person_dict = {}
        for prop in db.Model.properties(Person):
            person_dict[prop] = getattr(self, prop)

        return person_dict

class PersonChange(db.Model):
    """ Represents an evolution of person"""
    cur_person = db.ReferenceProperty(Person, required = True,
                    collection_name="previous_changes")
    prev_person = db.ReferenceProperty(Person, required = True,
                    collection_name="next_changes")

class BatchSpreadsheet(db.Model):
    """ Indicates connections between Google Spreadsheets and Batches """
    gsid = db.StringProperty(required = True)
    batch = db.ReferenceProperty(Batch, required = True,
                                collection_name="spreadsheets")

class OptOutToken(db.Model):
    """ The tokens used to associate an opt-out request with a person and 
    batch"""
    token = db.StringProperty(required = True)
    person = db.ReferenceProperty(Person, required = True)
    batch = db.ReferenceProperty(Batch, required = True)

class OptOut(db.Model):
    """ Record of a person opting out"""
    person = db.ReferenceProperty(Person, required = True)
    batch = db.ReferenceProperty(Batch, required = True, 
                                    collection_name='OptOuts')
    reason = db.Text()
    occurred = db.DateTimeProperty()

class Bounce(db.Model):
    """ Record of a bounce"""
    person = db.ReferenceProperty(Person, required = True)
    batch = db.ReferenceProperty(Batch, required = True, 
                                 collection_name='Bounces')
    message = db.Text()
    occurred = db.DateTimeProperty()
