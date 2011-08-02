#### MEMORY-BASED SHALLOW PARSER ######################################################################

# Copyright (c) 2003-2010 University of Antwerp, Belgium and Tilburg University, The Netherlands
# Vincent Van Asch <vincent.vanasch@ua.ac.be>, Tom De Smedt <tom@organisms.be>
# License: GNU General Public License, see LICENSE.txt

### RULES ############################################################################################
# Rules can be used to find better anchor candidates.
# Rules are applied in the final step of classify.get_pp_attachments().

try: 
    from MBSP.config import CHUNK, PNP
except ImportError:
    # We will end up here if mbsp.py is called directly from the command line
    from config import CHUNK, PNP

def apply(attachments, sentence):
    """ Applies all the rules. This is called from classify.get_pp_attachments().
        Returns updated attachments based on the rules below.
    """
    if len(attachments) == 0:
        return attachments
    attachments = reattach_inner_anchors(attachments, sentence)
    attachments = reattach_interjections(attachments, sentence)
    return attachments

#--- INNER ANCHORS -----------------------------------------------------------------------------------

def reattach_inner_anchors(attachments, sentence):
    """ Reattaches the PP's to the previous PP in sentences like:
        "I enjoy the weather as for today."
        We append "for" to "as" no matter what the classifiers say.
    """
    output = []
    for (A,P), info in attachments:
        pp = sentence.get(P-1, CHUNK)
        if pp and pp.type == "PP":
            # Note: this should now happen automatically with rule 1) in mbsp._find_prepositions().
            output.append(((P-1, P), 'reattach_inner_anchors'))
        else:
            output.append(((A,P), info))
    return output

#--- INTERJECTIONS -----------------------------------------------------------------------------------

def reattach_interjections(attachments, sentence):
    """ Reattaches the PP's that were attached to a chunk inside brackets, 
        to the chunk in front of the bracket:
        "The purified homodimer (two p50s) of the DNA-binding subunit"
        Instead of "p50s" as anchor we take "homodimer" as anchor for "the DNA-binding subunit".
    """
    
    output = []
    L = sentence.indexof('(') # left round brackets
    R = sentence.indexof(')') # right round brackets
    if len(L) == len(R):
        brackets = zip(L,R)
    else:
        # Do nothing because we don't know which brackets are a pair.
        return attachments
    for (A,P), info in attachments:
        rng = range(A,P)
        if P < A: rng = reversed(rng) # XXX - if P == A should raise ValueError('anchor cannot be pp')
        l = sorted(set(L).intersection(set(rng)))
        r = sorted(set(R).intersection(set(rng)))
        if len(r) == 1 and len(l) == 0:
                # There is a ) between the anchor and the PP.
                # Get the index of the left bracket.
                # Get the chunk before the left bracket.
                # Use the last index of the chunk (head) as the anchor.
                for bracket in brackets:
                    if bracket[1] == r[0]:
                        i = bracket[0]; break
                try:
                    A = sentence.get(i-1, CHUNK).head.index
                except AttributeError:
                    pass # No previous chunk for anchor.
                except IndexError:
                    output.append(((A,P), info))
                else:
                    output.append(((A,P), 'reattach_interjections'))
        else:
            # We end up here if there is a ( ) between A and P,
            # if there are no brackets between, or ( ) ) between.
            output.append( ((A,P), info))
    return output
