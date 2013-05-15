# coding=utf-8

from ..models import Bounce, Person
import datetime as dt

def createBounce(person, message, bounce_datetime=None):
    """
    Creates a record indicating the an email sent to the provided Person
    bounced. If provided, bounce_datetime will be recorded as the time the 
    bounce was received. Otherwise, the datetime of writing to the DB will be
    recorded as the bounce time.

    Input:  person - the Person instance or ID of the Person instnace who is 
                     bouncing
            message - a string representing the bounce message received.
            bounce_datetime - datetime that the bounce was received
    Output: a Bounce model created by the logging of the Bounce.
    Side Effect: an entry is saved to the database for the opt-out
    """
    person = Person.verifyOrGet(person)
    batch = person.source_batch
    if bounce_datetime:
        if not isinstance(bounce_datetime, dt.datetime):
            raise TypeError("bounce_datetime must be a datetime instance")
        bounce = Bounce(person=person,
                        batch=batch,
                        message=message,
                        occurred=bounce_datetime)
        
    else:
        bounce = Bounce(person=person, batch=batch, message=message)
    bounce.put()
    return bounce

def createBounceFromEmailAddress(address, message, bounce_datetime=None):
    """
    Creates a record indicating that the email sent to the provided address
    bounced. The provided address will be used to lookup the corresponding
    Person instance. If provided, bounce_datetime will be recorded as the time 
    the  bounce was received. Otherwise, the datetime of writing to the DB will 
    be recorded as the bounce time.

    Input:  address - the email address that caused a bounce. This will be used
                        to find an associated Person instance.
            message - a string representing the bounce message received.
            bounce_datetime - datetime that the bounce was received
    Output: a Bounce model created by the logging of the Bounce.
    Side Effect: an entry is saved to the database for the opt-out
    Throws: LookupError if a Person can not be found based on the provided
            address.
    """
    q = Person.all()
    q.filter('email =', address)
    q.filter('created >=', dt.datetime.now() - dt.timedelta(days=2))
    person = q.get()
    if not person:
        raise LookupError('No person with address %s found.' % address)
    return createBounce(person, message, bounce_datetime)

def getBounces(since=None):
    """
    Retrieves an interable of all Bounces that have occurred. If since is 
    specified, will only retrieve Bounces since the specified datetime.

    Input:  since - optional datetime indicating that only Bounces newer
            than since should be retrieved.
    Output: an interable of Bounce instances
    """
    q = Bounce.all()
    if since:
        q.filter('occurred >=', since)
    return q.run()
