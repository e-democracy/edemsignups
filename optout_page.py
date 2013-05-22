import webapp2
from google.appengine.ext.webapp import template 
from signupVerifier.processors.optout_processor import processOptOut,\
    getPersonByOptOutToken

import logging

optout_reason_template = 'templates/optout_request_reason.html' 
optout_confirm_template = 'templates/optout_confirm.html'

class OptOutPage(webapp2.RequestHandler):

    # Opt-Out Page
    #   1.) User Visits Opt-out Page (here)
    #   2.) Script checks for Out-Out Token (OptOutProcessor)
    #   3a.) If Exists
    #       1.) Ask user for Reason (here)
    #       2.) Enter Opt-Out (OptOutProcessor)
    #       3.) Remove Opt-Out Token (OptOutProcessor)
    #   3b.) Else
    #       1.) Display Error (here)

    def get(self):
        self.handleRequest()

    def post(self):
        self.handleRequest()

    def handleRequest(self):
        params = self.request.params

        # processOptOut and getPersonByOptOutToken will both throw LookupError
        # if the provided token can not be found.
        try:
            if 'token' in params:
                token = params['token']
                logging.info('Got token %s' % token)
                if 'reason' in params:
                    reason = params['reason']
                    optout = processOptOut(token, reason)
                    # Display confirmation page
                    retval = template.render(optout_confirm_template, {}) 
                else:
                    person = getPersonByOptOutToken(token)
                    # Display page requesting reason for optout
                    values = {'token': token}
                    retval = template.render(optout_reason_template, values)
            else:
                # Display a 404
                logging.info('No Token')
                self.abort(404)

            self.response.write(retval)

        except LookupError as e:
            #Display 404
            self.abort(404)


app = webapp2.WSGIApplication([
	webapp2.Route('/optout', handler=OptOutPage, name='optout')])
