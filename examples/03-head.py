#### MEMORY-BASED SHALLOW PARSER ######################################################################

# Copyright (c) 2003-2010 University of Antwerp, Belgium and Tilburg University, The Netherlands
# License: GNU General Public License, see LICENSE.txt

######################################################################################################

# Add the upper directory (where the MBSP module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..", ".."))
import MBSP

if not MBSP.config.autostart:
    MBSP.start()

s = MBSP.parse("I ate many slices of pizza with a fork.")
s = MBSP.split(s)

# A useful operation is to extract the heads in a sentence,
# for example to create a "normalized" sentence, or to construct a Timbl lookup instance.
# A head is the principal word in a chunk.
# We could retrieve the heads by iterating over Sentence.chunks, 
# but this would skip the loose words in between chunks (e.g. "and" or ","),
# which can also be useful, particularly in the case of contructing a lookup instance.
# Sentence.constituents() returns an in-order list of mixed Chunk and Word objects 
# that can be used for this purpose:
heads = []
for p in s[0].constituents(pnp=False):
    if isinstance(p, MBSP.Word):
        heads.append((
            p.index, 
            p.lemma))
    if isinstance(p, MBSP.Chunk):
        heads.append((
            p.head.index, 
            p.head.lemma))

print heads

# Remove the servers from memory when you're done:
# MBSP.stop()