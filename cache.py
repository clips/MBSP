#### MEMORY-BASED SHALLOW PARSER ######################################################################

# Copyright (c) 2003-2010 University of Antwerp, Belgium and Tilburg University, The Netherlands
# Vincent Van Asch <vincent.vanasch@ua.ac.be>, Tom De Smedt <tom@organisms.be>
# License: GNU General Public License, see LICENSE.txt

### CACHE ############################################################################################
# Implements an ordered dictionary with (optionally) hashed keys.
# It is used in three ways:
# - For the MBSP.parse() command, cache the given string and its tagged output for reuse.
# - For MBSP.prepositions.pp_attachments(), cached the tagged string and its anchor tuples for reuse.
# - Keep a log of all the lookup instances sent to TiMBL and MBT server, and their response.
# This way, when we are testing with an example sentence, 
# we don't need to parse it every time but we can reuse the tagged output from cache (see mbsp.py).
# The lookup instances are available in server logs for inspection (see clients.Timbl).

try:
    # If Python 2.6+ is used we can import hashlib, otherwise we revert to md5.
    import hashlib; encrypt = hashlib.md5
except:
    import md5; encrypt = md5.new

#--- ORDERED DICTIONARY ------------------------------------------------------------------------------
# If we log server requests in a list, it takes more time to retrieve them (using the log as a cache).
# If we log server requests in a dictionary, we lose the order in which they occured.
# The ordered dictionary solves this, but it requires more memory overhead (keys are stored twice).

class odict(dict):
    """ A dictionary with ordered keys.
        With reversed=True, the latest keys will be returned first when traversing the dictionary.
    """
    def __init__(self, d=None, reversed=True):
        dict.__init__(self)
        self._o = [] # The ordered keys.
        self._f = reversed and self._insertkey or self._appendkey
        if d != None: self.update(dict(d))
    @property
    def reversed(self):
        return self._f == self._insertkey
    @classmethod
    def fromkeys(odict, k, v=None, reversed=True):
        d = odict(reversed=reversed)
        for k in k: d.__setitem__(k,v)
        return d
    def _insertkey(self, k):
        if k not in self: self._o.insert(0,k) # Sort newest-first with reversed=True.
    def _appendkey(self, k):
        if k not in self: self._o.append(k)   # Sort oldest-first with reversed=False.
    def append(self, (k, v)):
        """ Takes a (key, value)-tuple. Sets the given key to the given value.
            If the key exists, pushes the updated item to the head (or tail) of the dict.
        """
        if k in self: self.__delitem__(k)
        self.__setitem__(k,v)
    def update(self, d):
        for k,v in d.items(): self.__setitem__(k,v)
    def setdefault(self, k, v=None):
        if not k in self: self.__setitem__(k,v)
        return self[k]        
    def __setitem__(self, k, v): 
        self._f(k); dict.__setitem__(self, k, v)
    def __delitem__(self, k):
        dict.__delitem__(self, k); self._o.remove(k)
    def pop(self, k):
        self._o.remove(k); return dict.pop(self, k)
    def clear(self):
        dict.clear(self); self._o=[]
    def keys(self): 
        return self._o
    def values(self):
        return map(self.get, self._o)
    def items(self): 
        return zip(self._o, self.values())
    def __iter__(self):
        return self._o.__iter__()
    def copy(self):
        d = self.__class__(reversed=self.reversed)
        for k,v in (self.reversed and reversed(self.items()) or self.items()): d[k] = v
        return d
    def __repr__(self):
        return "{%s}" % ", ".join(["%s: %s" % (repr(k), repr(v)) for k, v in self.items()])

#--- CACHE -------------------------------------------------------------------------------------------

class Cache(odict):

    def __init__(self, d=None, size=100, hashed=False, reversed=False): 
        """ An ordered dictionary with a size limit and (optionally) hashed keys.
            Hashed keys have the advantage of being relatively small in size.
            They can be used when the original keys are long strings, for example.
        """
        self.size = size
        self._hashed = hashed
        odict.__init__(self, d, reversed)
    
    @property
    def hashed(self):
        return self._hashed
    
    def _hash(self, k):
        if not self._hashed: return k
        if not isinstance(k, basestring): k = str(k)
        if isinstance(k, unicode): k = k.encode("utf-8") # MD5 works on Python byte strings.
        return encrypt(k).hexdigest()

    def __setitem__(self, k, v):
        odict.__setitem__(self, self._hash(k), v)
        if len(self) > self.size:
            # If the cache exceeds the maximum size, remove the oldest entry.
            odict.__delitem__(self, self.keys()[self.reversed and -1 or 0])
            
    def __getitem__(self, k):
        try: return odict.__getitem__(self, self._hash(k))
        except KeyError:
            raise KeyError, k

    def __delitem__(self, k):
        try: odict.__delitem__(self, self._hash(k))
        except KeyError:
            raise KeyError, k

    def __contains__(self, k):
        return odict.__contains__(self, self._hash(k))
        
    def copy(self):
        d = self.__class__(size=self.size, hashed=self._hashed, reversed=self.reversed)
        for k,v in (self.reversed and reversed(self.items()) or self.items()): d[k] = v
        return d

#--- LOG ---------------------------------------------------------------------------------------------

class Log(dict):
    """ A collection of Cache objects with a name.
        This is used with TiMBL and MBT clients to create a separate log for each type of server.
    """
    
    def create(self, name, *args, **kwargs):
        self[name] = Cache(*args, **kwargs)
        
    def copy(self):
        return Log([(k,v.copy()) for k,v in self.items()])

