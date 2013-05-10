# coding=utf-8
import webapp2
from google.appengine.ext.webapp.mail_handlers import BounceNotification,\
                                                    BounceNotificationHandler
from signupVerifier.processors.bounce_processor import \
                                        createBounceFromEmailAddress

import logging

# Bounce Handler
#   1.) Add record to Bounce (BounceProcessor)

class BounceHandler(BounceNotificationHandler):

    def receive(self, bounce_message):
        """
            When a bounce is received, find the Person associated with it, and
            add an entry to the Bounce table.
        """
        bouncing_email = bounce_message.original['to']
        notification = bounce_message.notification['text']
        logging.debug('Received bounce from %s' % bouncing_email)

        # Save the bounce to the DB
        bounce = createBounceFromEmailAddress(bouncing_email, notification)

app = webapp2.WSGIApplication([BounceHandler.mapping()], debug=True)
