# coding=utf-8

from ..models import Batch, Person, OptOutToken, OptOut 
from google.appengine.ext.db import delete as modelDelete

def createOptOutToken(batch, person):
    """
    Generates an opt-out token for the provided person, saves that token
    to the database, and returns that token.
    
    Input: person - a Person model
    Output: the opt-out token string generated for the Person
    Side Effect: The opt-out token string is saved to the databse
    """
    batch = Batch.verifyOrGet(batch)
    person = Person.verifyOrGet(person)
    token = OptOutToken(batch = batch, person = person)
    token.put()
    return token

def getPersonByOptOutToken(token):
    """
    Searches the database for a record associated with the provided token,
    and returns the Person associated with the token if found.
    
    Input: token - a token string to search the Opt-Out Token table on.
    Output: a Person model if the provided token is found, or False if not
            found.
    """
    token = OptOutToken.verifyOrGet(token)
    return token.person

def removeOptOutToken(token):
    """
    Removes the associated OptOutToken from the database. If an OptOutToken
    instance is provided, then it will be removed from the database. If a
    string is provided, then an associated OptOutToken will be searched for
    and removed from the database.

    Input: token - either an OptOutToken, or a token string 
                         associated with an OptOutToken in the database.
    Output: True if removal is successful, False otherwise
    Side Effect: The database record associated with the provided
                 optouttoken will be deleted.
    """
    token = OptOutToken.verifyOrGet(token)
    token.delete()
    return True

def removeAllOptOutTokens():
    """
    Deletes all records from the OptOutToken table, effectively making all
    opt out tokens expire.

    Output: True if removal is successful, False otherwise
    Side Effect: All OptOutToken instances will be deleted from the
                 database.
    """
    q = OptOutToken.all(keys_only=True)
    modelDelete(q.run())
    return True

def createOptOut(person, batch, reason):
    """
    Creates a record in the database that the user opt-out of joining the
    forum indicated by the email that he/she received, and returns the
    created OptOut.

    Input:  person - the Person model who is opting out
            batch - the Batch associated with this optout
            reason - a string provided by the person as to why they are
                     opting out.
    Output: an OptOut model created by the logging of the opt-out.
    Side Effect: an entry is saved to the database for the opt-out
    """
    person = Person.verifyOrGet(person)
    batch = Batch.verifyOrGet(batch)
    if not isinstance(reason, basestring):
        raise TypeError('reason must be a string')
    optout = OptOut(person=person,
                    batch=batch,
                    reason=reason)
    optout.put()
    return optout 

def processOptOut(token, reason):
    """
    Performs the database actions associated with a user opting out of
    performing an action indicated by the email that he/she received. This
    includes logging the opt-out and removing the opt-out token from the
    databse.

    Input:  token - a token string representing the Opt-Out Token being
                    used.
            reason - a string provided by the person as to why they are
                     opting out.
    Output: a OptOut model created by the process if successful, False
            otherwise.
    Side Effect: an entry is made in the OptOut table representing the
                 person's wish to opt-out, and the associated OutOutToken 
                 is removed from the database.
    """

def getOptOuts(since=None):
    """
    Retrieves a list of all OptOuts that have occurred. If since is 
    specified, will only retrieve OptOuts since the specified datetime.

    Input:  since - optional datetime indicating that only OptOuts newer
            than since should be retrieved.
    Output: a list of OptOut instances
    """
    pass


