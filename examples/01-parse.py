#### MEMORY-BASED SHALLOW PARSER ######################################################################

# Copyright (c) 2003-2010 University of Antwerp, Belgium and Tilburg University, The Netherlands
# License: GNU General Public License, see LICENSE.txt

######################################################################################################

# Add the upper directory (where the MBSP module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..", ".."))
import MBSP
from MBSP.prepositions import rules
reload(rules)

if not MBSP.config.autostart:
    MBSP.start()

q = 'I eat pizza with a fork.'
s = MBSP.parse(q,
     tokenize = True, # Split tokens, e.g. 'fork.' => 'fork' + '.'
         tags = True, # Assign part-of-speech tags => 'fork' = noun = NN.
       chunks = True, # Assign chunk tags => 'a' + 'fork' = noun phrase = NP.
    relations = True, # Find chunk relations: 'I' = sentence subject = NP-SBJ-1.
      anchors = True, # Find prepositional noun phrase anchors.
      lemmata = True) # Find word lemmata.

# Print the output of the parser in a readable table format.
# The tags assigned to each part-of-speech are listed at:
# http://www.clips.ua.ac.be/pages/mbsp-tags
MBSP.pprint(s)

# Print the output of the parser as XML:
print
print MBSP.xml(s)

# Remove the servers from memory when you're done:
# MBSP.stop()
