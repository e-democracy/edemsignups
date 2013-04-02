# coding=utf-8
import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib'))

from google.app.engine.ext.webapp.mail_handlers import BounceNotification,\
                                                    BounceNotificationHandler
from gdata.spreadsheets.client import ListQuery 
from gdata.spreadsheets.data import SpreadsheetsFeed
from settings import gdocs_settings
from clients import Clients

import logging

class BounceHandler(BounceNotificationHandler):

    def __init__():
        super(BounceHandler, self).__init__()
        self.__clients__ = None

    @property
    def clients(self):
        if self.__clients__ is None:
            self.__clients__ = Clients()

        assert self.__clients__
        return self.__clients__


    def receive(self, bounce_notification):
        bouncing_email = bounce_notification.notification_from
        logging.info('Received bounce form %s' % bouncing_email)
        logging.info('\tBouncing Message: %s' bounce_notification.original_raw_message())
        query = ListQuery(sq="email=%s" % bouncing_email)

        


app = webapp2.WSGIApplication([BounceHandler.mapping()],
                              debug=True)
