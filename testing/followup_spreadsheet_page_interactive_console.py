from google.appengine.ext.webapp import template                                
from google.appengine.api import mail 
from signupVerifier.io.gclient import *
from signupVerifier.processors.final_processor import *
from signupVerifier.processors.optout_processor import *
import datetime as dt
import pprint
followup_template = 'templates/followup_template.html' 
pp = pprint.PrettyPrinter(indent=4)
gclient = GClient()

def new_followup_struct():
    return {'optouts': [],
            'bounces': []}
staff_followups = dict()
successes = []
print "Getting Batches from Recent BatchSpreadsheets"
bss = gclient.getBatchSpreadsheets(before=dt.datetime.now())
print bss
batches = [bs.batch for bs in bss]
print batches
for batch in batches:
    removeAllOptOutTokensFromBatches([batch])
    optouts = batch.optouts.run()
    bounces = batch.optouts.run()
    print "optouts: %s" % optouts
    print "bounces: %s" % bounces
    if optouts:
        ooss, oows = gclient.createOptOutSpreadsheet(batch)
        if not batch.staff_email in staff_followups:
            staff_followups[batch.staff_email] = new_followup_struct()
        staff_followups[batch.staff_email]['optouts'].append((batch, ooss))
    if bounces:
        bss, brws = gclient.createBouncedSpreadsheet(batch)       
        if not batch.staff_email in staff_followups:                    
            staff_followups[batch.staff_email] = new_followup_struct()  
        staff_followups[batch.staff_email]['bounces'].append((batch,bss))
    successful_signups = getSuccessfulSignups(batch)                    
    successes.append((batch, successful_signups))
pp.pprint(staff_followups)
for email,followup in staff_followups.iteritems():                       
    if followup['optouts'] or followup['bounces']:                      
        email_body = template.render(followup_template, followup)       
        mail.send_mail(settings['email_as'], email,                     
                                'Submitted Signups Followup', email_body)
pp.pprint(successes)
csvs = [("% - %.csv" % (batch.event_name, batch.staff_name),            
                    personsToCsv(successful_signups))                           
                    for batch, successful_signups in successes]                 
#   10.) Email Uploader (FinalProcessor)
emailCsvs(csvs)
