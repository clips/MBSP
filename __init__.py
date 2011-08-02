#### MEMORY-BASED SHALLOW PARSER ######################################################################

# Copyright (c) 2003-2010 University of Antwerp, Belgium and Tilburg University, The Netherlands
# Vincent Van Asch <vincent.vanasch@ua.ac.be>, Tom De Smedt <tom@organisms.be>
# License: GNU General Public License, see LICENSE.txt
#
#   MBSP is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 3 of the License, or
#   (at your option) any later version.
#
#   MBSP is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
# 
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, see <http://www.gnu.org/licenses/>.
#
# Reference:
# Daelemans, W. and A. van den Bosch (2005) "Memory-Based Language Processing." 
# Cambridge: Cambridge University Press.
#
# CLiPS Computational Linguistics Group, University of Antwerp, Belgium
# Induction of Linguistics Research Group, Tilburg University, The Netherlands

### CREDITS ##########################################################################################

__author__    = "Vincent Van Asch, Tom De Smedt"
__version__   = "1.4"
__copyright__ = "Copyright (c) 2003-2010 University of Antwerp (BE), Tilburg University (NL)"
__license__   = "GPL"

######################################################################################################
# Memory-Based Shallow Parser for Python 2.5+
# MBSP is a text analysis system based on the TiMBL and MBT memory based learning applications
# developed at CLiPS (previously CNTS) and ILK. 
# It provides tools for Tokenization and Sentence Splitting, Part of Speech Tagging, Chunking, 
# Lemmatization, Relation Finding and Prepositional Phrase Attachment.
# The general English version of MBSP has been trained on data from the Wall Street Journal corpus.
#
# For example:
# 'I eat pizza with a fork.' is transformed into:
# u'I/PRP/B-NP/O/NP-SBJ-1/O/i 
#   eat/VBP/B-VP/O/VP-1/A1/eat 
#   pizza/NN/B-NP/O/NP-OBJ-1/O/pizza 
#   with/IN/B-PP/B-PNP/PP/P1/with 
#   a/DT/B-NP/I-PNP/NP/P1/a 
#   fork/NN/I-NP/I-PNP/NP/P1/fork 
#   ././O/O/O/O/.'
#
# The sentence period has been split from 'fork'.
# The word 'I' has been tagged as PRP (personal pronoun), NP chunk (noun phrase), SBJ-1 
# (first sentence subject, related to VP-1), etc.

import os, sys
import config         # General settings for server ports and autostarting.
import server         # TiMBL and MBT servers.
import client         # TiMBL and MBT clients.
import mbsp           # The parser: part-of-speech tagger, chunker, lemmatizer, relation finder, PP-attachment.
import tokenizer      # The parser's sentence tokenizer.
import relationfinder # The parser's relation finder.
import prepositions   # The parser's PP-attacher.
import tree           # Tree traversal of chunks in the sentence.
import tags           # Tag information.

# Four different servers will be started.
# - lemma: for word lemmatization: "was" => "be".
# - chunk: for word tagging and phrase detection: "the big ocean" = > the/DT/NP big/JJ/NP ocean//NN/NP
# - relation: for finding subject/object/predicate relations between phrases.
# - preposition: for attaching prepositions to their anchor: "eating with a fork" => eating how? => with a fork.
from config import LEMMA, CHUNK, RELATION, PREPOSITION, ALL
from config import events
from server import active_servers, Server, Servers, TIMBL, MBT
from client import Client, Timbl, Mbt, LOCALHOST, log
from client import ClientError, ClientDisconnectedError, ClientTimeoutError, ServerConnectionError
from client import CONNECTION_RESET_BY_PEER, CONNECTION_REFUSED, BROKEN_PIPE
from mbsp   import TokenString, TokenList, TokenTags, TOKENS
from tree   import Text, Sentence, Slice, Chunk, PNPChunk, Chink, Word, AND, OR
from tags   import description as taginfo

######################################################################################################
# MBSP will split a string into sentences with words, and assign grammatical tags to words.
# For example: pizza/NN/B-NP/O/NP-OBJ-1/O/pizza (word/pos/chunk/pnp/relation/anchor/lemma)

