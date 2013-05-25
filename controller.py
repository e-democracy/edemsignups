# coding=utf-8

import datetime as dt
import webapp2
from urllib import urlencode
from google.appengine.ext.webapp import template
from google.appengine.api import mail
from signupVerifier.io.gclient import GClient, spreadsheet_id, worksheet_id
from signupVerifier.processors.initial_processor import importBatch,\
    importPerson, addBatchChange, addPersonChange, sendVerificationEmails
from signupVerifier.processors.optout_processor import createOptOutToken,\
    getPersonByOptOutToken, removeAllOptOutTokensFromBatches
from signupVerifier.processors.final_processor import getSuccessfulSignups,\
    personsToCsv, emailCsvs
from signupVerifier.models import Person
from signupVerifier.settings import settings

import logging

initial_template = 'templates/emails/initial_template.html'
initial_template_text = 'templates/emails/initial_template.txt'
optout_reason_template = 'templates/optout_request_reason.html'
optout_confirm_template = 'templates/optout_confirm.html'
followup_template = 'templates/emails/followup_template.html'
followup_template_text = 'templates/emails/followup_template.txt'

spreadsheet_export_url = \
    'https://spreadsheets.google.com/feeds/download/spreadsheets/Export'


def build_xlsx_download_link(gsid):
    params = urlencode({'key': gsid, 'exportFormat': 'xlsx'})
    return '?'.join([spreadsheet_export_url, params])


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
            return {'meta_dict': meta_dict, 'spreadsheet_url': spreadsheet_url,
                    'error': None, 'persons_success': [], 'persons_fail': [],
                    'errors_sheet_url': None}

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
                if not meta_list_feed:
                    raise LookupError('Coversheet contains no data')
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
                batch_log = new_batch_log(
                            {
                                'staff_email': settings['admin_email_address'],
                                'event_name': 'ERROR',
                                'event_date': 'ERROR'
                            }, build_xlsx_download_link(
                                spreadsheet_id(new_spreadsheet)))
                batch_logs.append(batch_log)
                batch_log['error'] = e
                continue

            # Create a batch log for the new batch
            batch_log = new_batch_log(meta_dict,
                            new_spreadsheet.FindHtmlLink())
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
            validations_spreadsheet = None
            validations_worksheet = None
            validations_listfeed = None
            error_i = 0
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

                batch.submitted_persons += 1

                # Make sure we have some level of valid data
                validation_errors = self.gclient.invalidPersonRow(
                                        person_list_entry)
                if validation_errors:
                    batch.invalid_persons += 1
                    # Need to patch together a dict on an error.
                    # Blug, this is ugly
                    errors_str = '; '.join(validation_errors)
                    batch_log['persons_fail'].append((
                        {'email': person_list_entry.get_value('email'),
                         'full_name': person_list_entry.get_value('fullname')
                        }, errors_str))

                    # TODO Add the row to a spreadsheet for validation errors,
                    # and create that spreadsheet if it doesn't exist.
                    if not validations_listfeed:
                        validations_spreadsheet, validations_worksheet = \
                            self.gclient.createValidationErrorsSpreadsheet(
                                batch)
                        vgsid = spreadsheet_id(validations_spreadsheet)
                        vwsid = worksheet_id(validations_worksheet)
                        validations_listfeed = \
                                self.gclient.spreadsheetsClient.GetListFeed(
                                    vgsid, vwsid).entry
                        batch_log['errors_sheet_url'] =\
                                build_xlsx_download_link(
                                    spreadsheet_id(validations_spreadsheet))

                    error_entry = validations_listfeed[error_i]
                    logging.info(error_entry)
                    error_i += 1
                    error_entry.from_dict(person_list_entry.to_dict())
                    error_entry.set_value('errors', errors_str)
                    self.gclient.spreadsheetsClient.Update(error_entry,
                            force=True)
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
            optout_base_url = '/'.join([
                                self.request.host_url.rpartition(':')[0],
                                'optout'])
            batch_log = sendVerificationEmails(batch, persons, optout_tokens,
                            optout_base_url, batch_log)

            # Save the model with updated tracking
            batch.put()

        # Process the batch_logs
        staff_templates = dict()
        for batch_log in batch_logs:
            if 'staff_email' not in batch_log['meta_dict']:
                # Staff person forgot to include their email address. Tell the
                # tech guy.
                staff_email = settings['admin_email_address']
            else:
                staff_email = batch_log['meta_dict']['staff_email']

            if not staff_email in staff_templates:
                staff_templates[staff_email] = \
                        {
                            'failed_batches': [],
                            'successful_batches': []
                        }

            template_values = staff_templates[staff_email]

            if batch_log['error']:
                template_values['failed_batches'].append(
                        {
                            'url': batch_log['spreadsheet_url'],
                            'event_name': batch_log['meta_dict']['event_name'],
                            'event_date': batch_log['meta_dict']['event_date'],
                            'error': batch_log['error']
                        })
            else:
                successful_batch = \
                    {
                        'url': batch_log['spreadsheet_url'],
                        'event_name': batch_log['meta_dict']['event_name'],
                        'event_date': batch_log['meta_dict']['event_date'],
                        'successful_persons': [],
                        'failed_persons': [],
                        'errors_sheet_url': batch_log['errors_sheet_url']
                    }

                for person in batch_log['persons_success']:
                    successful_batch['successful_persons'].append(
                        {
                            'email': person.email,
                            'full_name': person.full_name
                        })
                for person, error in batch_log['persons_fail']:
                    if isinstance(person, Person):
                        email = person.email
                        full_name = person.full_name
                    else:
                        email = person['email']
                        full_name = person['full_name']
                    successful_batch['failed_persons'].append(
                        {
                            'email': email,
                            'full_name': full_name,
                            'error': error
                        })

                template_values['successful_batches'].append(successful_batch)

        retval = ''
        for email, template_values in staff_templates.iteritems():
            email_html = template.render(initial_template, template_values)
            email_text = template.render(
                            initial_template_text,
                            template_values)
            message = mail.EmailMessage(
                        sender=settings['app_email_address'],
                        subject=settings['subject_initial_staff'])
            message.to = email
            message.cc = settings['signups_email_address']
            message.html = email_html
            message.body = email_text
            message.send()

            retval += email_html
        self.response.headers['Content-Type'] = 'text/html'
        self.response.write(retval)

