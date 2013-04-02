import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib'))

from google.app.engine.ext.webapp.mail_handlers import BounceNotification,\
                                                    BounceNotificationHandler
from gdata.docs.client import DocsClient, DocsQuery
from gdata.spreadsheets.client import SpreadsheetsClient
from gdata.spreadsheets.data import SpreadsheetsFeed
from settings import gdocs_settings

import logging

class BounceHandler(BounceNotificationHandler):

    def receive(self, bounce_notification):
        logging.info('Received bounce form %s' % bounce_notification.notification_from)
        


app = webapp2.WSGIApplication([BounceHandler.mapping()],
                              debug=True)
