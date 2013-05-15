# coding=utf-8
import webapp2
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler
from signupVerifier.processors.optout_processor import \
                                        createOptoutFromEmailAddress

import logging


class OptOutHandler(InboundMailHandler):

    def receive(self, mail_message):
        """
            When a message is received, find the Person associated with email
            address (created within the previous two days), and submit the
            optout.
        """
        message = mail_message.bodies('text/plain')
        address = mail_message.sender
        logging.info('Received OptOut from %s' % address)

        # Save the optout to the DB
        bounce = createOptoutFromEmailAddress(address, message)

app = webapp2.WSGIApplication([OptOutHandler.mapping()], debug=True)
