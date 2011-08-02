#### MEMORY-BASED SHALLOW PARSER ######################################################################

# Copyright (c) 2003-2010 University of Antwerp, Belgium and Tilburg University, The Netherlands
# Vincent Van Asch <vincent.vanasch@ua.ac.be>, Tom De Smedt <tom@organisms.be>
# License: GNU General Public License, see LICENSE.txt

#### CLASSIFY ########################################################################################
# Module for appending PP's using just one classifier.
# For a given sentence tagged with part-of-speech, chunk, preposition tags (and preferably lemmata), 
# constructs a Sentence tree and derives TiMBL lookup instances from it.
# These instances will then decide how prepositions are "attached" (related) to other chunks.
# This includes sending them to TiMBL, revoting the output if there are multiple candidates,
# and applying a set of rules to correct certain limitations.

import re, socket
import instance
import voting
import rules

try:
    from MBSP import config
    from MBSP.config import WORD, POS, CHUNK, PNP, REL, ANCHOR, LEMMA
    from MBSP.client import batch, TimblPP
    from MBSP.tree   import Sentence
except ImportError:
    # We will end up here if mbsp.py is called directly from the command line
    import config
    from config import WORD, POS, CHUNK, PNP, REL, ANCHOR, LEMMA
    from client import batch, TimblPP
    from tree   import Sentence

try:
    HOST = config.hosts[config.servers.index('preposition')] # Preposition server host (e.g. localhost).
    PORT = config.ports[config.servers.index('preposition')] # Preposition server port.
except:
    HOST = ''
    PORT = 0

#--- PP INSTANCE -------------------------------------------------------------------------------------

def _count_NP(sentence, i, j):
    """ Returns the number of NP chunks between word i and j. 
        Chunks inside PNP are not counted.
    """
    i, j = min(i,j), max(i,j)
    n = len(filter(lambda ch: ch.start>i and ch.stop<=j and ch.type=='NP' and not ch.pnp, sentence.chunk))
    return n
    
def _count_PNP(sentence, i, j):
    """ Returns the number of PNP chunks between word i and j.
    """
    i, j = min(i,j), max(i,j)
    n = len(filter(lambda ch: ch.start>i and ch.stop<=j, sentence.pnp))
    return n

def _count_punctuation(sentence, i, j, selection=[]):
    """ Returns a (selected, other, sum)-tuple,
        where sum is the number of punctuation marks between word i and j.
        The selection is a list of punctuation marks (e.g. '.') for which you need a separate count.
    """
    a = b = 0
    for word in sentence.words[i+1:j]:
        if word.string in selection:
            a += 1
        elif re.match('\W+$', word.string, re.U):
            b += 1
    return (a, b, a+b)

def _PP_instance(s, pnp, chunk, pp=None):
    """ Create an Instance object with a lookup string for the PP-attacher TiMBL server.
        If the chunk is a NP inside a PNP, you must supply the PP preceding it.
    """
    lemma = lambda i: s.lemmata[i] or s.words[i]      # Prefer lemmata, use words if unavailable.
    p0 = pp and lemma(pp.start) or '-'                # The PP as lemma, if given, '-' otherwise.
    p1 = lemma((pp or chunk).head.index)              # The head of the chunk as lemma.
    p2 = s.pos[(pp or chunk).head.index]              # The head of the chunk as part-of-speech tag.
    p3 = pnp.start != 0 and lemma(pnp.start-1) or '-' # The lemma of the word before the PP.
    p4 = pnp.start != 0 and s.pos[pnp.start-1] or '-' # The part-of-speech tag of the word before the PP. 
    p5 = lemma(pnp.start)                             # The preposition word of the PNP as lemma.
    p6 = lemma(pnp.head.index)                        # The head of the PNP as lemma.
    p7 = s.pos[pnp.head.index]                        # The head of the PNP as part-of-speech tag.    
    p8 = _count_NP(s, chunk.start, pnp.start)         # The number of NPs between the chunk and the PNP.
    p9 = _count_PNP(s, chunk.start, pnp.start)        # The number of PNPs between the chunk and the PNP.
    if pnp.start > chunk.start:
        # The number of commas and other punctuation between the chunk and the PNP.
        # The distance between chunk and pnp (add one so it is never zero).
        comma, other, n = _count_punctuation(s, chunk.stop-1, pnp.start, selection=[u','])
        distance = pnp.start - (pp or chunk).stop + 1
    else:
        comma, other, n = _count_punctuation(s, pnp.stop-1, chunk.start, selection=[u','])
        distance = -1 * ((pp or chunk).start - pnp.stop + 1)
    if pp and distance < 0:
        return None
    # Create the instance.
    format = u'%d %d %d %s %s %s %s %s %s %s %s %d %d'
    format = format % (comma, other, distance, p0, p1, p2, p3, p4, p5, p6, p7, p8, p9)
    return instance.Instance(format, chunk.head.index, pnp.start, chunk.type)

