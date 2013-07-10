# coding=utf-8
from urllib import urlencode
from google.appengine.ext.webapp import template
from google.appengine.api import mail

from ..settings import settings
from ..models import Batch, BatchChange, Person, PersonChange
from ..models.utils import clone_entity


verification_email_template = \
    'signupVerifier/processors/templates/verification_email.html'
verification_email_template_text = \
    'signupVerifier/processors/templates/verification_email.txt'


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

    batch_record = Batch(staff_email=batch['staff_email'],
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

    cur_batch = clone_entity(prev_batch, True, True, extra_args=batch)
    cur_batch.submitted_persons = 0
    cur_batch.invalid_persons = 0
    cur_batch.optedout_persons = 0
    cur_batch.bounced_persons = 0
    cur_batch.put()

    change_record = BatchChange(cur_batch=cur_batch, prev_batch=prev_batch)
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

    person_record = Person(email=person['email'],
                        first_name=person['first_name'],
                        last_name=person['last_name'],
                        full_name=person['full_name'],
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

    cur_person = clone_entity(prev_person, True, True, extra_args=person)
    cur_person.put()

    change_record = PersonChange(cur_person=cur_person,
                        prev_person=prev_person)
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


def sendVerificationEmails(batch, persons=None, optout_tokens=None,
        optout_base_url='http://localhost/optout', batch_log=None):
    """
    Generates an email based on the metadata of the provided batch, each
    person in the batch, and each person's opt-out token. Then sends the
    verification email to each person in the batch.

    Input:  batch - a Batch model
            persons - a list of Person models associated with this batch. If
                not provided, the Batch model will be used to find associated
                Person models. However, if Person models were very recently
                associated with the Batch, App Engine may not have yet updated
                the Person indexes, necessitating that a list of Person models
                be provided.
            optout_tokens - a dict mapping keys of Person models with instances
                of OptOutToken. Like persons, if not provided, the Batch or
                provided Person list will be used to find OptOutToken models,
                but may not be successful if OptOutToken models were recently
                saved.
            optout_base_url - a string containing the url of the optout page
                that should be used to build output links in emails.
            batch_log - option batch_log data structure. Must have
                persons_success and persons_fail list attributes. If no log is
                provided, then no logging will occur.
    Output: a modified batch_log if batch_log is provided. Otherwise,  True if
            verification emails are sent successfully, False otherwise.
    Side Effect: Emails are sent to all Person associated with the Batch
                    model.
    Throws: If batch_log is not provided, any encountered exceptions will
            bubble up.
    """
    batch = Batch.verifyOrGet(batch)

    try:
        if persons is None:
            # Can probably use run, except for wanting to possible generate
            # optout_tokens and then re-iterate
            persons = batch.persons.fetch(limit=None)

        if optout_tokens is None:
            optout_tokens = dict()
            for person in persons:
                optout_token[person.key()] = person.optout_tokens.filter(
                                                'batch =', batch).get()
    except Exception as e:
        if batch_log:
            batch_log['error'] = e
            return batch_log
        else:
            raise e

    for person in persons:
        try:
            optout_token = optout_tokens[person.key()]
            optout_uri = '?'.join([optout_base_url,
                            urlencode({'token': optout_token.key().id()})])
            template_values = {
                'first_name': person.first_name,
                'last_name': person.last_name,
                'full_name': person.full_name,
                'email': person.email,
                'optout_uri': optout_uri,
                'subject': settings['subject_initial_user']
            }

            email_html = template.render(verification_email_template,
                            template_values)
            email_text = template.render(verification_email_template_text,
                            template_values)
            message = mail.EmailMessage(sender=settings['app_email_address'],
                            subject=settings['subject_initial_user'])
            message.to = template_values['email']
            message.reply_to = settings['optout_email_address']
            message.html = email_html
            message.body = email_text
            message.send()

            if batch_log:
                batch_log['persons_success'].append(person)
        except Exception as e:
            if batch_log:
                batch_log['persons_fail'].append((person, e))
            else:
                raise e

    return batch_log if batch_log else True
