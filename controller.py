# coding=utf-8

import webapp2
from google.appengine.ext.webapp import template
from google.appengine.api import mail
from signupVerifier.io.gclient import GClient
from signupVerifier.processors.initial_processor import importBatch,\
                    importPerson, addBatchChange, addPersonChange,\
                    sendVerificationEmails 
from signupVerifier.processors.optout_processor import createOptOutToken,\
                    getPersonByOptOutToken, processOptOut
from signupVerifier.models import Person
from signupVerifier.settings import settings

import logging
log_template = 'templates/log_template.html'
optout_reason_template = 'templates/optout_request_reason.html'
optout_confirm_template = 'templates/optout_confirm.html'
followup_template = 'templates/followup_template.html'


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
        # 0.) Setup output lists
        batch_logs = []
        def new_batch_log(meta_dict, spreadsheet_url):
            return {'meta_dict' : meta_dict, 'spreadsheet_url': spreadsheet_url,
                    'error': None, 'persons_success': [], 'persons_fail': []}

        # 1.) Get list of all spreadsheets in folder 
        signups_folder = self.gclient.docsClient.GetResourceById(
                                                settings['signups_folder_id'])
        spreadsheets = self.gclient.spreadsheets(signups_folder)

        # 2.) Discard from that list all spreadsheets already processed
        new_spreadsheets = self.gclient.filterOutOldSpreadsheets(spreadsheets)

        # 3.) Process the remaining spreadsheets
        for new_spreadsheet in new_spreadsheets:

            batch = None
            batchSpreadsheet = None
            try:
                #  1.) Convert spreadsheets meta info to batch_dict
                meta_list_feed = self.gclient.getMetaListFeed(new_spreadsheet)
                meta_dict = self.gclient.metaRowToDict(meta_list_feed[0])
                
                # 2.) Import meta_dict into Batch table  
                if 'prev_batch' in meta_dict:
                    batch = addBatchChange(meta_dict, meta_dict['prev_batch'])
                    meta_dict = batch.asDict()
                    batchSpreadsheet = self.gclient.importBatchSpreadsheet(
                                                        batch, new_spreadsheet)
                else:
                    batch = importBatch(meta_dict)

                    batchSpreadsheet = self.gclient.importBatchSpreadsheet(
                                                        batch, new_spreadsheet)
            except Exception as e:
                # Something serious has happened. Need to piece together a
                # batch_log for the tech guy and undo any changes to the DB
                if batch and batch.is_saved():
                    batch.delete()
                if batchSpreadsheet and batchSpreadsheet.is_saved():
                    batchSpreadsheet.delete()

                logging.exception(e)
                batch_log = new_batch_log({
                            'staff_email': settings['username'],
                            'event_name': 'ERROR',
                            'event_date': 'ERROR'
                            }, new_spreadsheet.FindHtmlLink())
                batch_logs.append(batch_log)
                batch_log['error'] = e
                continue

            # Create a batch log for the new batch
            batch_log = new_batch_log(meta_dict,new_spreadsheet.FindHtmlLink())
            batch_logs.append(batch_log)
            
            # 3.) Convert and import persons and create OptOutTokens
            # Make sure the first row of the Raw sheet is the header row we 
            # want, since sometimes meta headers are placed in these 
            # spreadsheets
            while not self.gclient.isFirstRawRowValid(new_spreadsheet):
                self.gclient.deleteFirstRawRow(new_spreadsheet)

            person_list_feed = self.gclient.getRawListFeed(new_spreadsheet)

            persons = []
            optout_tokens = dict()
            for person_list_entry in person_list_feed:
                # Because of how the Full Name column is a formula output that
                # always includes an empty space, we need to first check that
                # several values exist to be sure that the row is actually data
                # entered by a user.

                if ((person_list_entry.get_value('email') is None or
                     not person_list_entry.get_value('email').strip()) and 
                    (person_list_entry.get_value('firstname') is None or 
                     not person_list_entry.get_value('firstname').strip()) 
                    and 
                    (person_list_entry.get_value('lastname') is None or
                     not person_list_entry.get_value('lastname').strip())
                    and 
                    (person_list_entry.get_value('fullname') is None or
                     not person_list_entry.get_value('fullname').strip())):
                    continue

                # Make sure we have some level of valid data
                validation_errors = self.gclient.invalidPersonRow(
                                                            person_list_entry)
                if validation_errors:
                    # Need to patch together a dict on an error.
                    # Blug, this is ugly
                    batch_log['persons_fail'].append((
                        {'email':person_list_entry.get_value('email'),
                         'full_name':person_list_entry.get_value('fullname')
                        }, '; '.join(validation_errors)))

                    # TODO Add the row to a spreadsheet for validation errors,
                    # and create that spreadsheet if it doesn't exist.
                    continue

                person_dict = self.gclient.personRowToDict(person_list_entry)
                try:
                    if 'person_id' in person_dict:
                        person_dict['source_batch'] = batch.key()
                        person = addPersonChange(person_dict, 
                                                    person_dict['person_id'])
                    else:
                        person = importPerson(person_dict, batch)

                    persons.append(person)
                    optout_tokens[person.key()] = createOptOutToken(batch,
                                                                    person)
                except Exception as e:
                    logging.exception(e)
                    batch_log['persons_fail'].append((person_dict, e))
            
            # 4.) Generate and send Emails! 
            batch_log = sendVerificationEmails(batch, persons, optout_tokens, 
                                                batch_log)


        # Process the batch_logs
        staff_templates = dict()
        for batch_log in batch_logs:
            if 'staff_email' not in batch_log['meta_dict']:
                # Staff person forgot to include their email address. Tell the
                # tech guy.
                staff_email = settings['username']
            else:
                staff_email = batch_log['meta_dict']['staff_email']

            if not staff_email in staff_templates:
               staff_templates[staff_email] = {
                            'failed_batches' : [],
                            'successful_batches': []
                        }
            template_values = staff_templates[staff_email]

            if batch_log['error']:
                template_values['failed_batches'].append(
                            {'url': batch_log['spreadsheet_url'],
                             'event_name': batch_log['meta_dict']['event_name'],
                             'event_date': batch_log['meta_dict']['event_date'],
                             'error': batch_log['error']})
            else:
                successful_batch = {
                    'url': batch_log['spreadsheet_url'],
                    'event_name': batch_log['meta_dict']['event_name'],
                    'event_date': batch_log['meta_dict']['event_date'],
                    'successful_persons' : [],
                    'failed_persons': []}
                for person in batch_log['persons_success']:
                    successful_batch['successful_persons'].append({
                        'email' : person.email,
                        'full_name' : person.full_name
                    })
                for person, error in batch_log['persons_fail']:
                    if isinstance(person, Person):
                        email = person.email
                        full_name = person.full_name
                    else:
                        email = person['email']
                        full_name = person['full_name']
                    successful_batch['failed_persons'].append({
                        'email' : email,
                        'full_name': full_name,
                        'error': error
                    })

                template_values['successful_batches'].append(successful_batch)

        retval = ''
        for email, template_values in staff_templates.iteritems():
            retval += template.render(log_template, template_values)
        self.response.headers['Content-Type'] = 'text/html'
        self.response.write(retval)

