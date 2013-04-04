# coding=utf-8

from gdata.spreadsheets.data import Spreadsheet, Worksheet, ListsFeed
from gdata.spreadsheets.client import WorksheetQuery

from clients import Clients
from settings import gdocs_settings
from models import EmailReference

def spreadsheet_id(spreadsheet):
    """
        Returns the true ID of the GData Spreadsheet.
    """
    if not isinstance(spreadsheet, Spreadsheet):
        raise TypeError("Must provide a GData Spreadsheet.")

    sid = spreadsheet.GetId().split('/')[-1]
    sid = sid.split('spreadsheet%3A')[-1]
    assert sid
    return sid

def worksheet_id(worksheet):
    """
        Returns the true ID of the GData Worksheet
    """

    if not isinstance(worksheet, Worksheet):
        raise TypeError("Must provide a GData Worksheet.")

    wid = worksheet.id.text.rsplit('/',1)[1]
    assert wid
    return wid

class SignupVerifier(object):

    def __init__():
        self.__clients__ = None

    @property
    def clients(self):
        if self.__clients__ is None:
            self.__clients__ = Clients()

        assert self.__clients__
        return self.__clients__

    def createBouncedSheet(self, spreadsheet_id, raw_sheet_id):
        """
            Creates a new worksheet via the Google Spreadsheets API dedicated 
            to displaying bouncing email addresses. The new worksheet will be
            titled 'Bounced'. It will be added to the spreadsheet associated
            with spreadsheet_id, and its header row will be based on the header
            row of the worksheet associated with raw_sheet_id.
        """
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

    def spreadsheets(self, folder):
        """
            Generates a list of Google Spreadsheets based on the Resource
            instance provided, which is assumed to be a folder. If the provided
            folder contains other folders, they will be ecursively searched for
            spreadsheets and other folders, breadth first.
            
            Returned spreadsheets will be Resource instances.
        """
        
        folders  = []

        contents = self.clients.docs.GetResources(uri=folder.content.src)
        for entry in contents.entry:
            if entry.GetResourceType() == 'folder':
                folders.append(entry)
            elif entry.GetResourceType() == 'spreadsheet':
                yield entry

        for folder in folders:
            for spreadsheet in self.spreadsheets(folder):
                yield spreadsheet

    def sendVerificationEmails(self, listsfeed):
        """
           Given a ListsFeed, sends an email to the email address associated
           with each row in the feed to verify that the email address exists,
           and to give the address the opportunity to opt-out. 
        """

        if not isinstance(listsfeed, ListsFeed):
            raise TypeError('Must provide a GData ListsFeed.')

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

