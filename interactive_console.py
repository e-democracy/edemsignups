from signupVerifier.io.gclient import *
from signupVerifier.processors.initial_processor import *
from signupVerifier.processors.optout_processor import *
gclient = GClient()
print "Getting Signups Folder"
signups_folder = gclient.docsClient.GetResourceById('0B_VUbsCmsj1jTERIX2ZWNDI4cHM')
print "Getting All Spreadsheets"
sss = gclient.spreadsheets(signups_folder)
print "Filtering out previous spreadsheets"
new_sss = gclient.filterOutOldSpreadsheets(sss)
for new_ss in new_sss:
    print spreadsheet_id(new_ss)
    meta_rows = gclient.getMetaListFeed(new_ss)
    meta_dict = gclient.metaRowToDict(meta_rows[0])
    print meta_dict
    person_list_feed = gclient.getRawListFeed(new_ss)     
    person_dicts = [gclient.personRowToDict(person_list_entry) for 
                            person_list_entry in person_list_feed if            
                            person_list_entry.get_value('email') is not None] 
    if 'prev_batch' in meta_dict:
        batch = addBatchChange(meta_dict, meta_dict['prev_batch'])   
        batchSpreadsheet = gclient.importBatchSpreadsheet(batch, new_ss)                        
        persons = []                                                    
        for person_dict in person_dicts:                                
            if 'person_id' in person_dict:      
                person_dict['source_batch'] = batch.key()             
                persons.append(addPersonChange(person_dict, person_dict['person_id']))
            else:
                persons.append(importPerson(person_dict, batch))
        print "Batch Change imported"
    else:
        batch = importBatch(meta_dict)
        batchSpreadsheet = gclient.importBatchSpreadsheet(batch, new_ss)
        persons = [importPerson(person_dict, batch) for person_dict in person_dicts]
        print "New Batch imported"
    print "Creating Tokens"
    for person in persons:
        token = createOptOutToken(batch, person)
    print "Sending Emails"
    sendVerificationEmails(batch)