class OptOutPage(webapp2.RequestHandler):

    # Opt-Out Page
    #   1.) User Visits Opt-out Page (here)
    #   2.) Script checks for Out-Out Token (OptOutProcessor)
    #   3a.) If Exists
    #       1.) Ask user for Reason (here)
    #       2.) Enter Opt-Out (OptOutProcessor)
    #       3.) Remove Opt-Out Token (OptOutProcessor)
    #   3b.) Else
    #       1.) Display Error (here)

    def get(self):
        self.handleRequest()

    def post(self):
        self.handleRequest()

    def handleRequest(self):
        params = self.request.params

        # processOptOut and getPersonByOptOutToken will both throw LookupError
        # if the provided token can not be found.
        try:
            if 'token' in params:
                token = params['token']
                logging.info('Got token %s' % token) 
                if 'reason' in params:
                    reason = params['reason']
                    optout = processOptOut(token, reason)
                    # Display confirmation page
                    retval = template.render(optout_confirm_template, {}) 
                else:
                    person = getPersonByOptOutToken(token)
                    # Display page requesting reason for optout
                    values = {'token': token}
                    retval = template.render(optout_reason_template, values)
            else:
                # Display a 404
                logging.info('No Token')
                self.abort(404)

            self.response.write(retval)

        except LookupError as e:
            #Display 404
            self.abort(404)

        

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



