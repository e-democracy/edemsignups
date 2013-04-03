# coding=utf-8
import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), 
                'lib'))

from gdata.docs.client import DocsClient, DocsQuery
from gdata.spreadsheets.client import SpreadsheetsClient
from gdata.spreadsheets.data import SpreadsheetsFeed
from settings import gdocs_settings


class Clients(object):
    def __init__(self):
        self.__docsClient__ = None
        self.__spreadsheetsClient__ = None

    # For now, being lazy and using username/password.
    # Eventually, we should use Oauth.

    @property
    def docs(self):
        if self.__docsClient__ is None:
            self.__docsClient__ = DocsClient()
            self.__docsClient__.ClientLogin(gdocs_settings['username'],
                                gdocs_settings['password'], 
                                gdocs_settings['app_name'])

        assert self.__docsClient__
        return self.__docsClient__

    @property
    def spreadsheets(self):
        if self.__spreadsheetsClient__ is None:
            self.__spreadsheetsClient__ = SpreadsheetsClient()
            self.__spreadsheetsClient__.ClientLogin(gdocs_settings['username'],
                                gdocs_settings['password'], 
                                gdocs_settings['app_name'])
        assert self.__spreadsheetsClient__
        return self.__spreadsheetsClient__

