from signupVerifier.io.gclient import *
from signupVerifier.processors.initial_processor import *
gclient = GClient()
print "Getting Signups Folder"
signups_folder = gclient.docsClient.GetResourceById('0B9kNsX36XQLDSUhmNU54djR6S00')
print "Getting All Spreadsheets"
sss = gclient.spreadsheets(signups_folder)
print "Filtering out previous spreadsheets"
new_sss = gclient.filterOutOldSpreadsheets(sss)
for new_ss in new_sss:
    print spreadsheet_id(new_ss)
    meta_rows = gclient.getMetaListFeed(new_ss)
    meta_dict = gclient.metaRowToDict(meta_rows[0])
    batch_model = importBatch(meta_dict)
    print "New Batch imported"
    person_rows = gclient.getRawListFeed(new_ss)
    for row in person_rows:
        if row.get_value('email') is not None:
            person_dict = gclient.personRowToDict(row)
            person_model = importPerson(person_dict, batch_model)
