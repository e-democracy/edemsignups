import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib'))

import webapp2
from google.appengine.ext.webapp import template
from google.appengine.api import mail
from gdata.docs.client import DocsClient, DocsQuery
from gdata.spreadsheets.client import SpreadsheetsClient
from gdata.spreadsheets.data import SpreadsheetsFeed
from settings import gdocs_settings

class MainPage(webapp2.RequestHandler):

    def __init__(self, request, response):
        # webapp2 uses initialize instead of __init__, cause it's special
        self.initialize(request, response)
        self.__docsClient__ = None
        self.__spreadsheetsClient__ = None
        self.email_path = os.path.join(os.path.dirname(__file__), 'email.html')
    
    # For now, being lazy and using username/password.
    # Eventually, we should use Oauth.

    @property
    def docsClient(self):
        if self.__docsClient__ is None:
            self.__docsClient__ = DocsClient()
            self.__docsClient__.ClientLogin(gdocs_settings['username'], 
                                gdocs_settings['password'], gdocs_settings['app_name'])

        assert self.__docsClient__
        return self.__docsClient__

    @property
    def spreadsheetsClient(self):
        if self.__spreadsheetsClient__ is None:
            self.__spreadsheetsClient__ = SpreadsheetsClient()
            self.__spreadsheetsClient__.ClientLogin(gdocs_settings['username'], 
                                gdocs_settings['password'], gdocs_settings['app_name'])
        assert self.__spreadsheetsClient__
        return self.__spreadsheetsClient__

    def spreadsheets(self, folder):
        '''Generates a list of Google Spreadsheets based on the Resource
           instance provided, which is assumed to be a folder. If the provided
           folder contains other folders, they will be recursively searched for
           spreadsheets and other folders, breadth first.
           
           Returned spreadsheets will be Resource instances.'''
        folders = []
        contents = self.docsClient.GetResources(uri=folder.content.src)
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

        folder = self.docsClient.GetResources(q=query).entry[0]

        retval = 'Your Spreadsheets:\n'
        for spreadsheet in self.spreadsheets(folder):
            # Another pain in the butt: as far as I can tell, there is no way 
            # to convert a Resource into another object. The Spreadsheet class
            # includes a GetSpreadsheetKey method that does the following. But
            # since I can't just convert the Resource into a Spreadsheet, I
            # have to get all goofy and reimplement GetSpreadsheetKey
            spreadsheet_id = spreadsheet.GetId().split('/')[-1]
            spreadsheet_id = spreadsheet_id.split('spreadsheet%3A')[-1]
            retval += '%s\n' % spreadsheet.title.text
            for worksheet in self.spreadsheetsClient.GetWorksheets(spreadsheet_id).entry:
                retval += '\t%s\n' % worksheet.title.text
                if worksheet.title.text == 'Raw':
                    rows = self.spreadsheetsClient.GetListFeed(spreadsheet_id, worksheet.id.text.rsplit('/',1)[1]).entry
                    for row in rows:
                        template_values = {
                            'firstname': row.get_value('firstname'), 
                            'lastname': row.get_value('lastname'), 
                            'fullname': row.get_value('fullname'), 
                            'email': row.get_value('email') 
                        }
                        retval += '\t\tFirst Name: %(firstname)s, Last Name: %(lastname)s, Full Name %(fullname)s, Email: %(email)s\n' % template_values
                        retval += '\t\t%s\n\n\n\n' % template.render(self.email_path, template_values)
                        mail.send_mail(gdocs_settings['email_as'], template_values['email'], 'Welcome to E-Democracy', template.render(self.email_path, template_values))

        self.response.headers['Content-Type'] = 'text/plain'
        self.response.write(retval)


app = webapp2.WSGIApplication([('/', MainPage)],
                              debug=True)
