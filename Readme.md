# E-Democracy Signup Processing #

Provides a number of scrips that run on a Google App Engine instance and 
automate parts of the outreach sign up process.

## Tools ##

### Google Spreadsheets API ###

The [Google Spreadsheets API](https://developers.google.com/google-apps/spreadsheets/) 
provides access to read and write to the cells, rows, and sheets in a Google 
Spreadsheet. There is also a [Python library build on this API](http://code.google.com/p/gdata-python-client/).

The [live_cleint_test](https://code.google.com/p/gdata-python-client/source/browse/tests/gdata_tests/spreadsheets/live_client_test.py)
is a wonderful reference for how to do things with the Spreadsheets API.

### App Engine Bounce Handlers ###

App Engine includes a [framework for handling bounce notices](https://developers.google.com/appengine/docs/python/mail/bounce)
from emails sent via App Engine.

### Scheduled Tasks ###

App Engine provides [scheduled tasks]
(https://developers.google.com/appengine/docs/python/config/cron), which are 
basically cron jobs. They are executed by making an HTTP request to a web 
accessible script.

## Verification##

Using Google Apps Engine and Google Spreadsheets, much of the verification 
process can be automated. The goal is to have the following implemented and 
ready for testing by the end of March. During April, this script can be tested 
with signups that are currently waiting to be processed. 

### Emailing Script ###
A script that checks the Sign Up Spreadsheets folder at regular intervals 
(every X days). For any spreadsheets that it finds in the folder, it sends an 
email to every email address it finds in that spreadsheet notifying the person 
that they will be signed up for the forum indicated in the spreadsheet, and 
offer instructions on how to opt out if they wish to. After all of the 
addresses in a spreadsheet have been emailed, the script will email the 
Technology Coordinator and/or signups@e-democracy.og indicating how many 
emails were sent and when. 48 hours later, a follow up script will notify the 
Technology Coordinator that a sheet of users is ready to upload and provide 
instructions on what to do.

### Bounce Handling ###

When a bounce is detected, the handler will move the corresponding record in 
the spreadsheet to a bouncers sheet, and indicate when the bounce occurred. 48 
hours after the Emailing Script is run, a followup script will check any 
spreadsheets found in the Sign Up Spreadsheets folder for bouncers, create a 
new spreadsheet based on the sheet of bouncers from the original spreadsheet, 
named <original spreadsheet name>-Retries, that retains the date/time of the 
original bounce. The follow up script will email the appropriate people to 
indicate that some addresses bounced, along with instructions on how to correct
the bounced email addresses. At some future point, the Emailing Script will run
again, and treat the Retries spreadsheet as it would any other spreadsheet it 
encounters (one idea is to also to have a cell in the Retries spreadsheet that 
indicates if the spreadsheet is ready to be processed). However, any bounces 
detected due to emails sent from the Retries spreadsheet will be regarded as a 
permanent failure.

### Opt Out Handling ###

When the Emailing script is run, it will generate and insert a link into 
each email that allows the recipient to click it to opt out of being included 
in the group. If a user clicks that link, the corresponding record in the 
spreadsheet will be moved to an opt-outs sheet. 48 hours after the Email 
Script is run, a followup script will check any spreadsheets found in the Sign 
Up Spreadsheets folder for Opt-Outs, and email the Technology Coordinator to 
indicate that some addresses opted-out.

In addition, the reply-to of the email sent by the Emailing Script will be 
signups@e-democracy.org. The email sent to the Technology Coordinator by the 
follow up script will remind him to check signups@e-democracy.org for any 
message that people sent in reply to the initial email, including people who 
indicate via email that they want to opt out.


