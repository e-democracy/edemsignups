# coding=utf-8

import webapp2
from google.appengine.ext.webapp import template
from google.appengine.api import mail
from signupVerifier.gclient import GClient

import logging


class SpreadsheetInitialPage(webapp2.RequestHandler):
    """
    Drive Initial Processing with Spreadsheets as the primary I/O.
    """

    def __init__(self, request, response):
        # webapp2 uses initialize instead of __init__, cause it's special
        self.initialize(request, response)
        self.__gclient__ = None
    
    @property
    def gclient(self):
        if self.__gclient__ is None:
            self.__gclient__ = GClient()

        assert self.__gclient__
        return self.__gclient__

    def get(self):
        #   1.) Get list of all spreadsheets in folder (GClient)
        signups_folder = self.gclient.docsClient.GetResourceById(
                                                settings['signups_folder_id')
        spreadsheets = self.gclient.spreadsheets(signups_folder)
        #   2.) Discard from list all spreadsheets already in Spreadsheet table
        #       (GSClient)
        new_spreadsheets = self.gclient.filterOutOldSpreadsheets(spreadsheets)
        #   3.) For all remaining spreadsheets, 
        #       1.) Convert spreadsheets to batch_dict and person_dict (GClient)
        #       2.) Import dicts into Batch and Person tables (InitialProcessor)  
        #            table (InitialProcessor & here)
        #           1.) If remaining spreadsheet meta sheet contains prev_gsid, add
        #               Batch Change, and use meta data from previous Batch
        #               (InitialProcessor & here).
        #   4.) For all remaining spreadsheets, for each row in Persons sheet
        #           (InitialProcessor)
        #       1.) Read in Row
        #       2.) Add info to Person table
        #       3.) If spreadsheet with prev_gsid, add entry to Person Change
        #   5.) For each Person with source_bid == current 
        #       1.) Generate/Save Opt-Out Token (OptOutProcessor)
        #       2.) Generate Email based on Opt-Out Token, Spreadsheet, and Person
        #           (InitialProcessor)
        #       3.) Send Email (Initial Processor)

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

from gdata.spreadsheets.client import WorksheetQuery, ListQuery, CellQuery
from gdata.spreadsheets.data import ListEntry, WorksheetEntry,\
                                    BuildBatchCellsUpdate
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

    def createBouncedSheet(self, spreadsheet_id, raw_sheet_id):
        # 1.) Get the top row of the Raw sheet
        cells = self.clients.spreadsheets.GetCells(spreadsheet_id, 
                raw_sheet_id, q=CellQuery(1, 1)).entry
                    
        # 2.) Make a new worksheet with 1 extra column (and an arbitrary
        # number of rows)
        result = self.clients.spreadsheets.AddWorksheet(spreadsheet_id, 
                                            'Bounced', 50, len(cells)+1)
        bounced_sheet_id = result.id.text.rsplit('/',1)[1]
        bounced_cells_update = BuildBatchCellsUpdate(spreadsheet_id,
                                    bounced_sheet_id)
        # 3.) Insert the header cells of the Raw sheet into the Bounced
        # sheet, plus a Bounced header 
        for i, cell in enumerate(cells):
            logging.info('Adding %s' % cell.content.text)
            bounced_cells_update.AddSetCell(1, i+1, cell.content.text)

        bounced_cells_update.AddSetCell(1, i+2, 'Bounced')
        self.clients.spreadsheets.batch(bounced_cells_update, force=True)

        return result

    def get(self):
        retval = ''
        bouncing_email = 'thisAddressDoesNotExistBecauseNoBodyWouldWantSuchALongAndRamblingAddress@gmail.com' 
        spreadsheet_id = '0AvVUbsCmsj1jdGpPVFhSR0lfZzhhQTJ2VWJ1dnlPMWc' 
        raw_sheet_id = 'od6'

        bounced_sheets = self.clients.spreadsheets.GetWorksheets(spreadsheet_id,
                                    q=WorksheetQuery(title='Bounced')).entry
        if len(bounced_sheets) == 0:
            bounced_sheets = [self.createBouncedSheet(spreadsheet_id,
                                raw_sheet_id)]
            
            # TODO Insert the name of the spreadsheet
            logging.info('Created Bounced sheet in spreadsheet.')

        if len(bounced_sheets) > 1:
            # This message should include the name of the spreadsheet. It 
            # should also be emailed.
            logging.warning('Multiple Bounce sheets found. \
                            Using the first one.')

        bounced_sheet = bounced_sheets[0]
        bounced_sheet_id = bounced_sheet.id.text.rsplit('/',1)[1]
        logging.debug('%s' % bounced_sheet_id)
        retval += '%s' % bounced_sheet_id 

        query = ListQuery(sq='email = "%s"' % bouncing_email)
        rows = self.clients.spreadsheets.GetListFeed(spreadsheet_id, 
                                                raw_sheet_id, q=query).entry
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


# Opt-Out Page
#   1.) User Visits Opt-out Page (here)
#   2.) Script checks for Out-Out Token (OptOutProcessor)
#   3a.) If Exists
#       1.) Ask user for Reason (here)
#       2.) Enter Opt-Out (OptOutProcessor)
#       3.) Remove Opt-Out Token (OptOutProcessor)
#   3b.) Else
#       1.) Display Error (here)

# Opt-Out Email Handler
#   Assumes all replies are out-outs
#   1.) Receives a reply (here)
#   2.) Retreive Person associated with email address and spreadsheet of
#       previous 2 days (here)
#   3.) Add entry in OptOut (OptOutProcessor)
#   4.) Remove associated Opt-Out Token (OptOutProcessor)

# Follow Up Script
#   1.) Delete all Opt-Out Tokens (OptOutProcessor)
#   2.) Get all Spreadsheet from 2 days prior (GClients)
#   3.) Get all Opt-Out from previous 2 days (here and OptOutProcessor)
#   4.) Get all Bounces from previous 2 days (here and BounceProcessor)
#   5.) For each Batch w/out-out (GClients)
#       1.) Create New Spreadsheet (GClients)
#       2.) Enter prev_bid in MetaSheet (GClients)
#       3.) Enter Row in Persons sheet for each Opt-Out + Reason & Occurred
#           (GClients)
#   6.) For each Batch with Bounce (GClients)
#       1.) Create New Spreadsheet (GClients)
#       2.) Ente prev_bid in Meta sheet (GClients)
#       3.) Enter Row in Persons sheet for each Bounce + Occurred (GClients)
#   7.) For each staff with a downloadable spreadsheet, email download links w/
#       directions (FinalProcessor)
#   8.) For each Batch
#       1.) Make a CSV (FinalProcessor)
#       2.) Add all Person without Bounce or Opt-Out (FinalProcessor)
#   9.) Email Uploader (FinalProcessor)

app = webapp2.WSGIApplication([('/', MainPage),
                                ('/test', TestPage)],
                              debug=True)
