import hmac, os, re, logging, datetime, urllib
from datetime import timedelta
from time import mktime

from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

import settings
import feedgen

logging.getLogger().setLevel(logging.DEBUG)

# Set the proper headers and return 'application/atom+xml' response or error
# interval can be 1 (1 minutes feed) or 5 (5 minutes feed)
# the one minute feed is protected by a secret
class Feed(webapp.RequestHandler):
  def get(self, interval, secret=None):
    # 1min and 5min feeds
    if interval == u"1":
      if not secret or secret != u"/" + settings.SECRET_TOKEN:
        self.error(400)
        return self.response.out.write('400 Invalid Request')
    # everything else will produce 5min feed
    else:
      interval = u"5"

    feed = memcache.get(u"AtomFeed" + interval)
    if feed is None:
      self.error(404)
      return self.response.out.write('404 Not Found')

    lastmod = feed.latest_post_date()
    if self.request.headers.has_key('If-Modified-Since'):
      dt = self.request.headers.get('If-Modified-Since').split(';')[0]
      modsince = datetime.datetime.strptime(dt, "%a, %d %b %Y %H:%M:%S %Z")
      # feed.latest_post_date() returning a float number of milliseconds! small correction
      if (modsince + datetime.timedelta(seconds=1)) >= lastmod:
        self.error(304)
        return self.response.out.write("304 Not Modified")
  
    self.response.headers['Last-Modified'] = lastmod.strftime("%a, %d %b %Y %H:%M:%S GMT")
    # The feed will be changed after 1 or 5 minutes, so do not cache it
    expires=lastmod + datetime.timedelta(minutes=2*int(interval))
    self.response.headers['Expires'] = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")

    # Etag will contain the ID of the last entry
    marker = memcache.get(u"myIter" + interval)
    if marker == None:
      memcache.set(u"myIter" + interval, "0")
      marker = 0
    marker = int(marker) + int(settings.NUM_ENTRIES)  
    signature = hmac.new(settings.SECRET_TOKEN, str(marker)).hexdigest()
    self.response.headers['Etag'] = '%s:%s' % (str(marker), signature)

    self.response.headers['Content-Type'] = 'application/atom+xml'
    return self.response.out.write(feed.writeString('UTF-8'))


# Feeds generation. Cronjob-driven (cron.yaml), available only for the admins (app.yaml)
class FeedGenerate(webapp.RequestHandler):
  def get(self, interval):
    feed_url = settings.SITE_URL + u"/feed/" + interval
    feed = feedgen.Atom1Feed(
        title = interval + u" min atom entries generator",
        author_name = u"Atom Generator",
        link = settings.SITE_URL + u"/",
        feed_url = feed_url,
        hub_url = settings.HUB_URL,
        description = u"Generate new entry every " + interval + " minutes.",
        language = u"en")

    now = datetime.datetime.now()

    marker = memcache.incr(u"myIter" + interval)
    if marker == None:
      memcache.set(u"myIter" + interval, "0")
      marker = 0

    for e in range(0, settings.NUM_ENTRIES):
        past = timedelta(minutes=(int(interval)*e))
        ts = (now - past).strftime("%Y-%m-%dT%H:%M:%SZ")
        index = int(marker) + settings.NUM_ENTRIES - e
        feed.add_item(title = u"entry " + str(index) + u" from " + ts,
                      link = settings.SITE_URL + u"/entry/" + str(index),
                      pubdate = (now-past),
                      description = ts)
        
    memcache.set(u"AtomFeed" + interval, feed)

    # for the 5 min feed, ping the PSHB hub, if exists
    if interval == u"5" and settings.HUB_URL is not None:
      form_fields = { u"hub.mode": u"publish",  u"hub.url": feed_url }
      response = urlfetch.fetch(url = settings.HUB_URL,
                                payload = urllib.urlencode(form_fields),
                                method = urlfetch.POST,
                                headers = {'Content-Type': 'application/x-www-form-urlencoded'})

    return self.response.out.write(feed.writeString('UTF-8'))
