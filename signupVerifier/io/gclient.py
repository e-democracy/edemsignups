# coding=utf-8
from gdata.docs.client import DocsClient, DocsQuery
from gdata.docs.data import Resource
from gdata.spreadsheets.client import SpreadsheetsClient, WorksheetQuery
from gdata.spreadsheets.data import SpreadsheetsFeed, Spreadsheet, Worksheet,\
					ListsFeed, ListRow
from ..settings import settings
from ..models import Batch

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

class GClient(object):
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

    def dictToRow(self, d):
        """
            Converts a dict to a spreadsheet ListRow. The dict's keys will be
            used as the attribute names of the ListRow.

            Input: d - a dict
            Output: A ListRow instance containing the data of d
        """
        row = ListRow()
        for key, value in d:
            row.SetValue(key, value)

        return row


    def cloneRawSheet(self, new_spreadsheet_id, orig_spreadsheet_id, 
                        headers_to_add):
        """
            Creates a new worksheet via the Google Spreadsheets API for people 
            who were not successfully signed up. Its header row will be based 
            on the header row of the worksheet associated with
            orig_raw_sheet_id, plus headers_to_add.

            
            Input:  new_spreadsheet_id - Google Drive ID of the new spreadsheet
                    orig_spreadsheet_id - Drive ID of the original spreadsheet
                    headers_to_add - A list of strings, representing headers
                                     that are to be added to the new 
                                    spreadsheet's Raw sheet, in addition to 
                                    headers from the original spreadsheet's Raw
                                    sheet.
            Output: A Worksheet instance associated with the newly created Raw
                    worksheet on Drive.
            Side Effects: A new worksheet, with its header row populated, will
                          be created in the spreadsheet identified by 
                          new_spreadsheet_id, on Drive.
        """
        # 1.) Get the header row of the original spreadsheet's Raw sheet
        orig_raw_sheets = self.spreadsheetsClient.GetWorksheets(
                            orig_spreadsheet_id,
                            q=WorksheetQuery(
                                title=settings['raw_sheet_title']
                            )
                          ).entry
        if len(orig_raw_sheets) != 1:
            raise IndexError('Spreadsheet %s should have exactly 1 %s sheet' \
                                % (orig_spreadsheet_id, 
                                    settings['raw_sheet_title'])
                            )
        orig_raw_sheet = orig_raw_sheets[0]
        orig_raw_sheet_id = worksheet_id(orig_raw_sheet)
        orig_headers = self.spreadsheetsClient.GetCells(orig_spreadsheet_id, 
                        orig_raw_sheet_id, q=CellQuery(1, 1)).entry
                    
        # 2.) Make a new worksheet with extra columns for the additional
        # headers (and an arbitrary number of rows)
        result = self.spreadsheetsClient.AddWorksheet(new_spreadsheet_id, 
                                settings['raw_sheet_title'], 50, 
                                len(orig_headers)+len(headers_to_add))
        new_raw_sheet_id = worksheet_id(result)
        new_raw_headers_update = BuildBatchCellsUpdate(new_spreadsheet_id,
                                    new_raw_sheet_id)

        # 3.) Insert the header cells of the original spreadsheet's Raw sheet 
        # into the Raw sheet of the new spreadsheet, plus additional headers 
        for i, cell in enumerate(orig_headers):
            new_raw_headers_update.AddSetCell(1, i+1, cell.content.text)

        for j, cell in enumerate(headers_to_add):
            new_raw_headers_update.AddSetCell(1, i+j, cell)
        self.spreadsheetsClient.batch(new_raw_headers_update, force=True)

        return result

    def createBouncedSpreadsheet(self, batch):
        """
        Creates a new Google Spreadsheet to store the rows from the provided
        Batch instance that caused a bounce, and returns a Spreadsheet
        instance.

        The created Spreadsheet will have a meta sheet with just one attribute
        (id of the provided Batch). It will also have a Raw sheet that
        contains the data from Batch of all people who bounced, plus a Person
        ID number, a time at which the bounce was detected, and the bounce
        message.

        Input:  batch - a Batch instance to create a bounced spreadsheet for.
        Output: A Spreadsheet instance that allows access to the created Google
                Spreadsheet.
        Side Effect: A new spreadsheet will be created on Google Drive, in a
            folder specified by the failed_spreadsheets_folder attribute of 
            settings.
        """
        if not isinstance(batch, Batch):
            raise TypeError('batch must be a Batch instance')

        # Get original spreadsheet
        ogsid = batch.spreadsheets.get.gsid
        original_spreadsheet = self.docsClient.GetResourceById(ogsid)

        # Get Failed Signups folder
        failed_signups_folder = self.docsClient.GetResouceById(
                                        settings['failed_signups_folder_id'])

        # Create a new Spreadsheet in Failed Signups folder
        new_spreadsheet_title = original_spreadsheet.title.text + " - Bounced"
        new_spreadsheet = Resource(type="spreadsheet",
                                    title=new_spreadsheet_title)
        new_spreadsheet = self.docsClient.CreateResource(new_spreadsheet,
                                        collection=failed_signups_folder)
        ngsid = spreadsheet_id(new_spreadsheet)

        # Create and populate the Meta sheet
        result = self.spreadsheetsClient.AddWorksheet(spreadsheet_id, 
                                settings['raw_sheet_title'], 50, 1)
        header_cell = self.spreadsheetsClient.GetCell(ngsid, 1, 1)
        header_cell.cell.input_value = 'prev_batch'
        result = self.spreadsheetsClient.update(header_cell)
        prev_batch_cell = self.spreadsheetsClient.GetCell(ngsid, 2, 1)
        prev_batch_cell.cell.input_value = batch.key()
        result = self.spreadsheetsClient.update(prev_batch_cell)

        # Create the cloned Raw sheet 
        headers_to_add = ['Bounce Time', 'Bounce Message', 'Person ID']
        new_raw_sheet = self.cloneRawSheet(ngsid, ogsid, headers_to_add)
        nbsid = workdsheet_id(new_raw_sheet)

        # Get the Bounces for this batch and populate the cloned Raw sheet
        for bounce in batch.bounces:
            bounce_row = bounce.person.asDict()

            # Adjust some keys, add additional key/values
            bounce_row['bounce_time'] = bounce.occurred
            bounce_row['bounce_message'] = bounce.message
            bounce_row['person_id'] = bounce.person.key()
            bounce_row['person_where?'] = bounce_row['born_where']
            del bounce_row['born_where']
            bounce_row['parents_where?'] = bounce_row['parents_born_where']
            del bounce_row['parents_born_where']
            bounce_row['#_in_house'] = bounce_row['num_in_house']
            del bounce_row['num_in_house']
            for i,forum in enumerate(bounce.person.forums):
                bounce_row[i] = forum
            del bounce_row['forums']
            del bounce_row['source_batch']

            bounce_row = self.dictToRow(bounce_dict)
            self.spreadsheetsClient.AddListEntry(bounce_row, ngsid, nbsid)
        





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
            settings.
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

