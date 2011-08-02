#### MEMORY-BASED SHALLOW PARSER ######################################################################

# Copyright (c) 2003-2010 University of Antwerp, Belgium and Tilburg University, The Netherlands
# Vincent Van Asch <vincent.vanasch@ua.ac.be>, Tom De Smedt <tom@organisms.be>
# License: GNU General Public License, see LICENSE.txt

### INSTANCES ########################################################################################
# Lookup instances for PP TiMBL client.
# These are command strings sent to the TiMBL server, created in classify.py.

from math import pow, log
try: 
    from MBSP import config
except ImportError:
    # We will end up here if mbsp.py is called directly from the command line.
    import config

#--- INSTANCE ----------------------------------------------------------------------------------------

class InstanceError(Exception): 
    pass

class Instance(unicode):
    """ TiMBL lookup instance represented as a unicode string,
        enhanced with anchor, pp, tag and type attributes.
        For the sentence: "I eat pizza with a fork." the instances will look something like:
        - 0 0 3 - i PRP pizza NN with fork NN 0 0
        - 0 0 2 - eat VBP pizza NN with fork NN 0 0
        - 0 0 1 - pizza NN pizza NN with fork NN 0 0
    """
    
    def __new__(cls, instance, anchor_index, pp_index, type):
        if not isinstance(instance, unicode):
            raise TypeError('instance must be unicode string')
        return unicode.__new__(cls, instance.strip())
        
    def __init__(self, instance, anchor, pp, type):
        if not isinstance(anchor, int):
            raise TypeError('anchor index must be an integer')
        if not isinstance(pp, int):
            raise TypeError('PP index must be an integer')
        if not isinstance(type, (str, unicode)):
            raise TypeError('type must be a string')
        self.anchor = anchor # The index in the sentence where the anchor of this instance is located.
        self.pp = pp         # The index in the sentence where the PP of this instance is located.
        self.type = type     # The type of the instance, i.e. the type of the anchor, NP/VP/PP.
        self.tag = None
        
    def __add__(self, other):
        if isinstance(other, unicode):
            return self.__class__(unicode(self)+' '+other.strip(), self.anchor, self.pp, self.type)
        else:
            raise TypeError('can only add a unicode string to the instance')

#--- TAGGED INSTANCE STRING --------------------------------------------------------------------------

class TaggedInstance(object):
    """ A tagged instance with format:
        0 0 24 finding NN of asbestos NN 5 2 NP { 0 1431.83 }        0.0041727069604562
        where the length of the instance can be different. 
    """
    
    def __init__(self, instance, predicted, distance, distribution):
        self.instance = instance       # An Instance object.
        self.distance = distance       # A float.
        self._predicted = [predicted]  # 0 or 1
        self.distribution = {0:0, 1:0} # A dictionary with at most a key 0 and a key 1.
        self.distribution.update(distribution.copy())
    
    @property
    def predicted(self):
        return self._predicted[-1]

    def change_prediction(self, new_predicted_class):
        # Changes the predicted class to the new predicted class.
        #if new_predicted_class not in [0,1]:
        #    raise ValueError('new_predicted_class should be 0 or 1')
        self._predicted.append(new_predicted_class)

    @property
    def entropy(self):
        """ Returns the entropy as: -1 * p(0) * log(p(0), 2) - p(1) * log(p(1), 2)
            where p(x) is self.distribution[x] / sum(self.distribution.values())
            If one of the p is zero it is substituted by math.pow(2, -100).
        """
        def _safe(t,n):
            if not t: return 0.0
            return t/n
        n = sum(self.distribution.values())
        p = [_safe(i,n) for i in self.distribution.values()]
        for i, chance in enumerate(p):
            if not chance:
                p[i] = pow(2, -100)
        return sum([-1 * p[i] * log(p[i], 2) for i in range(len(p))])

    def format(self):
        """ Returns a unicode string formatted as in the original TiMBL file.
        """
        a, b = self.distribution[1], self.distribution[0]
        if a and b: 
            d = '{ 0 %.5f,  1 %.5f }' % (b, a)
        elif a: 
            d = '{ 1 %.5f }' % a
        elif b: 
            d = '{ 0 %.5f }' % b
        else:
            d = '{ 0 0.0,  1 0.0 }'
        s = u'%s %s %s      %f' % (self.instance, str(self.predicted), d, self.distance)
        return s.encode(config.encoding)
        
    def __str__(self):
        return self.format()
        
    def change_prediction(self, new_predicted_class):
        # Changes the predicted class to the new predicted class.
        self._predicted.append(new_predicted_class)

#--- SCOREABLE TAGGED INSTANCE -----------------------------------------------------------------------

def distribution(values):
    """ Takes a list like ['0','45.56','1','454.65'] and returns a dictionary { 0: 45.56, 1: 454.65 }
        If one class isn't present the value of that class will be 0.0
    """
    def _strip(string):
        # Returns the string but without a trailing comma is present.
        try:
            return string[:string.index(',')]
        except:
            return string
    d = {0:0.0, 1:0.0}
    for i in range(0, len(values), 2):
        d[int(values[i])] = float(_strip(values[i+1]))
    return d

class ScoreableTaggedInstance(TaggedInstance):
    """ A tagged instance with format:
        0 0 24 finding NN of asbestos NN 5 2 0 0 { 0 1431.83 }        0.0041727069604562
        where the length of the instance can be different. 
    """
    
    def __init__(self, instance):
        # instance: unicode string of correct format.
        if not isinstance(instance, unicode):
            raise TypeError('instance must be unicode')
        p = instance.strip().split()
        try: i = p.index('{')
        except ValueError:
            raise ValueError('instance must contain distribution and distance information')
        TaggedInstance.__init__(self, 
                instance = ' '.join(p[:i-2]),
               predicted = [int(p[i-1])],
                distance = float(p[-1]),
            distribution = distribution(p[i+1:p.index('}')])
        )
        self.given = int(p[leftcurl-2]) # The given class.
            