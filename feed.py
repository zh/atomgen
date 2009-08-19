import hmac, os, re, logging, datetime
from datetime import timedelta
from time import mktime

from google.appengine.api import memcache
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

import settings
import feedgen

logging.getLogger().setLevel(logging.DEBUG)

class OneMinFeed(webapp.RequestHandler):
  def get(self, secret):
    if not secret or secret != settings.SECRET_TOKEN:
      self.error(400)
      return self.response.out.write('400 Invalid Request')

    f1m = memcache.get("feed1min")
    if f1m is None:
      self.error(404)
      return self.response.out.write('404 Not Found')

    entry = f1m.items[0]['title']
    lastmod = datetime.datetime.strptime(entry, "%Y-%m-%dT%H:%M:%SZ")
    if self.request.headers.has_key('If-Modified-Since'):
      dt = self.request.headers.get('If-Modified-Since').split(';')[0]
      modsince = datetime.datetime.strptime(dt, "%a, %d %b %Y %H:%M:%S %Z")
      if modsince >= lastmod:
        self.error(304)
        return self.response.out.write("304 Not Modified")

    now = datetime.datetime.now()
    self.response.headers['Last-Modified'] = now.strftime("%a, %d %b %Y %H:%M:%S GMT")
    # The feed will be changed after 1 minute, so do not cache it
    expires=now + datetime.timedelta(minutes=2)
    self.response.headers['Expires'] = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")

    # Etag will contain the current time
    signature = hmac.new(settings.SECRET_TOKEN, entry).hexdigest()
    self.response.headers['Etag'] = '%s:%s' % (entry, signature)
    self.response.headers['Content-Type'] = 'application/atom+xml'
    return self.response.out.write(f1m.writeString('UTF-8'))


class FiveMinFeed(webapp.RequestHandler):
  def get(self):
    f5m = memcache.get("feed5min")
    if f5m is None:
      self.error(404)
      return self.response.out.write('404 Not Found')

    entry = f5m.items[0]['title']
    lastmod = datetime.datetime.strptime(entry, "%Y-%m-%dT%H:%M:%SZ")
    if self.request.headers.has_key('If-Modified-Since'):
      dt = self.request.headers.get('If-Modified-Since').split(';')[0]
      modsince = datetime.datetime.strptime(dt, "%a, %d %b %Y %H:%M:%S %Z")
      if modsince >= lastmod:
        self.error(304)
        return self.response.out.write("304 Not Modified")

    now = datetime.datetime.now()
    self.response.headers['Last-Modified'] = now.strftime("%a, %d %b %Y %H:%M:%S GMT")
    # The feed will be changed after 5 minute, so do not cache it
    expires=now + datetime.timedelta(minutes=10)
    self.response.headers['Expires'] = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")

    signature = hmac.new(settings.SECRET_TOKEN, entry).hexdigest()
    self.response.headers['Etag'] = '%s:%s' % (entry, signature)
    self.response.headers['Content-Type'] = 'application/atom+xml'
    return self.response.out.write(f5m.writeString('UTF-8'))


class OneMinFeedGenerate(webapp.RequestHandler):
  def get(self):
    feed_url = settings.SITE_URL + u"/feed/1min"
    f1m = feedgen.Atom1Feed(
        title = u"1min atom entries generator",
        author_name = u"Atom Generator",
        link = feed_url,
        feed_url = feed_url,
        hub_url = settings.HUB_URL,
        description = u"Generate new entry every minute.",
        language = u"en")

    now = datetime.datetime.now()
    for e in range(0, settings.NUM_ENTRIES):
        past = timedelta(minutes=e)
        ts = (now - past).strftime("%Y-%m-%dT%H:%M:%SZ")
        f1m.add_item(title = ts,
                     link = settings.SITE_URL + u"/entry/" + str(e),
                     pubdate = (now-past),
                     description = ts)
    if not memcache.add("feed1min", f1m, 120):
      logging.error("Memcache for 1min set failed.")
    return self.response.out.write(f1m.writeString('UTF-8'))


class FiveMinFeedGenerate(webapp.RequestHandler):
  def get(self):
    feed_url = settings.SITE_URL + u"/feed/5min"
    f5m = feedgen.Atom1Feed(
        title = u"5min atom entries generator",
        author_name = u"Atom Generator",
        link = feed_url,
        feed_url = feed_url,
        hub_url = settings.HUB_URL,
        description = u"Generate new entry every 5 minutes.",
        language = u"en")

    now = datetime.datetime.now()
    for e in range(0, settings.NUM_ENTRIES):
        past = timedelta(minutes=(5*e))
        ts = (now - past).strftime("%Y-%m-%dT%H:%M:%SZ")
        f5m.add_item(title = ts,
                     pubdate = (now-past),
                     link = settings.SITE_URL + u"/entry/" + str(e),
                     description = ts)
    if not memcache.add("feed5min", f5m, 600):
      logging.error("Memcache for 5min set failed.")
    return self.response.out.write(f5m.writeString('UTF-8'))


class Entries(webapp.RequestHandler):
  def get(self, enum):
    if enum == u"0":
      return self.response.out.write(u"now")
    if enum == u"1":
      return self.response.out.write(u"1 minute ago")
    return self.response.out.write(enum + u" minutes ago")
