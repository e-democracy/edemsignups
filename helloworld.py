import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib'))

import webapp2
from gdata.docs.client import DocsClient, DocsQuery
from gdata.spreadsheets.client import SpreadsheetsClient
from gdata.spreadsheets.data import SpreadsheetsFeed
import gdata.spreadsheet
from settings import gdocs_settings

class MainPage(webapp2.RequestHandler):
  def get(self):

      # This is a bit confusing, because the Spreadsheets Client does not 
      # directly support searching for a folder. So, a Docs Client is first
      # used to search for the folder we want to retreive spreadsheets from.
      dclient = DocsClient()
      query = DocsQuery(
        title='Sign Up Spreadsheets (Data)',
        title_exact='true',
        show_collections='true')

      # For now, being lazy and using username/password. The token returned by 
      # one type of client can be used by other types. In fact, it has to, as
      # future calls to ClientLogin will result in unusable tokens.
      #
      # Eventually, we should use Oauth.
      token = dclient.ClientLogin(gdocs_settings['username'], 
                    gdocs_settings['password'], gdocs_settings['app_name'])
      folder = dclient.GetResources(q=query).entry[0]

      # Now that we have the folder, its time to get the spreadsheets...
      sclient = SpreadsheetsClient()
      # Unfortunately, we can't just use the get_spreadsheets method, because 
      # we need to provide the URI of the specific folder we want to get 
      # spreadsheets from. A get_spreadsheets_from_folder function would be a
      # nice addition.
      spreadsheets = sclient.get_feed(uri=folder.content.src, 
                    desired_class=SpreadsheetsFeed, auth_token=token)

      retval = 'Your Spreadsheets:\n'
      #for entry in spreadsheets.entry:
        #retval += "%s\n" % entry.category
      for i, entry in enumerate(spreadsheets.entry):
          if isinstance(spreadsheets, gdata.spreadsheet.SpreadsheetsCellsFeed):
              print '%s %s\n' % (entry.title.text, entry.content.text)
          elif isinstance(spreadsheets, gdata.spreadsheet.SpreadsheetsListFeed):
              print '%s %s %s' % (i, entry.title.text, entry.content.text)
              # Print this row's value for each column (the custom dictionary is
              # built using the gsx: elements in the entry.)
              print 'Contents:'
              for key in entry.custom:  
                  print '  %s: %s' % (key, entry.custom[key].text)
              print '\n',
          else:
              print '%s %s\n' % (i, entry.title.text)

      self.response.headers['Content-Type'] = 'text/plain'
      self.response.write(retval)

app = webapp2.WSGIApplication([('/', MainPage)],
                              debug=True)
