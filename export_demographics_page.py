import webapp2
from signupVerifier.settings import settings
from signupVerifier.models.models import Person
from signupVerifier.processors.unicode_csv import UnicodeDictWriter
from StringIO import StringIO


class ExportDemographicsPage(webapp2.RequestHandler):

    def get(self):
        self.handleRequest()

    def post(self):
        self.handleRequest()

    def handleRequest(self):
        csv_buffer = StringIO()
        columns = settings['demographics_column_order']
        columns.extend(['bounced', 'opted_out'])
        dict_writer = UnicodeDictWriter(csv_buffer,
                                        columns,
                                        extrasaction='ignore')
        dict_writer.writeheader()
        persons = Person.all()
        persons = [person for person in persons
                   if not person.next_changes.count()]
        for person in persons:
            person_dict = person.asDict()
            person_dict['bounced'] = bool(person.bounces.count())
            person_dict['opted_out'] = bool(person.optouts.count())
            if person.born_out_of_us is not None and not person.born_out_of_us:
                person_dict['born_out_of_us'] = 'False'
            if person.parents_born_out_of_us is not None and\
                    not person.parents_born_out_of_us:
                person_dict['parents_born_out_of_us'] = 'False'
            dict_writer.writerow(person_dict)

        csv_string = csv_buffer.getvalue()
        csv_buffer.close()
        self.response.headers['Content-Type'] = 'text/csv'
        self.response.write(csv_string)


routes = [webapp2.Route('/export_demographics.csv',
          handler=ExportDemographicsPage, name='optout')]
app = webapp2.WSGIApplication(routes=routes, debug=True)
