# coding=utf-8
import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib'))

import webapp2
from google.appengine.ext.webapp.mail_handlers import BounceNotification,\
                                                    BounceNotificationHandler
from gdata.spreadsheets.client import ListQuery 
from gdata.spreadsheets.data import SpreadsheetsFeed
from settings import gdocs_settings
from clients import Clients
from models import EmailReference

import logging

class BounceHandler(BounceNotificationHandler):

    def __init__(self, request, response):
        super(BounceHandler, self).__init__(request, response)
        self.__clients__ = None

    @property
    def clients(self):
        if self.__clients__ is None:
            self.__clients__ = Clients()

        assert self.__clients__
        return self.__clients__


    def receive(self, bounce_notification):
        bouncing_email = bounce_notification.original['to']
        logging.debug('Received bounce from %s' % bouncing_email)

        # Retrieve the ID of the Spreadsheet containing this user's record from the Reference
        q = EmailReference.all()
        q.filter("address =", bouncing_email)
        q.order('-created')
        if q.count() == 0:
            log.error('Received bounce from an address we did not email: %s' % bouncing_email)
            return
        
        ref = q.get()
        query = ListQuery(sq="email=%s" % bouncing_email)
        self.clients.spreadsheet.GetListFeed(ref.spreadsheet, ref.worksheet, q=query)

        


app = webapp2.WSGIApplication([BounceHandler.mapping()], debug=True)
