# E-Democracy Signup Processing #

Provides a number of scrips that run on a Google App Engine instance and 
automate parts of the outreach sign up process.

## Scheduled Tasks ##

App Engine provides [scheduled tasks]
(https://developers.google.com/appengine/docs/python/config/cron), which are 
basically cron jobs. They are executed by making an HTTP request to a web 
accessible script.
