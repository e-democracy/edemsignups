# coding=utf-8
from google.appengine.ext.webapp import template
from google.appengine.api import mail

from ..settings import settings
from ..models import Batch, BatchChange, Person, PersonChange
from ..models.utils import clone_entity


verification_email_template_path = 'verification_email.html'

def importBatch(batch):
    """
    Imports the provided batch into the database, and returns the created
    Batch model.
    
    Input: batch - a dict representing the batch to save to the database.
                   Allowable attributes of the dict are: 
                        'staff_name': string,
                        'staff_email': string, 
                        'event_name': string, 
                        'event_date': date, 
                        'event_location': string
    Output: a Batch model created by the import.
    Side Effect: an entry is saved to the database for the batch.
    """
    if not isinstance(batch, dict):
        raise TypeError('Expected dict')

    batch_record = Batch(staff_email = batch['staff_email'],
                            staff_name=batch['staff_name'])
    for key, value in batch.iteritems():
        setattr(batch_record, key, value)
    batch_record.put()

    return batch_record

def addBatchChange(batch, prev_batch):
    """
    Imports a change to a previously existing Batch, and returns the
    created Batch model. Values associated with the previous Batch will be
    used in the created Batch, unless a value is specified in the batch
    dict.

    Input:  batch - a dict representing the batch to save to the database.
            prev_batch - either the ID or Batch instance of the previous 
                        instance of the provided batch
    Output: a Batch model created by the addition of the new batch.
    Side Effect: an entry is saved to the database for the batch, and an
                 association between the new batch and its previous 
                 instance is saved.
    Throws: TypeError if batch is not a dict
    """
    if not isinstance(batch, dict):
        raise TypeError('Expected batch to be dict')

    prev_batch = Batch.verifyOrGet(prev_batch)

    cur_batch = clone_entity(prev_batch, True, True, extra_args = batch)
    cur_batch.put()

    change_record = BatchChange(cur_batch = cur_batch,
                                prev_batch = prev_batch)
    change_record.put()

    return cur_batch
    

def importPerson(person, batch):
    """
    Imports the provided single person, associated with the indicated
    batch, into the databse, and returns the created Person model.

    Input:  person - a dict representing the person to save to the
                     database. See Person in models for list of attributes.
            batch - the ID or instance of the Batch model that this person is 
                    associated with.
    Output: a Person model craeted by the import.
    Side Effect: an entry is saved to the database for the person.
    Throws: TypeError if person is not a dict
    """
    if not isinstance(person, dict):
        raise TypeError('Expected person to be dict')

    batch = Batch.verifyOrGet(batch)

    person_record = Person(email = person['email'],
                           first_name = person['first_name'],
                           last_name = person['last_name'],
                           full_name = person['full_name'],
                           source_batch = batch)
    for key, value in person.iteritems():
        setattr(person_record, key, value)
    person_record.put()

    return person_record

def addPersonChange(person, prev_person):
    """
    Imports a change to a previously existing Person, and returns the
    created Person model. Values of the previous instance of the Person 
    will be used in the new instance of the Person, unless a value is 
    specified in the person dict.

    Input:  person - a dict representing the person to save to the database.
            prev_person - the ID or Person instance of the previous instance of 
                          the provided person.
    Output: a Person model created by the addition of the new person.
    Side Effect: an entry is saved to the database for the person, and an
                 association between the new person and its previous 
                 instance is saved.
    """
    if not isinstance(person, dict):
        raise TypeError('Expected person to be dict')
  
    prev_person = Person.verifyOrGet(prev_person)

    cur_person = clone_entity(prev_person, True, True, extra_args = person)
    cur_person.put()

    change_record = PersonChange(cur_person = cur_person,
                                 prev_person = prev_person)
    change_record.put()

    return cur_person

def importPersons(persons, batch):
    """
    Imports the provided persons, associated with the indicated batch, into
    the database, and returns a list of Person models.
    
    Input:  persons - a List of dicts representing persons to save to the
                        database.
            batch - the ID or instance of the Batch model that these persons 
                    are to be associated with.
    Output: a List of Person models created by the import.
    Side Effect: Entries are saved to the database for each person
                    contained in the persons list.
    """
    batch = Batch.verifyOrGet(batch)

    person_records = [importPerson(person, batch) for person in persons]
    return person_records   

def sendVerificationEmails(batch):
    """ 
    Generates an email based on the metadata of the provided batch, each 
    person in the batch, and each person's opt-out token. Then sends the 
    verification email to each person in the batch.

    Input: batch - a Batch model
    Output: True if verification emails are sent successfully, false
            otherwise.
    Side Effect: Emails are sent to all Person associated with the Batch
                    model.
    """
    batch = Batch.verifyOrGet(batch)

    pq = Person.all().filter('source_batch =', batch)

    print "Persons in this batch: %d" % batch.persons.count()

    for person in pq.run():
        print "Sending an email to %s" % person.full_name
        optout_token = person.optout_tokens.filter('batch =', batch).get() 
        template_values = {
            'first_name': person.first_name,
            'last_name': person.last_name,
            'full_name': person.full_name,
            'email': person.email,
            'optout_token': optout_token.key()
        }

        email_body = template.render(verification_email_template_path)
        print email_body

        mail.send_mail(settings['email_as'],
                        template_values['email'],
                        settings['verification_subject'],
                        email_body)

    return True
