#### BIOMINT SHALLOW PARSER ###########################################################################

# Copyright (c) 2003-2010 University of Antwerp, Belgium and Tilburg University, The Netherlands
# License: GNU General Public License, see LICENSE.txt

######################################################################################################

# Biomedical Shallow Parser based on MBSP for Python, 
# using training data from the GENIA corpus.
# See also: http://www.clips.ua.ac.be/projects/biomint-biological-text-mining

import os, sys

MODULE = os.path.dirname(os.path.abspath(__file__))

try: 
    import MBSP
except ImportError:
    for i in range(5):
        # Look for the MBSP module in upper directories.
        p = os.path.join(*[MODULE]+[os.path.pardir]*i)
        if os.path.isdir(os.path.join(p, 'MBSP')):
            sys.path.insert(0,p); break
    import MBSP

# Ensure that the tokenizer's biomedical mode is enabled:
MBSP.tokenizer.BIOMEDICAL = True

# The biomedical parse() function is similar to MBSP's,
# but the output has an additional SEMANTIC tag at the end ('cell_type', 'NONE', ...)
# This tag ends up in Word.custom_tags when split() is called with the TokenString output.
SEMANTIC = 'semantic'

#--- INSTALL SERVERS ---------------------------------------------------------------------------------

MBSP.active_servers.append(
    MBSP.Server(
            name = 'biomedical_pos',
            port = 6065, 
         process = MBSP.MBT,
        features = {'-s' : os.path.join(MODULE, 'models', 'GENIAPOS.settings'),}))
        # All the server options are bundled in a .settings file.
    
MBSP.active_servers.append(
    MBSP.Server(
            name = 'biomedical_sem',
            port = 6066, 
         process = MBSP.MBT,
        features = {'-s' : os.path.join(MODULE, 'models', 'GENIASEM.settings'),}))
        # All the server options are bundled in a .settings file.

#--- EXTEND TAGGER/CHUNKER ---------------------------------------------------------------------------

def update_pos_tag(tokenstring):
    """ Event handler that fires when the MBSP parser is done tagging and chunking.
        Updates the part-of-speech tags from a specialized biomedical corpus.
        Returns the updated string to the parser.
    """
    client = MBSP.Mbt(port=6065)
    # Retag the part-of-speech tags with the GENIA corpus.
    # Example: "TGF-beta1-transcribing/NN/I-NP macrophages/NNS/I-NP"
    s1 = tokenstring.split() 
    # => [[[u'TGF-beta1-transcribing', u'NN', u'I-NP'], [u'macrophages', u'NNS', u'I-NP']]]
    s2 = s1.reduce([MBSP.WORD]) 
    # => [[[u'TGF-beta1-transcribing'], [u'macrophages']]]
    s2 = MBSP.TokenString(client.send(s2.join()), tags=[MBSP.WORD, MBSP.PART_OF_SPEECH])
    # => TGF-beta1-transcribing/JJ macrophages/NNS
    s2 = s2.split() 
    # => [[[u'TGF-beta1-transcribing', u'JJ'], [u'macrophages', u'NNS']]]
    s2.tags.append(MBSP.CHUNK, values=s1.tags.pop(s1.tags.index(MBSP.CHUNK)))
    # => [[[u'TGF-beta1-transcribing', u'JJ', u'I-NP'], [u'macrophages', u'NNS', u'I-NP']]]
    s2 = s2.join()
    # => TGF-beta1-transcribing/JJ/I-NP macrophages/NNS/I-NP
    client.disconnect()
    return s2

MBSP.events.parser.on_parse_tags_and_chunks = update_pos_tag

#--- SEMANTIC PARSER --------------------------------------------------------------------------------

def parse_semantic_tag(tokenstring):
    """ Extension that appends the SEMANTIC tag to the output of the parser.
    """
    client = MBSP.Mbt(port=6066)
    # Find the semantic tag of words in the sentence.
    # Example: "macrophage/NN/I-NP/O/O/O/macrophage".
    s1 = tokenstring.split()
    # => [[[u'macrophage', u'NN', u'I-NP', u'O', u'O', u'O', u'macrophage']]]
    s2 = s1.reduce([MBSP.WORD])
    # => [[[u'macrophage']]]
    s2 = MBSP.TokenString(client.send(s2.join()), tags=[MBSP.WORD, SEMANTIC])
    # => macrophage/protein
    s2 = s2.split()
    # => [[[u'macrophage', u'protein']]]
    s1.tags.append(SEMANTIC, values=s2.tags.pop(s2.tags.index(SEMANTIC)))
    # => [[[u'macrophage', u'NN', u'I-NP', u'O', u'O', u'O', u'macrophage', u'protein']]]
    s1 = s1.join()
    # => macrophage/NN/I-NP/O/O/O/macrophage/protein
    client.disconnect()
    return s1

#-----------------------------------------------------------------------------------------------------

def parse(*args, **kwargs):
    s = MBSP.parse(*args, **kwargs)
    s = parse_semantic_tag(s)
    return s

#-----------------------------------------------------------------------------------------------------

# This example assumes that the servers have been started:
print parse("TGF-beta1-transcribing macrophage is observed")
