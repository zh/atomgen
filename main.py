import cgi
import wsgiref.handlers

import settings
from feed import *
from google.appengine.ext import webapp

class Index(webapp.RequestHandler):
  def get(self):
    context = {
        'debug': settings.DEBUG,
    }
    # calculate the template path
    path = os.path.join(os.path.dirname(__file__), 'templates', 'index.html')
    # render the template with the provided context
    output = template.render(path, context)
    self.response.out.write(output)

def main():
  application = webapp.WSGIApplication(
    [('/', Index),
     ('/feed/1min/(.*)$', OneMinFeed),   # the 1min feed need a secret token
     ('/feed/5min', FiveMinFeed), 
     ('/gen/1min', OneMinFeedGenerate),
     ('/gen/5min', FiveMinFeedGenerate),
     ('/entry/(\d)$', Entries)], debug = True)
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == "__main__":
  main()
