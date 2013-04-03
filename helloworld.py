# coding=utf-8
import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), 
                'lib'))

import webapp2
from google.appengine.ext.webapp import template
from google.appengine.api import mail
from gdata.docs.client import DocsQuery
from gdata.spreadsheets.data import SpreadsheetsFeed
from clients import Clients
from settings import gdocs_settings
from models import EmailReference

import logging

class MainPage(webapp2.RequestHandler):

    def __init__(self, request, response):
        # webapp2 uses initialize instead of __init__, cause it's special
        self.initialize(request, response)
        self.__clients__ = None
        self.email_path = os.path.join(os.path.dirname(__file__), 'email.html')
    
    @property
    def clients(self):
        if self.__clients__ is None:
            self.__clients__ = Clients()

        assert self.__clients__
        return self.__clients__

    def spreadsheets(self, folder):
        '''Generates a list of Google Spreadsheets based on the Resource
           instance provided, which is assumed to be a folder. If the provided
           folder contains other folders, they will be recursively searched for
           spreadsheets and other folders, breadth first.
           
           Returned spreadsheets will be Resource instances.'''
        folders = []
        contents = self.clients.docs.GetResources(uri=folder.content.src)
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

        folder = self.clients.docs.GetResources(q=query).entry[0]

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
            for worksheet in self.clients.spreadsheets.GetWorksheets(
                                                        spreadsheet_id).entry:
                retval += '\t%s\n' % worksheet.title.text
                worksheet_id = worksheet.id.text.rsplit('/',1)[1]
                if worksheet.title.text == 'Raw':
                    rows = self.clients.spreadsheets.GetListFeed(
                                        spreadsheet_id, worksheet_id).entry
                    for row in rows:
                        template_values = {
                            'firstname': row.get_value('firstname'), 
                            'lastname': row.get_value('lastname'), 
                            'fullname': row.get_value('fullname'), 
                            'email': row.get_value('email') 
                        }
                        retval += '\t\tFirst Name: %(firstname)s, \
                                    Last Name: %(lastname)s, \
                                    Full Name %(fullname)s, \
                                    Email: %(email)s\n' % template_values
                        retval += '\t\t%s\n\n\n\n' % template.render(
                                            self.email_path, template_values)
                        mail.send_mail(gdocs_settings['email_as'], 
                                        template_values['email'], 
                                        'Welcome to E-Democracy', 
                                        template.render(self.email_path, 
                                                        template_values))

                        # Save a reference to the email we just sent for later
                        ref = EmailReference(address = template_values['email'],
                                            spreadsheet = spreadsheet_id,
                                            worksheet = worksheet_id)
                        ref.put()

                        logging.debug('Emailed: %s' % template_values['email'])


        self.response.headers['Content-Type'] = 'text/plain'
        self.response.write(retval)

from gdata.spreadsheets.client import WorksheetQuery, ListQuery
from gdata.spreadsheets.data import ListEntry
from datetime import datetime
class TestPage(webapp2.RequestHandler):

    def __init__(self, request, response):
        # webapp2 uses initialize instead of __init__, cause it's special
        self.initialize(request, response)
        self.__clients__ = None
    
    @property
    def clients(self):
        if self.__clients__ is None:
            self.__clients__ = Clients()

        assert self.__clients__
        return self.__clients__

    def get(self):
        retval = ''
        spreadsheet_id = '0AvVUbsCmsj1jdGpPVFhSR0lfZzhhQTJ2VWJ1dnlPMWc' 

        bounced_sheets = self.clients.spreadsheets.GetWorksheets(spreadsheet_id,
                                    q=WorksheetQuery(title='Bounced')).entry
        if len(bounced_sheets) == 0:
            # Make a Bounced sheet
            result = self.clients.spreadsheets.AddWorksheet(spreadsheet_id, 
                                                            'Bounced', 50, 50)
            # 1.) Get the top row of the Raw sheet
            # 2.) Insert it into the Worksheet created above

        if len(bounced_sheets) > 1:
            # This message should include the name of the spreadsheet. It 
            # should also be emailed.
            logging.warning('Multiple Bounce sheets found. \
                            Using the first one.')
        bounced_sheet = bounced_sheets[0]
        bounced_sheet_id = bounced_sheet.id.text.rsplit('/',1)[1]
        logging.debug('%s' % bounced_sheet_id)
        retval += '%s' % bounced_sheet_id 

        query = ListQuery(sq='email = "%s"' % 
            'thisAddressDoesNotExistBecauseNoBodyWouldWantSuchALongAndRamblingAddress@gmail.com')
        rows = self.clients.spreadsheets.GetListFeed(spreadsheet_id, 
                                                        'od6', q=query).entry
        retval += 'Results:\n'
        for row in rows:
            template_values = {
                'firstname': row.get_value('firstname'),
                'lastname': row.get_value('lastname'),
                'fullname': row.get_value('fullname'),
                'email': row.get_value('email')
            }

            retval += '\t\tFirst Name: %(firstname)s, \
                        Last Name: %(lastname)s, \
                        Full Name %(fullname)s, \
                        Email: %(email)s\n' % template_values

            # Indicate the bounce was received now
            bounce_time_str = datetime.now().strftime('%m/%d/%Y %H:%M:%S %Z')
            logging.debug('\t\tTime: %s\n' % bounce_time_str)
            retval += '\t\tTime: %s\n' % bounce_time_str
            row.set_value('bounced', bounce_time_str)

            # Move the record to the Bounced Sheet
            # Using the same instance of a ListEntry works just fine here. 
            # In the first, a new row is being created based on the data in the
            # ListEntry instance. In the second, Delete will refer to the URI
            # of the ListEntry instance, which refers to the original row.
            self.clients.spreadsheets.AddListEntry(row, spreadsheet_id, 
                                                        bounced_sheet_id)
            self.clients.spreadsheets.Delete(row)

        
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.write(retval)



app = webapp2.WSGIApplication([('/', MainPage),
                                ('/test', TestPage)],
                              debug=True)