def PP_instances(sentence):
    """ Returns lookup instances for the preposition server, parsed from the given Sentence object.
        For the sentence: "I eat pizza with a fork." the instances will look something like:
        - 0 0 3 - i PRP pizza NN with fork NN 0 0
        - 0 0 2 - eat VBP pizza NN with fork NN 0 0
        - 0 0 1 - pizza NN pizza NN with fork NN 0 0
        The respective responses from the server:
        - CATEGORY {n-NP} DISTRIBUTION { n-NP 3.46845 } DISTANCE {2.03775}
        - CATEGORY {VP} DISTRIBUTION { VP 2.69053, n-VP 0.773870 } DISTANCE {2.0533}
        - CATEGORY {n-NP} DISTRIBUTION { n-NP 22.0963 } DISTANCE {2}
    """
    instances = []
    for pnp in sentence.pnp:
        for chunk in sentence.chunks:
            # Don't attach to words inside this PNP.
            if chunk.start not in pnp.range:
                if chunk.type == 'NP':
                    pp = sentence.get(chunk.start, PNP)
                    if pp is None:
                        instances.append(_PP_instance(sentence, pnp, chunk))
                    elif pp.span != pnp.span:
                        # A NP inside another PNP.
                        instances.append(_PP_instance(sentence, pnp, chunk, pp))
                elif chunk.type == 'VP':
                    instances.append(_PP_instance(sentence, pnp, chunk))
    return [x for x in instances if x is not None]

#-----------------------------------------------------------------------------------------------------
# Create TiMBL lookup instances from a given sentence.
# The given sentence is transformed to a search tree of chunks and prepositions which is traversed.

def _typeof(instances):
    """ Takes a list of tagged instances and returns the type:
        -  0: one positive instance, others negative.
        - +1: more than one positive instance.
        - -1: all negative.
    """
    n = 0
    for instance in instances:
        if not instance.predicted.startswith('n-'): n += 1
    if n == 1: return 0
    if n  > 1: return 1
    return -1
    
def _tuplify(instances):
    """ Returns a (anchor index, PP index)-tuple from a unique tagged instance list.
    """
    if _typeof(instances) != 0:
        raise Exception, 'anchor must be uniquely defined (see prepositions.classify module)'
    for instance in instances:
        if not instance.predicted.startswith('n-'):
            return instance.instance.anchor, instance.instance.pp

def get_pp_attachments(s, format=[WORD, POS, CHUNK, PNP, LEMMA], timeout=None):
    """ Takes a parsed string and returns a tuple of tuples ((anchor index, PP index), ...) 
        and a tuple with info about where the anchor came from (TiMBL/lowest_entropy/baseline).
        - Lowest entropy is used when different anchor candidates have the same score.
        - Baseline is used when no candidates where found with TiMBL.
        The given sentence can also be a Sentence object (see tree.py).
    """
    # Create a parse tree from the parsed string.
    # We need POS, CHUNK and PNP tags, but it works up to 5x faster with LEMMA given.
    if isinstance(s, (str, unicode)):
        s = Sentence(s, token=format)
    # Generate instances from the parse tree.
    # Send the instances to the TiMBL server.
    # The batch() function in the client module takes care of managing server clients,
    # we simply pass it all the tagging jobs and a definition of the client we need.
    instances = PP_instances(s)
    instances2= [x.encode(config.encoding)+' ?' for x in instances]
    tags = batch(instances2, client=(TimblPP, HOST, PORT, config.PREPOSITION, config.log), retries=1)    
    # Tag and group the instances by PP.
    grouped = {}
    for i, x in enumerate(instances):
        grouped.setdefault(x.pp, []).append(instance.TaggedInstance(x, tags[i][0], tags[i][1], tags[i][2]))
    # Revote the instance groups that do not have unique anchors.
    attachments = []
    for instances in grouped.values():
        type = _typeof(instances)
        if type == 0:
            # TiMBL determined the best anchor candidate.
            attachments.append((_tuplify(instances), 'timbl'))
        elif type == +1:
            # There is more than one possible candidate and extra voting is needed.
            # Example: "She added: 'I was a little naive as to the impact it would have 
            #           because I really didn't have any idea it would be like that.'"
            attachments.append((_tuplify(voting.lowest_entropy(instances)), 'lowest_entropy'))
        elif type == -1:
            # There are no candidates so we are going to make a calculated guess.
            # Example: "The red cat at the left is sleeping."
            attachments.append((_tuplify(voting.base_candidate(instances)), 'baseline'))
    # Rules can be applied here (e.g. to correct things like "as for me").
    attachments = rules.apply(attachments, s)
    attachments = tuple([x[0] for x in attachments]), tuple([x[1] for x in attachments])
    return attachments
