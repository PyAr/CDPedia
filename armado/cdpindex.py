# -*- coding: utf8 -*-

"""
Biblioteca para armar y leer los índices.

Se usa desde server.py
"""

from __future__ import division

import shelve

def getsubstrings(source, minim=3):
    for size in range(minim, len(source)+1):
        for pos in range(0, len(source)-size+1):
            yield source[pos:pos+size]

class Index:
    todisk = 1
    def __init__(self, filename):
        self.filename = filename
        if self.todisk:
            self.opendisk()
        else:
            self.word_shelf = {}
            self.id_shelf = {}
        
    def search(self, keywords):
        print "keywords", keywords
        result = None
        for word in keywords.lower().split(" "):
            if word in self.word_shelf:
                print "adding results from", word
                if result is None:
                    result = self.word_shelf[word]
                else:
                    result.intersection_update( self.word_shelf[word] )
            else:
                print "word", word, "not in database"
                pass            
        if result is None: return []
        return [ self.id_shelf[str(x)] for x in result ]
        
    def index(self, item, description):
        iid = hash(item)
        self.id_shelf[ str(iid) ] = item,description
        parts = description.split(":")
        result = []
        for p in parts:
            result += p.split(" ")
            
        result = [ w.lower() for w in result ]
        result = set(result)
        words = set(result)
        for w in result:
            res = list(getsubstrings(w))
            words.update(res)
            
        for word in words:
            s = self.word_shelf.get(word, set())
            s.add( iid )
            self.word_shelf[word]=s

    def flush(self):
        if self.todisk:
            self.word_shelf.sync()
            self.id_shelf.sync()
            
    def opendisk(self):
        filename = self.filename
        #print "Opening", filename
        self.word_shelf = shelve.open(filename,  writeback=True)
        #print "Opening", filename+"_ids"
        self.id_shelf = shelve.open(filename+"_ids" , writeback=True)

    def save(self):
        if self.todisk:
            self.flush()
        else:
            wshelf = self.word_shelf
            ishelf = self.id_shelf
            self.opendisk()
            print "Updating word shelf"
            self.word_shelf.update(wshelf)
            print "Updating id shelf"
            self.id_shelf.update(ishelf)
            print "Syncing"
            self.flush()
            print 'Done'