WORD     = config.WORD        # The word as it appears in the sentence.
POS      = config.POS         # The part-of-speech of the word (e.g. noun, adjective).
CHUNK    = config.CHUNK       # The chunk tag of a group of words (e.g. noun phrase, verb phrase).
PNP      = config.PREPOSITION # Indicates a prepositional noun phrase (e.g. with a fork)
RELATION = config.RELATION    # Verb/argument tags (e.g. sentence subject, sentence object).
ANCHOR   = config.ANCHOR      # The chunk has prepositional noun phrases attached (e.g. eat => with a fork).
LEMMA    = config.LEMMA       # The base form of the word (e.g. mice => mouse).

PART_OF_SPEECH = POS # Not used internally because too long.
REL = RELATION       # Not used externally because too short.

# Common chunk tags:
from config import NP, VP, PP, ADJP, ADVP, DT, CC
from config import SBJ, OBJ, PRD, CLR, DIR, EXT, LOC, PRP

######################################################################################################

def clear_cache():
    """ Clears the parser cache, the client logs and all internal clients.
    """
    for dict in (mbsp.cache, prepositions.cache, client.log, client._clients, ):
        dict.clear()

def started(name=ALL):
    """ Returns True when the TiMBL and MBT servers are up and running.
        The servers can also be checked individually by name (CHUNK/LEMMA/RELATION/PREPOSITION).
    """
    return active_servers.started(name != ALL and name or None)

def start(timeout="default"):
    """ Starts the TiMBL and MBT servers.
        If some of the servers are unable to start in 60 seconds (default), raises an error.
    """
    if timeout == "default": timeout = config.timeout # 60
    active_servers.start(timeout)

def stop():
    """ Stops the TiMBL and MBT servers by killing the process id's.
        Clears the parser cache, the client logs and all internal clients.
        This ensures there are no stray clients referencing old servers,
        or cache entries parsed with old servers.
    """
    active_servers.stop(); clear_cache()

def parse(*args, **kwargs):
    """ Takes a string of sentences and returns a tagged Unicode string. 
        Sentences in the output are separated by newline characters. 
        The input must be a unicode object. If it is a string it will be decoded using config.encoding.
        - tokenize  : if False no tokenization is carried out (the input must be tokenized already).
        - tags      : if False doesn't add the part-of-speech tags  (e.g. NN) to the output.
        - chunks    : if False doesn't add the chunk (e.g. NP) and PNP tags to the output.
        - relations : if False doesn't search for relations (-SBJ etc.)
        - anchors   : if False doesn't search for PP anchors.
        - lemmata   : if False doesn't search for lemmata.
        - encoding  : encoding used to decode the input.
    """
    return mbsp.parse(*args, **kwargs)

######################################################################################################

def tokenize(*args, **kwargs):
    return mbsp.tokenize(*args, **kwargs)
    
def tag(*args, **kwargs):
    return mbsp.tag(*args, **kwargs)
    
def chunk(*args, **kwargs):
    return mbsp.chunk(*args, **kwargs)
    
def lemma(*args, **kwargs):
    return mbsp.lemma(*args, **kwargs)
    
def lemmatize(*args, **kwargs):
    return mbsp.lemmatize(*args, **kwargs)
    
def nouns(*args, **kwargs):
    return mbsp.nouns(*args, **kwargs)
    
def adjectives(*args, **kwargs):
    return mbsp.adjective(*args, **kwargs)
    
def verbs(*args, **kwargs):
    return verbs(*args, **kwargs)

######################################################################################################

def split(string, token=[WORD, POS, CHUNK, PNP, RELATION, ANCHOR, LEMMA]):
    """ Transforms the output from MBSP.parse() into a traversable Text object.
        The token parameter lists the order of tags in each token in the input string.
    """
    return tree.Text(string, token)

def xml(string, token=[WORD, POS, CHUNK, PNP, RELATION, ANCHOR, LEMMA]):
    """ Transforms the output from MBSP.parse() into an XML string.
        The format parameter lists the order of tags in each token in the input string.
    """
    return tree.Text(string, token).xml
    
def pprint(string, token=[WORD, POS, CHUNK, PNP, RELATION, ANCHOR, LEMMA], column=4):
    """ Pretty-prints the output of MBSP.parse() as a table with outlined columns.
        Alternatively, you can supply a Text or Sentence object.
    """
    if isinstance(string, basestring):
        print "\n\n".join([tree.table(sentence, fill=column) for sentence in tree.Text(string, token)])
    if isinstance(string, tree.Text):
        print "\n\n".join([tree.table(sentence, fill=column) for sentence in string])
    if isinstance(string, tree.Sentence):
        print tree.table(string, fill=column)
