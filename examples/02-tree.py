#### MEMORY-BASED SHALLOW PARSER ######################################################################

# Copyright (c) 2003-2010 University of Antwerp, Belgium and Tilburg University, The Netherlands
# License: GNU General Public License, see LICENSE.txt

######################################################################################################

# Add the upper directory (where the MBSP module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..", ".."))
import MBSP

if not MBSP.config.autostart:
    MBSP.start()

s = MBSP.parse("I eat pizza with a fork.")
s = MBSP.split(s) # Yields a list of traversable Sentence objects.
      
for sentence in s:
    for chunk in sentence.chunks:
        print repr(chunk)
        print
        print "      Words:", chunk.words       # A list of Word objects.
        print "  Relations:", chunk.related     # A list of Chunk objects.
        print " Parent PNP:", repr(chunk.pnp)   # A PNPChunk object, or None.
        print "Related PNP:", chunk.attachments # A list of PNPChunk objects.
        print
        
# Remove the servers from memory when you're done:
# MBSP.stop()