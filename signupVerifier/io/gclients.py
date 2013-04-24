# coding=utf-8
from gdata.docs.client import DocsClient, DocsQuery
from gdata.spreadsheets.client import SpreadsheetsClient, WorksheetQuery
from gdata.spreadsheets.data import SpreadsheetsFeed, Spreadsheet, Worksheet,\
					ListsFeed
from settings import gdocs_settings

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

class GClients(object):
    def __init__(self):
        self.__docsClient__ = None
        self.__spreadsheetsClient__ = None

    # For now, being lazy and using username/password.
    # Eventually, we should use Oauth.

    @property
    def docsClient(self):
        if self.__docsClient__ is None:
            self.__docsClient__ = DocsClient()
            self.__docsClient__.ClientLogin(gdocs_settings['username'],
                                gdocs_settings['password'], 
                                gdocs_settings['app_name'])

        assert self.__docsClient__
        return self.__docsClient__

    @property
    def spreadsheetsClient(self):
        if self.__spreadsheetsClient__ is None:
            self.__spreadsheetsClient__ = SpreadsheetsClient()
            self.__spreadsheetsClient__.ClientLogin(gdocs_settings['username'],
                                gdocs_settings['password'], 
                                gdocs_settings['app_name'])
        assert self.__spreadsheetsClient__
        return self.__spreadsheetsClient__

    def createBouncedSheet(self, spreadsheet_id, raw_sheet_id):
        """
            Creates a new worksheet via the Google Spreadsheets API dedicated 
            to displaying bouncing email addresses. The new worksheet will be
            titled 'Bounced'. It will be added to the spreadsheet associated
            with spreadsheet_id, and its header row will be based on the header
            row of the worksheet associated with raw_sheet_id.
        """
        # 1.) Get the top row of the Raw sheet
        cells = self.spreadsheetsClient.GetCells(spreadsheet_id, 
                raw_sheet_id, q=CellQuery(1, 1)).entry
                    
        # 2.) Make a new worksheet with 1 extra column (and an arbitrary
        # number of rows)
        result = self.spreadsheetsClient.AddWorksheet(spreadsheet_id, 
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
        self.spreadsheetsClient.batch(bounced_cells_update, force=True)

        return result

    def createBouncedSpreadsheet(self, batch):
        """
        Creates a new Google Spreadsheet to store the rows from the provided
        Batch instance that caused a bounce, and returns a Spreadsheet
        instance.

        The created Spreadsheet will have a meta sheet with just one attribute
        (id of the provided Batch). It will also have a people sheet that
        contains the data from Batch of all people who bounced, plus a Person
        ID number and a time at which the bounce was detected.

        Input:  batch - a Batch instance to create a bounced spreadsheet for.
        Output: A Spreadsheet instance that allows access to the created Google
                Spreadsheet.
        Side Effect: A new spreadsheet will be created on Google Drive, in a
            folder specified by the failed_spreadsheets_folder attribute of 
            this GClients instance.
        """
        pass

    def createOptOutSpreadsheet(self, batch):
        """
        Creates a new Google Spreadsheet to store the rows from the provided
        Batch instance that opted out, and returns a Spreadsheet instance.

        The created Spreadsheet will have a meta sheet with just one attribute
        (id of the provided Batch). It will also have a people sheet that
        contains the data from Batch of all people who opted out, plus a Person
        ID number and a reason given for opting out.

        Input:  batch - a Batch instance to create an opt-out spreadsheet for.
        Output: A Spreadsheet instance that allows access to the created Google
                Spreadsheet.
        Side Effect: A new spreadsheet will be created on Google Drive, in a
            folder specified by the failed_spreadsheets_folder attribute of 
            this GClients instance.
        """
        pass

    def spreadsheets(self, folder, query=None):
        """
        Generates a list of Google Spreadsheets based on the Resource
        instance provided, which is assumed to be a folder. If the provided
        folder contains other folders, they will be recursively searched 
        for spreadsheets and other folders, breadth first.
        
        Returned spreadsheets will be Resource instances.

        Input:  folder - a Resource instance representing a folder to be
                         search on Drive.
                query - a Query instance that is used to search for
                        spreadsheets with specific attributes.
        Output: a list of Resource instances that represent spreadsheets
                contained in the provided folder or its subfolders.
        """
        
        folders  = []

        contents = self.docsClient.GetResources(uri=folder.content.src, q=query)
        for entry in contents.entry:
            if entry.GetResourceType() == 'folder':
                folders.append(entry)
            elif entry.GetResourceType() == 'spreadsheet':
                yield entry

        for folder in folders:
            for spreadsheet in self.spreadsheets(folder):
                yield spreadsheet

