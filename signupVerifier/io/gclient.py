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

    def personDictToRow(self, d):
        """
            Converts a dict to a spreadsheet ListRow. The dict's keys will be
            used as the attribute names of the ListRow.

            Input: d - a dict
            Output: A ListRow instance containing the data of d
        """
        # Clean/rearrange some keys
        d['person_where?'] = d['born_where']
        del d['born_where']
        d['parents_where?'] = d['parents_born_where']
        del d['parents_born_where']
        d['#_in_house'] = d['num_in_house']
        del d['num_in_house']
        for i,forum in enumerate(d['forums']):
            d[i] = forum
        del d['forums']
        if hasattr(d, 'source_batch']:
            del d['source_batch']
        
        # Create the ListRow
        row = ListRow()
        for key, value in d:
            row.SetValue(key, value)

        return row

    def personRowToDict(self, r):
        """
            Converts a spreadsheet ListRow to a dict. The ListRow's attributes
            will be used as the dict's keys.

            Input: r - a ListRow
            Output: A dict containing the data of r
        """
        d = dict()
        forum_keys = []
        for attribute in r.GetAttributes():
            attribute = attribute.text
            d[attribute] = r.GetValue(attribute)
            if attribute.isdigit():
                forum_keys.append(attribute)

        # Convert some keys
        d['born_where'] = d['person_where?']
        del d['person_where?']
        d['parents_born_where'] = d['parents_where?']
        del d['parents_where?']
        d['num_in_house'] = d['#_in_house']
        del d['#_in_house']
        d['forums'] = []
        for i in forum_keys.sorted():
            d['forums'].append(d[i])
            del d[i]



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

    def cloneSpreadsheetForFailure(self, ogsid, batch_id, 
                                    suffix = None, headers_to_add):
        """
        Creates a new Google Spreadsheet that is a clone of the
        structure/metadata of the spreadsheet used as input for the provided
        batch. The cloned spreadsheet is intended to be used by this system to
        output information on signups that failed. Returns a reference to the 
        resulting Spreadsheet and the Raw sheet as a tuple.

        Input:  ogsid - Original Google Spreadsheet ID; id of the spreadsheet
                        we are going to clone.
                batch_id - ID/key of the batch that these spreadsheets are
                            associated with.
                suffix - a string to be appended to the name of the original
                        spreadsheet to form the name of the new spreadsheet.
                headers_to_add - a list of headers to add to the Raw sheet in
                                 the cloned spreadsheet
        Output: a tuple that contains a Spreadsheet instance refering to the
                newly created spreadsheet and a Worksheet instance referring to
                the Raw sheet of the newly created spreadsheet.
        """
        
        # Get original spreadsheet
        original_spreadsheet = self.docsClient.GetResourceById(ogsid)

        # Get Failed Signups folder
        failed_signups_folder = self.docsClient.GetResouceById(
                                        settings['failed_signups_folder_id'])

        # Create a new Spreadsheet in Failed Signups folder
        new_spreadsheet_title = original_spreadsheet.title.text + suffix
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
        prev_batch_cell.cell.input_value = batch_id
        result = self.spreadsheetsClient.update(prev_batch_cell)

        # Create the cloned Raw sheet 
        new_raw_sheet = self.cloneRawSheet(ngsid, ogsid, headers_to_add)
        nbsid = workdsheet_id(new_raw_sheet)

        return (new_spreadsheet, new_raw_sheet)

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
        if not hasattr(batch, 'spreadsheets') or \
                len(batch.spreadsheets.get()) == 0:
            raise LookupError('Provided batch does not have a Google
                                Spreadsheet associated with it.')

        ogsid = batch.spreadsheets.get.gsid
        batch_id = batch.key()

        
        headers_to_add = ['Bounce Time', 'Bounce Message', 'Person ID']
        (new_spreadsheet, new_raw_sheet) = cloneSpreadsheetForFailure(ogsid, 
                                                batch_id, " - Bounced", 
                                                headers_to_add)
        ngsid = spreadsheet_id(new_spreadsheet)
        nbsid = worksheet_id(new_raw_sheet)

        # Get the Bounces for this batch and populate the cloned Raw sheet
        #TODO see about making this a batch operation
        for bounce in batch.bounces:
            bounce_dict = bounce.person.asDict()

            # Adjust some keys, add additional key/values
            bounce_dict['bounce_time'] = bounce.occurred
            bounce_dict['bounce_message'] = bounce.message
            bounce_dict['person_id'] = bounce.person.key()
            

            bounce_row = self.personDictToRow(bounce_dict)
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
        if not isinstance(batch, Batch):
            raise TypeError('batch must be a Batch instance')
        if not hasattr(batch, 'spreadsheets') or \
                len(batch.spreadsheets.get()) == 0:
            raise LookupError('Provided batch does not have a Google
                                Spreadsheet associated with it.')

        ogsid = batch.spreadsheets.get.gsid
        batch_id = batch.key()
        
        headers_to_add = ['OptOut Time', 'OptOut Message', 'Person ID']
        (new_spreadsheet, new_raw_sheet) = cloneSpreadsheetForFailure(ogsid, 
                                                batch_id, " - OptOuts", 
                                                headers_to_add)
        ngsid = spreadsheet_id(new_spreadsheet)
        nbsid = worksheet_id(new_raw_sheet)

        # Get the Optouts for this batch and populate the cloned Raw sheet
        #TODO see about making this a batch operation
        for optout in batch.optouts:
            optout_dict = optout.person.asDict()

            # Adjust some keys, add additional key/values
            optout_dict['optout_time'] = optout.occurred
            optout_dict['optout_message'] = optout.message
            optout_dict['person_id'] = optout.person.key()
            

            optout_row = self.personDictToRow(optout_dict)
            self.spreadsheetsClient.AddListEntry(optout_row, ngsid, nbsid)


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

