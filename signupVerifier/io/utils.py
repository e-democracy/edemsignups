# coding=utf-8
import socket.error
from httplib import BadStatusLine, HTTPException
from google.appengine.api.urlfetch_errors import DeadlineExceededError
import logging


def tryXTimes(func, times=5):
    """
        Helper function that will retry a function in the event of a
        BadStatusLine. Attempts the provided function as many times as
        indicated, or until there is no BadStatusLine.
    """
    for i in range(1, times):
        try:
            return func()
        except BadStatusLine as e:
            logging.error('Caught BadStatusLine on try %s' % i)
            logging.exception(e)
        except DeadlineExceededError as e:
            logging.error('Caught DeadlineExceededError on try %s' % i)
            logging.exception(e)
        except HTTPException as e:
            logging.error('Caught HTTPException on try %s' % i)
            logging.exception(e)
        except socket.error as e:
            logging.error('Caught socket.error on try %s' % i)
            logging.exception(e)

    logging.info('Final Try')
    return func()
