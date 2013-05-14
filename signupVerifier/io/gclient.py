# coding=utf-8
import datetime as dt
import re
from gdata.docs.client import DocsClient, DocsQuery
from gdata.docs.data import Resource
from gdata.spreadsheets.client import SpreadsheetsClient, WorksheetQuery,\
                                        CellQuery
from gdata.spreadsheets.data import SpreadsheetsFeed, Spreadsheet, Worksheet,\
					ListsFeed, ListEntry, BuildBatchCellsUpdate
from ..settings import settings
from ..models import Batch, BatchSpreadsheet
from ..processors.final_processor import getBatches
from google.appengine.api.datastore_types import Key

import logging

def spreadsheet_id(spreadsheet):
    """
        Returns the true ID of the GData Spreadsheet.
    """
    if not isinstance(spreadsheet, Resource):
        raise TypeError("Must provide a GData Resource that is a spreadsheet.")

    sid = spreadsheet.GetId().split('/')[-1]
    sid = sid.split('spreadsheet%3A')[-1]
    assert sid
    return sid

def worksheet_id(worksheet):
    """
        Returns the true ID of the GData Worksheet
    """

    #if not isinstance(worksheet, Worksheet):
    #    raise TypeError("Must provide a GData Worksheet.")

    wid = worksheet.id.text.rsplit('/',1)[1]
    assert wid
    return wid

meta_key_map = {
    'staff_name':'staffname',
    'staff_email':'staffemail',
    'event_name':'eventname',
    'event_date':'eventdate',
    'event_location':'eventlocation',
    'prev_batch':'prevbatch'
}

person_key_map = {
    'first_name':'firstname',
    'last_name':'lastname',
    'full_name':'fullname',
    'street_address':'streetaddress',
    'zip_code':'zipcode',
    'stated_race':'statedrace',
    'census_race':'censusrace',
    'year_born':'yearborn',
    'born_out_of_us':'bornoutofus',
    'born_where': 'personwhere',
    'parents_born_out_of_us':'parentsbornoutofus',
    'parents_born_where': 'parentswhere',
    'num_in_house': 'inhouse',
    'yrly_income': 'yrlyincome',
    'person_id': 'personid'
}


