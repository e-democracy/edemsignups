import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib'))

import webapp2
from gdata.docs.client import DocsClient, DocsQuery
from gdata.spreadsheets.client import SpreadsheetsClient
from gdata.spreadsheets.data import SpreadsheetsFeed
import gdata.spreadsheet
from settings import gdocs_settings

class MainPage(webapp2.RequestHandler):

    def __init__(self, request, response):
        # webapp2 uses initialize instead of __init__, cause it's special
        self.initialize(request, response)
        self.__token__ = None
        self.__docsClient__ = None
        self.__spreadsheetsClient__ = None
    
    @property
    def docsClient(self):
        if self.__docsClient__ is None:
            self.__docsClient__ = DocsClient()
        assert self.__docsClient__
        return self.__docsClient__

    @property
    def spreadsheetsClient(self):
        if self.__spreadsheetsClient__ is None:
            self.__spreadsheetsClient__ = SpreadsheetsClient()
        assert self.__spreadsheetsClient__
        return self.__spreadsheetsClient__

    @property
    def token(self):
        # For now, being lazy and using username/password. The token returned by 
        # one type of client can be used by other types. In fact, it has to, as
        # future calls to ClientLogin will result in unusable tokens.
        #
        # Eventually, we should use Oauth.
        if self.__token__ is None:
            self.__token__ = self.docsClient.ClientLogin(gdocs_settings['username'], 
                    gdocs_settings['password'], gdocs_settings['app_name'])
        assert self.__token__
        return self.__token__

    def spreadsheets(self, folder):
        '''Generates a list of Google Spreadsheets based on the Resource
           instance provided, which is assumed to be a folder. If the provided
           folder contains other folders, they will be recursively searched for
           spreadsheets and other folders, breadth first.
           
           Returned spreadsheets will be Resource instances.'''
        folders = []
        contents = self.docsClient.GetResources(uri=folder.content.src,
                    auth_token=self.token)
        for entry in contents.entry:
            if entry.GetResourceType() == 'folder':
                folders.append(entry)
            elif entry.GetResourceType() == 'spreadsheet':
                yield entry

        for folder in folders:
            for spreadsheet in self.spreadsheets(folder):
                yield spreadsheet


    def get(self):
        # This is a bit confusing, because the Spreadsheets Client does not 
        # directly support searching for a folder. So, a Docs Client is first
        # used to search for the folder we want to retreive spreadsheets from.
        query = DocsQuery(
            title='Sign Up Spreadsheets (Data)',
            title_exact='true',
            show_collections='true')

        folder = self.docsClient.GetResources(q=query, auth_token=self.token).entry[0]

        # Now that we have the folder, its time to get the spreadsheets...
        # Unfortunately, we can't just use the get_spreadsheets method, because 
        # we need to provide the URI of the specific folder we want to get 
        # spreadsheets from, and we need to recurse on other folders. A 
        # get_spreadsheets_from_folder function would be a nice addition.
        
        retval = 'Your Spreadsheets:\n'
        for spreadsheet in self.spreadsheets(folder):
            retval += '%s\n' % (spreadsheet.title.text)

        self.response.headers['Content-Type'] = 'text/plain'
        self.response.write(retval)


app = webapp2.WSGIApplication([('/', MainPage)],
                              debug=True)