from bounce_handler import BounceHandler
from google.appengine.ext.webapp.mail_handlers import BounceNotification


class TestBouncePage(webapp2.RequestHandler):

    def get(self):
        """
            Simply takes received arguments and passes them on the Bounce
            Handler.
        """
        bounce = BounceNotification({
            'original-from': self.request.get('original-from'),
            'original-to': self.request.get('original-to'),
            'original-subject': self.request.get('original-subject'),
            'original-text': self.request.get('original-text'),
            'notification-from': self.request.get('notification-from'),
            'notification-to': self.request.get('notification-to'),
            'notification-subject': self.request.get('notification-subject'),
            'notification-text': self.request.get('notification-text'),
            'raw-message': self.request.get('raw-message')})

        bh = BounceHandler()
        return bh.receive(bounce)

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

        before = None
        if self.request.get('before') == 'now':
            before = dt.datetime.now()

        # Follow Up Script
        #   1.) Get BatchSpreadsheets from 46 to 50 hours ago
        #   2.) Get associated Batches
        if before:
            batches = [bs.batch for bs in
                    self.gclient.getBatchSpreadsheets(before=before)]
        else:
            batches = [bs.batch for bs in self.gclient.getBatchSpreadsheets()]

        if not batches:
            return
        staff_followups = dict()
        successes = []
        for batch in batches:
            #   3.) Delete all Opt-Out Tokens associated with Batches
            #   4.) Get all Opt-Outs associated with Batches
            #   5.) Get all Bounces associated with Bounces
            removeAllOptOutTokensFromBatches([batch])
            optouts = batch.optouts.fetch(limit=None)
            bounces = batch.bounces.fetch(limit=None)

            # Update Batch tracking
            batch.optedout_persons = len(optouts)
            batch.bounced_persons = len(bounces)
            batch.put()

            # 6.) For each Batch w/opt-out
            if optouts:
                # 1.) Clone associated Spreadsheet for Optouts (GClient)
                ooss, oows = self.gclient.createOptOutSpreadsheet(batch)
                if not batch.staff_email in staff_followups:
                    staff_followups[batch.staff_email] = new_followup_struct()
                optout_xlsx_url = build_xlsx_download_link(
                                    spreadsheet_id(ooss))
                staff_followups[batch.staff_email]['optouts'].append(
                        (batch, optout_xlsx_url))
            #   7.) For each Batch with Bounce (GClients)
            if bounces:
                # 1.) Clone associated Spreadsheet for Bounce (GClients)
                bss, brws = self.gclient.createBouncedSpreadsheet(batch)
                if not batch.staff_email in staff_followups:
                    staff_followups[batch.staff_email] = new_followup_struct()
                bounce_xlsx_url = build_xlsx_download_link(spreadsheet_id(bss))
                logging.info('bounces spreadsheet: %s' % bounce_xlsx_url)
                staff_followups[batch.staff_email]['bounces'].append(
                        (batch, bounce_xlsx_url))

            successful_signups = getSuccessfulSignups(batch)
            successes.append((batch, successful_signups))

        #   8.) For each staff with a downloadable spreadsheet, email download
        #       links w/directions (FinalProcessor)
        retval = ""
        for staff_address, followup in staff_followups.iteritems():
            if followup['optouts'] or followup['bounces']:
                email_html = template.render(followup_template, followup)
                email_text = template.render(followup_template_text, followup)
                message = mail.EmailMessage(
                            sender=settings['app_email_address'],
                            subject=settings['subject_followup_staff'])
                message.to = staff_address
                message.cc = settings['signups_email_address']
                message.html = email_html
                message.body = email_text
                message.send()

                retval += email_html

        #   9.) For each Batch
        #       1.) Make a CSV of successful signups (FinalProcessor)
        csvs = [("%s - %s.csv" % (batch.event_name, batch.staff_name),
                personsToCsv(successful_signups))
                for batch, successful_signups in successes]

        #   10.) Email Uploader (FinalProcessor)
        emailCsvs(csvs, batches)

        self.response.headers['Content-Type'] = 'text/html'
        self.response.write(retval)

routes =  [
            ('/spreadsheet_initial', SpreadsheetInitialPage),
            ('/test_bounce', TestBouncePage),
            ('/spreadsheet_followup', SpreadsheetFollowupPage)
          ]

app = webapp2.WSGIApplication(routes = routes, debug = True)
