#### MEMORY-BASED SHALLOW PARSER ######################################################################

# Copyright (c) 2003-2010 University of Antwerp, Belgium and Tilburg University, The Netherlands
# Vincent Van Asch <vincent.vanasch@ua.ac.be>, Tom De Smedt <tom@organisms.be>
# License: GNU General Public License, see LICENSE.txt

### PREPOSITIONS #####################################################################################
# Implements a trimmed version of the PP attacher.
# The PP attacher finds out which is the anchor chunk for prepositions.
# For example: "I eat pizza with a fork" => "eat" in what way? => "with a fork".
# Running the parser with PP-attachment involves a lot of server queries, it is about 3x slower
# (on a MacBook Pro, 50 minutes for 650 sentences vs. 17 minutes without PP-attachment).

import classify  # PP classifier.
import instance  # Lookup instances for PP TiMBL client.
import voting    # Revotes TiMBL output when ambiguation occurs..
import rules     # Updates specific output from TiMBL.
    
try:
    from MBSP.cache import Cache
except ImportError:
    # We will end up here if mbsp.py is called directly from the command line.
    from cache import Cache
    
# Keep the last results of the parser stored in cache for faster retrieval.    
cache = Cache(size=100, hashed=True)

######################################################################################################

def pp_attachments(parsed_string, *args, **kwargs):
    """ Returns a list of (anchor, PP)-tuples, where anchor and PP are word indices.
        For example: "The airplane flies above the clouds" 
        => [(2,3)] 
        => "above" is attached to "fly".
        The given string is the output from MBSP.parse(), with at least POS, CHUNK, PNP tags.
    """
    k = repr(parsed_string)
    if k in cache:
        return cache[k]
    attachments, sources = classify.get_pp_attachments(parsed_string, *args, **kwargs)
    attachments = list(attachments)
    cache[k] = attachments
    return attachments

attachments = anchors = pp_attachments