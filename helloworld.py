import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib'))

import webapp2
import gdata.docs.service
from settings import gdocs_settings

class MainPage(webapp2.RequestHandler):
  def get(self):
      client = gdata.docs.service.DocsService()
      client.ClientLogin(gdocs_settings['username'], gdocs_settings['password'])
      documents_feed = client.GetDocumentListFeed()
      retval = ''
      for entry in documents_feed.entry:
        retval += entry.title.text + "\n"
      self.response.headers['Content-Type'] = 'text/plain'
      self.response.write(retval)

app = webapp2.WSGIApplication([('/', MainPage)],
                              debug=True)
