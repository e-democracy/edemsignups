# coding=utf-8

class InitialProcessor(object):

    def importBatch(batch):
        """
        Imports the provided batch into the database, and returns the created
        Batch model.
        
        Input: batch - a dict representing the batch to save to the database.
        Output: a Batch model created by the import.
        Side Effect: an entry is saved to the database for the batch.
        Throws:
        """
        pass
    
    def addBatchChange(batch, prev_bid):
        """
        Imports a change to a previously existing Batch, and returns the
        created Batch model. Values associated with the previous Batch will be
        used in the created Batch, unless a value is specified in the batch
        dict.

        Input:  batch - a dict representing the batch to save to the database.
                prev_bid - the ID of the previous instance of the provided
                            batch.
        Output: a Batch model created by the addition of the new batch.
        Side Effect: an entry is saved to the database for the batch, and an
                     association between the new batch and its previous 
                     instance is saved.
        """
        pass

    
    def importPerson(person, bid):
        """
        Imports the provided single person, associated with the indicated
        batch, into the databse, and returns the created Person model.

        Input:  person - a dict representing the person to save to the
                         database.
                bid - the ID of the Batch model that this person is associated
                      with.
        Output: a Person model craeted by the import.
        Side Effect: an entry is saved to the database for the person.
        """
        pass

    def addPersonChange(person, prev_pid):
        """
        Imports a change to a previously existing Person, and returns the
        created Person model. Values of the previous instance of the Person 
        will be used in the new instance of the Person, unless a value is 
        specified in the person dict.

        Input:  person - a dict representing the person to save to the database.
                prev_pid - the ID of the previous instance of the provided
                            person.
        Output: a Person model created by the addition of the new person.
        Side Effect: an entry is saved to the database for the person, and an
                     association between the new person and its previous 
                     instance is saved.
        """
        pass

    def importPersons(persons, bid):
        """
        Imports the provided persons, associated with the indicated batch, into
        the database, and returns a list of Person models.
        
        Input:  persons - a List of dicts representing persons to save to the
                            database.
                bid - the ID of the Batch model that these persons are to be
                associated with.
        Output: a List of Person models created by the import.
        Side Effect: Entries are saved to the database for each person
                        contained in the persons list.
        Throws:
        """
        pass

    def sendVerificationEmails(batch):
        """ 
        Generates an email based on the metadata of the provided batch, each 
        person in the batch, and each person's opt-out token. Then sends the 
        verification email to each person in the batch.

        Input: batch - a Batch model
        Output: True if verification emails are sent successfully, false
                otherwise.
        Side Effect: Emails are sent to all Person associated with the Batch
                        model.
        """
        pass
