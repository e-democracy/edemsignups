# coding=utf-8

from models import Bounce
import datetime as dt

def createBounce(person, message, bounce_datetime=None):
    """
    Creates a record indicating the an email sent to the provided Person
    bounced. bounce_datetime will be recorded as the time the bounce was
    received.

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
