# coding=utf-8

from google.appengine.ext import db

def asDict(cls, instance):
    """ Returns the instance of a Model as a dict"""
    model_dict = {}
    for prop in cls.properties():
        model_dict[prop] = getattr(instance, prop)

    return model_dict

def verifyOrGet(cls, challenge):
    """
        Verifies that the provided challenge refers in some way to an actual
        instance of the provided class, and returns the instance it refers to. 
        If challenge is an instance of the class, than it will simply be 
        returned. If challenge is a string, then the function will assume it is
        a key and attempt to retrieve the class instance associated with it.

        Input:  cls - The class that is being verified or fetched for.
                challege - Either an instance of cls, or a string that is the 
                            key of an instance of cls.
        Output: An instance of cls
        Throws: TypeError if challenge is not a string or cls instnace
                LookupError if challenge can not be found
    """
    if isinstance(challenge, cls):
        return challenge

    if isinstance(challenge, basestring):
        key = challenge
        challenge = cls.get(key)
        if not (challenge and isinstance(challenge, cls)):
            raise LookupError('provided key could not be found: %s' %
                                key)
        return challenge
    else:
        raise TypeError('challenge must be either string or %s' % str(cls))


class Batch(db.Model):
    """ Represents a batch of sign-ups gathered at a particular event and
    entered by a particular staff person."""
    staff_name = db.StringProperty(required = True)
    staff_email = db.EmailProperty(required = True)
    event_name = db.StringProperty()
    event_date = db.DateProperty()
    event_location = db.StringProperty()
    created = db.DateTimeProperty(required = True, auto_now_add = True)
    submitted_persons = db.IntegerProperty(default=0)
    invalid_persons = db.IntegerProperty(default=0)
    optedout_persons = db.IntegerProperty(default=0)
    bounced_persons = db.IntegerProperty(default=0)
    

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
        return verifyOrGet(cls, batch)

class BatchChange(db.Model):
    """ Represents an evolution of a batch"""
    cur_batch = db.ReferenceProperty(Batch, required = True,
                collection_name="previous_changes")
    prev_batch = db.ReferenceProperty(Batch, required = True,
                collection_name="next_changes")

class Person(db.Model):
    """ A person who signed up during an event, along with captured information
    about that person."""
    created = db.DateTimeProperty(required = True, auto_now_add = True)
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
        return asDict(Person, self)

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
        return verifyOrGet(cls, person)

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
        return verifyOrGet(cls, token)

class OptOut(db.Model):
    """ Record of a person opting out"""
    person = db.ReferenceProperty(Person, required = True,
                                    collection_name='optouts')
    batch = db.ReferenceProperty(Batch, required = True, 
                                    collection_name='optouts')
    reason = db.TextProperty()
    occurred = db.DateTimeProperty(required = True, auto_now_add = True)

class Bounce(db.Model):
    """ Record of a bounce"""
    person = db.ReferenceProperty(Person, required = True,
                                collection_name='bounces')
    batch = db.ReferenceProperty(Batch, required = True, 
                                 collection_name='bounces')
    message = db.TextProperty()
    occurred = db.DateTimeProperty(required = True, auto_now_add = True)
