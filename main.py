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


class Entries(webapp.RequestHandler):
  def get(self, enum):
    return self.response.out.write(u"entry" + enum)


def main():
  application = webapp.WSGIApplication(
    [('/', Index),
     ('/feed/(1|5)(.*)$', Feed),   # the 1min feed need a secret token
     ('/gen/(1|5)$', FeedGenerate),
     ('/entry/(\d+)$', Entries)], debug = True)
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == "__main__":
  main()