class GClient(object):
    def __init__(self):
        self.__docsClient__ = None
        self.__spreadsheetsClient__ = None
        self.__rawSheetIds__ = {}

    # For now, being lazy and using username/password.
    # Eventually, we should use Oauth.

    @property
    def docsClient(self):
        if self.__docsClient__ is None:
            self.__docsClient__ = DocsClient()
            self.__docsClient__.ClientLogin(settings['username'],
                                settings['password'], 
                                settings['app_name'])

        assert self.__docsClient__
        return self.__docsClient__

    @property
    def spreadsheetsClient(self):
        if self.__spreadsheetsClient__ is None:
            self.__spreadsheetsClient__ = SpreadsheetsClient()
            self.__spreadsheetsClient__.ClientLogin(settings['username'],
                                settings['password'], 
                                settings['app_name'])
        assert self.__spreadsheetsClient__
        return self.__spreadsheetsClient__

    #################################
    # dict <-> ListEntity converters
    #################################

    def dictToRow(self, d):
        """
            A general dict -> ListEntry converter. Does not make any changs to
            keys or data.
        """
        row = ListEntry()
        row.from_dict(d)
        return row

    def metaDictToRow(self, d):
        """
            Converts a meta dict to a spreadsheet ListRow. Modified version of
            the dict's keys will be used as the attribute names of the ListRow.

            Input: d - a dict that represents meta information about a batch
            Output: A ListRow instance containing the data of d
        """
        # Fix keys
        for dict_key, row_key in meta_key_map.iteritems():
            d[row_key] = d[dict_key]
            del d[dict_key]

        if hasattr(d, 'created'):
            del d['created']

        return self.dictToRow(d)

    def personDictToRow(self, d):
        """
            Converts a person dict to a spreadsheet ListRow. The dict's keys 
            will be used as the attribute names of the ListRow.

            Input: d - a dict that represents information about a person
            Output: A ListRow instance containing the data of d
        """
        #Casting
        def cast_datetime_to_str(dti):
            return dti.strftime('%m/%d/%Y %H:%M:%S')
        if 'occurred' in d and isinstance(d['occurred'], dt.datetime):
            d['occurred'] = cast_datetime_to_str(d['occurred'])

        # Clean/rearrange keys
        for dict_key, row_key in person_key_map.iteritems():
            if dict_key in d:
                if d[dict_key]:
                    d[row_key] = d[dict_key]
                del d[dict_key]
        for i,forum in enumerate(d['forums']):
            d['forum%s' % (i+1)] = forum
        del d['forums']
        if 'source_batch' in d:
            del d['source_batch']

        # Make sure that all attributes are strings and not None
        keys = d.keys()
        for key in keys:
            if not d[key]:
                del d[key]
            else:
                d[key] = '%s' % d[key]

        
        return self.dictToRow(d)

    def rowToDict(self, r):
        """
            A general ListEntry -> dict converter. Does not make any changes to
            keys or data.
        """
        if not isinstance(r, ListEntry):
            raise TypeError('Row to Dict conversion requires a ListRow,'\
                             + 'received a %s' % type(r))

        d = r.to_dict()
        return d

    def metaRowToDict(self, r):
        """
            Converts a row from a spreadsheet's Meta sheet into a dict.

            Input: r - a ListEntry
            Output: A dict containing the data of r
        """
        d = self.rowToDict(r)

        # Convert keys
        for dict_key, row_key in meta_key_map.iteritems():
            if row_key in d:
                d[dict_key] = d[row_key]
                del d[row_key]
                if isinstance(d[dict_key], basestring):
                    d[dict_key] = d[dict_key].strip()


        if 'event_date' in d:
            d['event_date'] = dt.datetime.strptime(d['event_date'],
                            "%m/%d/%Y").date()

        return d

    def personRowToDict(self, r):
        """
            Converts a spreadsheet ListEntry to a dict. The ListEntry's 
            attributes will be used as the dict's keys.

            Input: r - a ListRow
            Output: A dict containing the data of r
        """
        d = self.rowToDict(r)

        # Convert some keys
        for dict_key, row_key in person_key_map.iteritems():
            if row_key in d:
                d[dict_key] = d[row_key]
                del d[row_key]
                if isinstance(d[dict_key], basestring):
                    d[dict_key] = d[dict_key].strip()
        

        # Casting
        yes = ['yes', 'true']
        if 'num_in_house' in d and d['num_in_house']:
            d['num_in_house'] = int(d['num_in_house'])
        if 'yrly_income' in d and d['yrly_income']:
            d['yrly_income'] = int(d['yrly_income'])
        if 'born_out_of_us' in d and d['born_out_of_us']:
            d['born_out_of_us'] = d['born_out_of_us'].lower() in yes
        if 'parents_born_out_of_us' in d and d['parents_born_out_of_us']:
            d['parents_born_out_of_us'] = d['parents_born_out_of_us'].lower() \
                                                                        in yes
        # Forum column/dict keys - XML does not support tags with just numeric
        # names, and Google semi-randomly assigns XML names in these cases. So
        # we have to make the forum column names strings in the spreadsheet.
        # http://comments.gmane.org/gmane.org.google.api.docs/1306
        d['forums'] = []
        forum_keys = [key.replace('forum', '') for key in d.keys() 
                                        if key.startswith('forum')].sort()
        for i in forum_keys:
            if d[i] is not None:
                d['forums'].append(d[i])
            del d[i]

        return d

    
    #####################################
    # Google Drive Interaction Functions
    #####################################

    def rawSheetId(self, spreadsheet):
        """
            Returns the id of the Raw Worksheet for the provided spreadsheet
        """
        sid = spreadsheet_id(spreadsheet)
        if not sid in self.__rawSheetIds__:
            raw_sheets = self.spreadsheetsClient.GetWorksheets(
                            sid,
                            q=WorksheetQuery(
                                title=settings['raw_sheet_title']
                            )
                          ).entry
            if len(raw_sheets) != 1:
                raise IndexError('Spreadsheet %s should have 1 %s sheet' \
                                % (orig_spreadsheet_id, 
                                    settings['raw_sheet_title'])
                            )
            raw_sheet = raw_sheets[0]
            self.__rawSheetIds__[sid] = worksheet_id(raw_sheet)

        assert self.__rawSheetIds__[sid]
        return self.__rawSheetIds__[sid]

    def getListFeed(self, spreadsheet, title):
        """
            A general method for finding and retrieving the ListFeed for a
            sheet of a specified name (title).

            Input:  spreadsheet - a Resource instance of a spreadsheet with
                                    a sheet of the specified name.
                    title - The specific sheet to look for
            Output: A ListFeed of the specified sheet
        """
        if not isinstance(spreadsheet, Resource) and \
                        spreadsheet.GetResourceType() != 'spreadsheet':
            raise TypeError('a Resource instance of type spreadsheet required')

        sid = spreadsheet_id(spreadsheet)
        q = WorksheetQuery(title = title)
        sheets = self.spreadsheetsClient.GetWorksheets(sid, q=q).entry

        if len(sheets) == 0:
            raise LookupError('Provided spreadsheet does not have a %s sheet' % 
                                title)
        
        sheet_id = worksheet_id(sheets[0])
        return self.spreadsheetsClient.GetListFeed(sid, sheet_id).entry


    def getMetaListFeed(self, spreadsheet):
        """
            Finds and retrieves the ListFeed for the Meta sheet in the provided
            Spreadsheet.

            Input: spreadsheet - a Resource instance of a spreadsheet with a
                                 Meta sheet.
            Output: A ListFeed of the Meta sheet
        """
        return self.getListFeed(spreadsheet, settings['meta_sheet_title'])
        
    def getRawListFeed(self, spreadsheet):
        """
            Finds and retrieves the ListFeed for the Raw sheet in the provided
            Spreadsheet.

            Input: spreadsheet - a Resource instance of a spreadsheet with a
                                 Raw sheet.
            Output: A ListFeed of the Raw sheet
        """
        return self.getListFeed(spreadsheet, settings['raw_sheet_title'])

    def isFirstRawRowValid(self, spreadsheet):
        """
            Indicates weather the first row of the Raw sheet is a valid set of
            headers.

            Input:  spreadsheet - a Spreadsheet instance
            Output: True if the first row is the set of expected headers, False
                    otherwise
        """
        required_headers = ['email', 'firstname', 'lastname', 'fullname']
        sid = spreadsheet_id(spreadsheet)
        rsid = self.rawSheetId(spreadsheet)
        row_cells = self.spreadsheetsClient.GetCells(sid, rsid,
                                            q=CellQuery(1,1)).entry
        
        for i, cell in enumerate(row_cells):
            if cell.content.text.lower().replace(" ", "") in required_headers:
                required_headers.remove(cell.content.text.lower().replace(" ",
                                                                        ""))
                if not required_headers: 
                    break
        
        return not required_headers


    def deleteFirstRow(self, gsid, wsid):
        """
        Deletes the first row in the spreadsheet and worksheet associated with
        ogsid and wsid.

        Input:  gsid - ID of the Google Spreadsheet to modify
                wsid - ID of the worksheet to modify
        Output: True
        Side Effect: The first row on the corresponding worksheet on Google
                        Drive is deleted
        """
        # Deleting the first row actually involves:
        # 1.) Overwriting the values of the first row with those of the second
        #first_row = self.spreadsheetsClient.GetCells(gsid, wsid, 
        #                                            q=CellQuery(1, 1)).entry
        second_row = self.spreadsheetsClient.GetCells(gsid, wsid, 
                                                    q=CellQuery(2, 2)).entry
        first_row_update = BuildBatchCellsUpdate(gsid, wsid)
        for i, cell in enumerate(second_row):
            first_row_update.AddSetCell(1, i+1, cell.content.text)

        self.spreadsheetsClient.batch(first_row_update, force=True)

        # 2.) Deleting the second row
        rows = self.spreadsheetsClient.GetListFeed(gsid, wsid).entry
        second_row = rows[0] # Think about that for a second
        self.spreadsheetsClient.Delete(second_row)

        return True

    def deleteFirstRawRow(self, spreadsheet):
        """
            Deletes the first row in the Raw sheet of the provided spreadsheet.

            Input:  spreadsheet - a Spreadsheet instance
            Output: True
            Side Effect: The first row of the spreadsheet's Raw worksheet will
                            be deleted on Google Drive
        """
        sid = spreadsheet_id(spreadsheet)
        rsid = self.rawSheetId(spreadsheet)
        return self.deleteFirstRow(sid, rsid)

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
            new_raw_headers_update.AddSetCell(1, i+j+2, cell)
        self.spreadsheetsClient.batch(new_raw_headers_update, force=True)

        return result



    def cloneSpreadsheetForFailure(self, ogsid, batch_id, 
                                    suffix = None, headers_to_add = []):
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
        failed_signups_folder = self.docsClient.GetResourceById(
                                        settings['failed_signups_folder_id'])

        # Create a new Spreadsheet in Failed Signups folder
        new_spreadsheet_title = original_spreadsheet.title.text + suffix
        new_spreadsheet = Resource(type="spreadsheet",
                                    title=new_spreadsheet_title)
        new_spreadsheet = self.docsClient.CreateResource(new_spreadsheet,
                                        collection=failed_signups_folder)
        ngsid = spreadsheet_id(new_spreadsheet)

        # Turn the default blank sheet into the Meta sheet
        new_meta_sheet = self.spreadsheetsClient.GetWorksheets(ngsid,
                            q=WorksheetQuery(title='Sheet 1')).entry[0]
        new_meta_sheet.title.text = settings['meta_sheet_title']
        self.spreadsheetsClient.Update(new_meta_sheet)

        nmsid = worksheet_id(new_meta_sheet)
        header_cell = self.spreadsheetsClient.GetCell(ngsid, nmsid, 1, 1)
        header_cell.cell.input_value = 'prevbatch'
        result = self.spreadsheetsClient.update(header_cell)
        prev_batch_cell = self.spreadsheetsClient.GetCell(ngsid, nmsid, 2, 1)
        prev_batch_cell.cell.input_value = batch_id
        result = self.spreadsheetsClient.update(prev_batch_cell)

        # Create the cloned Raw sheet 
        new_raw_sheet = self.cloneRawSheet(ngsid, ogsid, headers_to_add)

        return (new_spreadsheet, new_raw_sheet)

    def createValidationErrorsSpreadsheet(self, batch):
        """
        Creates a new Google Spreadsheet to store the rows from the provided
        Batch instance that had validation errors.

        The created Spreadsheet will have a meta sheet with just one attribute
        (id of the provided Batch). It will also have a people sheet with
        headers identical to the headers of the spreadsheet associated with
        batch. Unlike the other create*Spreadsheet methods, this method does
        not insert the data of any persons. This is instead left up to the
        caller.

        Input:  batch - a Batch instance to create an opt-out spreadsheet for.
        Output: A tuple with a Spreadsheet instance for the newly created
            spreadsheet, and a Worksheet for the new spreadsheet's Raw sheet.
        Side Effect: A new spreadsheet will be created on Google Drive, in a
            folder specified by the failed_spreadsheets_folder attribute of 
            settings.
        """
        batch = Batch.verifyOrGet(batch)
        ogs = batch.spreadsheets.get()
        if not ogs:
            raise LookupError('Provided batch does not have a Google' + \
                                'Spreadsheet associated with it.')

        ogsid = ogs.gsid
        batch_id = str(batch.key())
        
        (new_spreadsheet, new_raw_sheet) = self.cloneSpreadsheetForFailure(
                                        ogsid, batch_id, " - Validation Errors")

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

        Input:  batch - a Batch instance or key of a Batch instance  to create 
                        a bounced spreadsheet for.
        Output:A tuple with a Spreadsheet instance for the newly created
            spreadsheet, and a Worksheet for the new spreadsheet's Raw sheet.
        Side Effect: A new spreadsheet will be created on Google Drive, in a
            folder specified by the failed_spreadsheets_folder attribute of 
            settings.
        """
        batch = Batch.verifyOrGet(batch)
        ogs = batch.spreadsheets.get()
        if not ogs:
            raise LookupError('Provided batch does not have a Google' + \
                                'Spreadsheet associated with it.')

        ogsid = ogs.gsid
        batch_id = str(batch.key())
        print "key: %s" % batch_id 

        
        headers_to_add = ['Occurred', 'Message', 'Person ID']
        (new_spreadsheet, new_raw_sheet) = self.cloneSpreadsheetForFailure(
                                            ogsid, batch_id, " - Bounced", 
                                                headers_to_add)
        ngsid = spreadsheet_id(new_spreadsheet)
        nbsid = worksheet_id(new_raw_sheet)

        # Get the Bounces for this batch and populate the cloned Raw sheet
        #TODO see about making this a batch operation
        for bounce in batch.bounces:
            bounce_dict = bounce.person.asDict()

            # Adjust some keys, add additional key/values
            bounce_dict['person_id'] = bounce.person.key()
            bounce_dict['occurred'] = bounce.occurred
            bounce_dict['message'] = bounce.message

            

            bounce_row = self.personDictToRow(bounce_dict)
            self.spreadsheetsClient.AddListEntry(bounce_row, ngsid, nbsid)

        return (new_spreadsheet, new_raw_sheet)



    def createOptOutSpreadsheet(self, batch):
        """
        Creates a new Google Spreadsheet to store the rows from the provided
        Batch instance that opted out, and returns a Spreadsheet instance.

        The created Spreadsheet will have a meta sheet with just one attribute
        (id of the provided Batch). It will also have a people sheet that
        contains the data from Batch of all people who opted out, plus a Person
        ID number and a reason given for opting out.

        Input:  batch - a Batch instance to create an opt-out spreadsheet for.
        Output: A tuple with a Spreadsheet instance for the newly created
            spreadsheet, and a Worksheet for the new spreadsheet's Raw sheet.
        Side Effect: A new spreadsheet will be created on Google Drive, in a
            folder specified by the failed_spreadsheets_folder attribute of 
            settings.
        """
        batch = Batch.verifyOrGet(batch)
        ogs = batch.spreadsheets.get()
        if not ogs:
            raise LookupError('Provided batch does not have a Google' + \
                                'Spreadsheet associated with it.')

        ogsid = ogs.gsid
        batch_id = str(batch.key())
        
        headers_to_add = ['Occurred', 'Reason', 'Person ID']
        (new_spreadsheet, new_raw_sheet) = self.cloneSpreadsheetForFailure(
                                            ogsid, batch_id, " - OptOuts", 
                                                headers_to_add)
        ngsid = spreadsheet_id(new_spreadsheet)
        nbsid = worksheet_id(new_raw_sheet)

        # Get the Optouts for this batch and populate the cloned Raw sheet
        #TODO see about making this a batch operation
        for optout in batch.optouts:
            optout_dict = optout.person.asDict()

            # Adjust some keys, add additional key/values
            optout_dict['occurred'] = optout.occurred
            optout_dict['reason'] = optout.reason
            optout_dict['person_id'] = optout.person.key()
            

            optout_row = self.personDictToRow(optout_dict)
            self.spreadsheetsClient.AddListEntry(optout_row, ngsid, nbsid)

        return (new_spreadsheet, new_raw_sheet)


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
        if not isinstance(folder, Resource) and \
                        folder.GetResourceType() != 'folder':
            raise TypeError('a Resource instance of type folder required')

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

    ####################
    # Validation Methods
    ####################

    def invalidPersonRow(self,r):
        """
            Checks that the provided list row contains at least the minimum,
            well formed forms needed to represent a person.

            Input: r - a ListRow
            Output: A list of validation errors. If the list row is valid, the
                list will be empty. Otherwise, it will contain one entry per
                validation error.
        """
        retval = [] 
        # Validate email address
        if not r.get_value('email') or not r.get_value('email').strip():
            retval.append('Missing email address')
        elif not re.match(r"[^@]+@[^@]+\.[^@]+", r.get_value('email')):
            retval.append('Malformed email address')
        # Validate first, last, and full names
        if (not r.get_value('firstname') or
                not r.get_value('firstname').strip()):
            retval.append('Missing first name')
        if (not r.get_value('lastname') or 
                not r.get_value('lastname').strip()):
            retval.append('Missing last name')
        if (r.get_value('fullname') is None or 
                not r.get_value('fullname').strip()):
            retval.append('Missing full name')
        # Validate at least one forum is selected
        # Easiest to convert to dict and look for special keys
        d = self.rowToDict(r)
        forum_keys = [key for key in d.keys() if key.startswith('forum')
                       and d[key] is not None] 
        if not forum_keys:
            retval.append('No forums selected for the user')

        return retval

    ####################################
    # Spreadsheet specific db functions
    ####################################

    def importBatchSpreadsheet(self, batch, spreadsheet):
        """
            Adds an entry to the database associated the provided batch with
            the provided spreadsheet_id.

            Input:  batch - a Batch instance of a key for a Batch instance
                    spreadsheet - Resource instance of type spreadsheet to 
                                    associate the batch with
            Output: An instance of BatchSpreadsheet if successful, False
                    otherwise
        """

        batch = Batch.verifyOrGet(batch)

        if not isinstance(spreadsheet, Resource) and \
                        spreadsheet.GetResourceType() != 'spreadsheet':
            raise TypeError('a Resource instance of type spreadsheet required')

        sid = spreadsheet_id(spreadsheet)

        bs_record = BatchSpreadsheet(gsid = sid, batch = batch)
        bs_record.put()

        return bs_record

    def filterOutOldSpreadsheets(self, spreadsheets):
        """
        Returns a list of spreadsheets from the provided list that are not
        already in the database.

        Input:  spreadsheets - list of Spreadsheet instances
        Output: a list of the difference between the input list and the list of
                spreadsheets already in the database.
        """
        q = BatchSpreadsheet.all()
        all_batch_spreadsheets = q.run()

        if all_batch_spreadsheets:
            existing_spreadsheet_ids = [bs.gsid for bs in
                                                    all_batch_spreadsheets]

            new_spreadsheets = [spreadsheet for spreadsheet in spreadsheets if
                spreadsheet_id(spreadsheet) not in existing_spreadsheet_ids]

        else:
            new_spreadsheets = spreadsheets

        return new_spreadsheets

    def getBatchSpreadsheets(self, before=dt.datetime.now() -
                            dt.timedelta(hours=50), after=dt.datetime.now() - 
                            dt.timedelta(hours=46)):
        """
        Returns an interable of BatchSpreadsheet instances. This is a wrapper
        of signupVerifier.processors.final_processor.getBatches.
        """
        for batch in getBatches(before=before, after=after):
            spreadsheet = batch.spreadsheets.get()
            if spreadsheet:
                yield spreadsheet
