# coding=utf-8

from google.appengine.ext.webapp import template
from google.appengine.api import mail

from clients import Clients
from settings import gdocs_settings
from models import EmailReference



class SignupVerifier(object):

    def __init__():
        self.__clients__ = None
        self.email_path = os.path.join(os.path.dirname(__file__), 
                            gdocs_settings['template_fn'])

    @property
    def clients(self):
        if self.__clients__ is None:
            self.__clients__ = Clients()

        assert self.__clients__
        return self.__clients__

    

    def sendVerificationEmails(self, listsfeed, spreadsheet_id, worksheet_id):
        """
           Given a ListsFeed and the associated spreadsheet_id and 
           worksheet_id, sends an email to the email address associated with 
           each row in the feed to verify that the email address exists, and to
           give the address the opportunity to opt-out. 
        """

        if not isinstance(listsfeed, ListsFeed):
            raise TypeError('Must provide a GData ListsFeed.')

        rows = listsfeed.entry
        for row in rows:
            template_values = {
                'firstname': row.get_value('firstname'), 
                'lastname': row.get_value('lastname'), 
                'fullname': row.get_value('fullname'), 
                'email': row.get_value('email')
            }

            mail.send_mail(gdocs_settings['email_as'],
                            template_values['email'],
                            gdocs_settings['verification_subject'],
                            template.render(self.email_path))

            # Save a reference to the email we just sent for later
            ref = EmailReference(address = template_values['email'],
                                spreadsheet = spreadsheet_id,
                                worksheet = worksheet_id)
            ref.put()

    def verifySignups(self):
        """
            Querys the Signups Folder in Google Drive for new spreadsheets
            containing records of people signed up in person and verifies those
            signups by checking that the record's email address exists.
        """
        signups_folder = self.clients.docs.GetResourceById(
                            gdoc_settings['signups_folder_id'])

        for spreadsheet in self.spreadsheets(signups_folder):
            sid = spreadsheet_id(spreadsheet)
            raw_sheet_query = WorksheetQuery(
                                title=gdoc_settings['raw_sheet_title'])
            raw_sheet = self.clients.spreadsheets.GetWorksheets(sid,
                            q=raw_sheet_query)
            raw_sheet_id = worksheet_id(raw_sheet)
            rows = self.clients.spreadsheets.GetListFeed(sid, wid)
            self.sendVerificationEmails(rows)

