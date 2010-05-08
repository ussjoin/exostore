from google.appengine.ext import db
from google.appengine.ext import webapp

import hashlib

from url_normalize import url_normalize

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
            return "%s URL: %s Private: %s" % (self.key(), self.link, self.private)
        else:
            return "%s Keyname: %s URL: %s" % (self.key(), Feed.makekeyname(self.link), self.link)
    
    @staticmethod
    def makekeyname(url):
        return hashlib.sha224(url_normalize(url)).hexdigest()

class Item(db.Model):
    title = db.StringProperty(required=True)
    link = NormalizedLinkProperty(required=True)
    retrieved = db.DateTimeProperty(required=True)
    content = db.TextProperty(required=True)
    summary = db.StringProperty(required=True)
    version = db.IntegerProperty(required=True) # Numeric "schema" version starting from 1
    
    # Sometimes here depending on how it came in
    created = db.DateTimeProperty(required=False)
    feed = db.ReferenceProperty(reference_class=Feed, required=False) # Corresponds to Feed model
    private = db.UserProperty(required=False) # If set, is private to that user
    
    # here for some things
    geo = db.GeoPtProperty(required=False)

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
        
    