# coding=utf-8
import re
import webapp2
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler
from signupVerifier.processors.optout_processor import \
                                        createOptOutFromEmailAddress

import logging


class OptOutHandler(InboundMailHandler):

    def receive(self, mail_message):
        """
            When a message is received, find the Person associated with email
            address (created within the previous two days), and submit the
            optout.
        """
        message = ""
        for content_type, body in mail_message.bodies('text/plain'):
            if body.encoding:
                message += body.payload.decode(body.encoding)
            else:
                message += body.payload
            message += "\n\n"

        email_re = "<(.*)>"
        matched = re.search(email_re, mail_message.sender)
        if matched:
            address = matched.group(1)
        else:
            address = mail_message.sender
        logging.info('Received OptOut from %s' % address)

        # Save the optout to the DB
        bounce = createOptOutFromEmailAddress(address, message)

app = webapp2.WSGIApplication([OptOutHandler.mapping()], debug=True)
