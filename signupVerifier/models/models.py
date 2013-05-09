# coding=utf-8

from google.appengine.ext import db

def asDict(cls, instance):
    """ Returns the instance of a Model as a dict"""
    model_dict = {}
    for prop in cls.properties():
        model_dict[prop] = getattr(instance, prop)

    return model_dict

class Batch(db.Model):
    """ Represents a batch of sign-ups gathered at a particular event and
    entered by a particular staff person."""
    staff_name = db.StringProperty(required = True)
    staff_email = db.EmailProperty(required = True)
    event_name = db.StringProperty()
    event_date = db.DateProperty()
    event_location = db.StringProperty()
    created = db.DateTimeProperty(required = True, auto_now_add = True)

    def asDict(self):
        return asDict(Batch, self)

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
    notes = db.StringProperty()
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
        return asDict(Batch, self)

    @classmethod
    def verifyOrGet(cls, person):
        """
            Verifies that the provided person refers in some way to an actual
            Person instance, and returns the Person instance it refers to. If
            person is a Person instance, than it will simply be returned. If
            person is a string, then the method will assume it is a key and
            attempt to retrieve the Person instance associated with it.

            Input: person - Either a Person instance, or a string that is the 
                            key of a Person instance.
            Output: A Person instance
            Throws: TypeError if person is not a string or Person
                    LookupError if person can not be found
        """
        if isinstance(person, Person):
            return person

        if isinstance(person, basestring):
            person_key = person
            person = Person.get(person_key)
            if not (person and isinstance(person, Person)):
                raise LookupError('provided person could not be found: %s' % 
                                    person_key) 
            return person
        else:
            raise TypeError('person must be either string or Person')

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
    person = db.ReferenceProperty(Person, required = True,
                                    collection_name='optout_tokens')
    batch = db.ReferenceProperty(Batch, required = True,
                                    collection_name='optout_tokens')
    @classmethod
    def verifyOrGet(cls, token):
        """
            Verifies that the provided batch refers in some way to an actual
            OptOutToken instance, and returns the OptOutToken instance it 
            refers to. If token is an OptOutToken instance, than it will simply 
            be returned. If token is a string, then the method will assume it 
            is a key and attempt to retrieve the OptOutToken instance 
            associated with it.

            Input: token - Either an OptOutToken instance, or a string that is 
                            the key of an OptOutToken instance.
            Output: An OptOutToken instance
            Throws: TypeError if token is not a string or OptOutToken
                    LookupError if token can not be found
        """
        if isinstance(token, cls):
            return token

        if isinstance(token, basestring):
            key = token
            token = cls.get(key)
            if not (token and isinstance(token, cls)):
                raise LookupError('provided token could not be found: %s' %
                                    key)
            return token
        else:
            raise TypeError('token must be either string or Batch')
    


class OptOut(db.Model):
    """ Record of a person opting out"""
    person = db.ReferenceProperty(Person, required = True,
                                    collection_name='optouts')
    batch = db.ReferenceProperty(Batch, required = True, 
                                    collection_name='optouts')
    reason = db.Text()
    occurred = db.DateTimeProperty()

class Bounce(db.Model):
    """ Record of a bounce"""
    person = db.ReferenceProperty(Person, required = True)
    batch = db.ReferenceProperty(Batch, required = True, 
                                 collection_name='bounces')
    message = db.Text()
    occurred = db.DateTimeProperty()
