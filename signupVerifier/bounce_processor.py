# coding=utf-8

class BounceProcessor(object):
       
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

