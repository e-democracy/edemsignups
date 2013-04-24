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

