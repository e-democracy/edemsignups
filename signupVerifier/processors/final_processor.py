# coding=utf-8
import datetime as dt
import csv
from google.appengine.ext.webapp import template
from google.appengine.api import mail


from StringIO import StringIO
from ..models import Batch

csvs_ready_template= 'signupVerifier/processors/csvs_ready_to_upload.html'

ordered_person_attributes_for_upload = [                                        
    'group_id',                                                                 
    'email',                                                                    
    'first_name',                                                               
    'last_name',                                                                
    'full_name',                                                                
    'neighborhood',                                                             
    'street_address',                                                           
    'city',                                                                     
    'state',                                                                    
    'zip_code',                                                                 
    'phone']

def getBatches(before=dt.datetime.now() - dt.timedelta(hours=50), 
                after=dt.datetime.now() - dt.timedelta(hours=46)):
    """
    Retrieves an interable of Batch models. If before and/or after are
    provided, these are used to limit retrived Batch instances to only those
    from before or after the provided datetimes.

    Input:  before - Optional datetime indicating the newest batches to return
            after - Optional datetime indicating the oldest batches to return
    Output: Interable of Batch instances
    """
    q = Batch.all()
    if before:
        q.filter('created <=', before)
    if after:
        q.filter('created >=', after)
    for batch in q.run():
        yield batch

def emailFollowUpToStaffPerson(staff_name, staff_email, batch_links, 
                        email_template):
    """
    Sends an email to the specified staff member with links and
    instructions that can be used to review and fix Persons who opted out
    or bounced.
    
    Input:  staff_name - String indicating the name of the staff person
            staff_email - The staff person's email address
            batch_links - a list of URLs that the staff person can visit to
                            view/fix/download the data of persons who 
                            bounced or opted out
            email_template - Template used to create the email
    Output: True if the email is sent successfully, False otherwise
    Side Effect: An email is sent
    """
    pass

def emailFollowUpsToStaff(batches, email_template, url_func):
    """
    Based on the provided batches, generates and sends emails to staff
    people with the information needed to follow up on Persons who bounced
    or opted out. 

    The method will search the provided list of Batches for Perons who
    bounced or opted out. It will then use the provided email_template and
    url_func to generate one email per staff person containing information
    for all relevant Batches.

    Input:  batches - a list of Batch instances to process and generate
                        emails based on.
            email_template - the template of the email
            url_func - a callback function that will be used to generate
                        the links sent to staff to access information on 
                        bouncers and opt-outers.
    Output: True if successful, False otherwise
    Side Effect: One email will be sent to each staff person who entered
                 the information of a person who bounced or opted out.
    """

def personsToCsv(persons):
    """
    Converts a list of Person instances to a CSV, returning the CSV.

    Input:  persons - a list of Person instances.
    Output: a CSV.
    """
    csv_string = StringIO()
    dict_writer = csv.DictWriter(csv_string,
                                    ordered_person_attributes_for_upload)
    dict_writer.writer.writerow(ordered_person_attributes_for_upload)
    for person in persons:
        person = person.asDict()
        forums = person['forums']
        del person['forums']
        for forum in forums:
            person['group_id'] = forum
            dict_writer.writer.writerows(person)

    return csv_string


def getSuccessfulSignups(batch):
    """
    Searches the provided Batch instance and returns a list of Person 
    instances who have not bounced or opted out.  

    Input:  batch - a Batch instance or key to search through. 
    Output: an interable of Person instances who did not bounce or opt-out. 
    """
    batch = Batch.verifyOrGet(batch)
    for person in batch.persons.run():
        if not person.bounces.get() and not person.optouts.get():
            yield person

def emailCsvs(csvs, email_template=csvs_ready_template):
    """
    Sends an email to the provided address that includes the provided list
    of CSVs. 

    Input:  csvs - a list of CSVs to be sent.
            email_template - template used to generate the email body
            address - email address to send to
    Output: True if successful, False otherwise
    Side Effect: An email is sent to the provided address.
    """
    email_body = template.render(email_template, {})
    mail.send_mail(settings['email_as'],
                    settings['admin_email'],
                    'E-Democracy CSVs ready for Upload',
                    email_body,
                    attachments=csvs)
    return True