# Opt-Out Email Handler
#   Assumes all replies are out-outs
#   1.) Receives a reply (here)
#   2.) Retreive Person associated with email address and spreadsheet of
#       previous 2 days (here)
#   3.) Add entry in OptOut (OptOutProcessor)
#   4.) Remove associated Opt-Out Token (OptOutProcessor)

class SpreadsheetFollowupPage(webapp2.RequestHandler):

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
        # Used to organize what to send to who
        def new_followup_struct():
            return {'optouts': [],
                    'bounces': []}

        # Follow Up Script
        #   1.) Get BatchSpreadsheets from 46 to 50 hours ago
        #   2.) Get associated Batches
        batches = [bs.batch for bs in self.gclient.getBatchSpreadsheets()]
        staff_followups = dict()
        successes = []
        for batch in batches:
        #   3.) Delete all Opt-Out Tokens associated with Batches (OptOutProcessor)
        #   4.) Get all Opt-Outs associated with Batches 
        #   5.) Get all Bounces associated with Bounces
            removeAllOptOutTokensFromBatches([batch])
            optouts = batch.optouts.run()
            bounces = batch.bounces.run()
            
        # 6.) For each Batch w/opt-out
            if optouts:
            # 1.) Clone associated Spreadsheet for Optouts (GClient)
                ooss, brws = self.gclient.createOptOutSpreadsheet(batch)
                if not batch.staff_email in staff_followups:
                    staff_followups[batch.staff_email] = new_followup_struct()
                staff_followups[batch.staff_email]['optouts'].append((batch,
                ooss))
        #   7.) For each Batch with Bounce (GClients)
            if bounces:
            # 1.) Clone associated Spreadsheet for Bounce (GClients)
                bss, brws = self.gclient.createBounceSpreadsheet(bounces)
                if not batch.staff_email in staff_followups:
                    staff_followups[batch.staff_email] = new_followup_struct()
                staff_followups[batch.staff_email]['bounces'].append((batch,
                                                                        bss))

            successful_signups = getSuccessfulSignups(batch)
            successes.append((batch, successful_signups))

        #   8.) For each staff with a downloadable spreadsheet, email download 
        #       links w/directions (FinalProcessor)
        for email,followup in enumerate(staff_followups):
            if followup['optouts'] or followup['bounces']:
                email_body = template.render(followup_template, followup)
                mail.send_mail(settings['email_as'], email, 
                                'Submitted Signups Followup', email_body)
                
        #   9.) For each Batch
        #       1.) Make a CSV of successful signups (FinalProcessor)
        csvs = [("% - %.csv" % (batch.event_name, batch.staff_name),
                    personsToCsv(successful_signups)) 
                    for batch, successful_signups in successes]

        #   10.) Email Uploader (FinalProcessor)
        emailCsvs(csvs) 
            

app = webapp2.WSGIApplication([('/', SpreadsheetInitialPage),
                                ('/test', TestPage),
                                ('/optout', OptOutPage),
                                ('/followup', SpreadsheetFollowupPage)],
                              debug=True)
