# coding=utf-8

def createBounce(person, bounce_datetime):
    """
    Creates a record indicating the an email sent to the provided Person
    bounced. bounce_datetime will be recorded as the time the bounce was
    received.

    Input:  person - the Person model who is opting out
            bounce_datetime - datetime that the bounce was received
    Output: a Bounce model created by the logging of the Bounce.
    Side Effect: an entry is saved to the database for the opt-out
    """
    pass

def getBounces(since=None):
    """
    Retrieves a list of all Bounces that have occurred. If since is 
    specified, will only retrieve Bounces since the specified datetime.

    Input:  since - optional datetime indicating that only Bounces newer
            than since should be retrieved.
    Output: a list of Bounce instances
    """
    pass
