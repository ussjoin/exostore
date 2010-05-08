from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.api import urlfetch
from google.appengine.api.labs import taskqueue

import hashlib
from datetime import datetime

from url_normalize import url_normalize
import feedparser

class NormalizedLinkProperty(db.LinkProperty):
    def validate(self, value):
        value = db.LinkProperty().validate(value)
        value = url_normalize(value)
        return value

class Feed(db.Model):
    link = NormalizedLinkProperty(required=True)
    private = db.UserProperty(required=False) # If set, is private to that user
    
    def __str__(self):
        if (self.private):
            return "URL: %s Private: %s" % (self.link, self.private)
        else:
            return "URL: %s" % (self.link)
    
    @staticmethod
    def makekeyname(url):
        return hashlib.sha224(url_normalize(url)).hexdigest()

class Item(db.Model):
    title = db.StringProperty(required=True)
    link = NormalizedLinkProperty(required=True)
    retrieved = db.DateTimeProperty(required=True)
    content = db.TextProperty(required=True)
    summary = db.StringProperty(required=False)
    version = db.IntegerProperty(required=True) # Numeric "schema" version starting from 1
    
    # Sometimes here depending on how it came in
    created = db.DateTimeProperty(required=False)
    feed = db.ReferenceProperty(reference_class=Feed, required=False) # Corresponds to Feed model
    private = db.UserProperty(required=False) # If set, is private to that user
    
    # here for some things
    geo = db.GeoPtProperty(required=False)
    
    @staticmethod
    def makekeyname(url):
        return hashlib.sha224(url_normalize(url)).hexdigest()

class FeedHandler(webapp.RequestHandler):
    def post(self):
        '''Adds a feed.'''
        feedurl = self.request.body
        feed = Feed.get_or_insert(Feed.makekeyname(feedurl), link=feedurl)
        self.response.out.write(Feed.makekeyname(feedurl)+"\n")
    
    def delete(self):
        '''Removes a feed.'''
        feedurl = self.request.body
        query = Feed.gql("WHERE link = :1", url_normalize(feedurl))
        feed = query.fetch(1)
        db.delete(feed)
        self.response.out.write("Deleted\n")
    
    def get(self):
        '''Outputs a list of currently-known feeds.'''
        query=Feed.all()
        feeds = query.fetch(100)
        ret = "List:</br>"
        for f in feeds:
            ret += str(f)+"<br>"
            
        self.response.out.write(ret)
        
class FetchHandler(webapp.RequestHandler):
    def post(self):
        '''Fetches one feed.'''
        key = self.request.body
        feed = Feed.get(key)
        result = urlfetch.fetch(feed.link)
        parsed = feedparser.parse(result.content)
        for entry in parsed['entries']:
            item = Item.get_or_insert(Item.makekeyname(entry.link),
            title = entry.title,
            link = entry.link,
            retrieved = datetime.now(),
            content = entry.content[0].value,
            #summary = entry.summary,
            version = 1,
            created = datetime(*(entry.published_parsed[:6])),
            feed = feed,
            )
        self.response.out.write("%d\n" % len(parsed['entries']))
        
    def get(self):
        '''Schedules all feeds to be fetched.'''
        query = Feed.all()
        for feed in query:
            task = taskqueue.Task(payload=str(feed.key()), url="/fetch")
            task.add()