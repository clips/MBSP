#### MEMORY-BASED SHALLOW PARSER ######################################################################

# Copyright (c) 2003-2010 University of Antwerp, Belgium and Tilburg University, The Netherlands
# Vincent Van Asch <vincent.vanasch@ua.ac.be>, Tom De Smedt <tom@organisms.be>
# License: GNU General Public License, see LICENSE.txt

#### CONFIG ##########################################################################################
# Settings for MBSP:
# - verbosity
# - ports to run severs on,
# - start servers when imported or not,
# - path to MBSP module,
# - path to TiMBL6, MBT3 and resource files,
# - character encoding to be used,
# - slash special character.

import os, sys, stat

#-----------------------------------------------------------------------------------------------------
# Verbosity of the MBSP parser.
# If verbosity set to True more info is printed during startup.
verbose = True

#-----------------------------------------------------------------------------------------------------
# Network ports for the servers (chunk / lemma / relation / PP-attachment).
# The default startup order of the servers is:
# servers = ['chunk', 'lemma', 'relation', 'preposition']
servers = ['chunk', 'lemma', 'relation', 'preposition']
ports = [6061, 6062, 6063, 6064] # Restart servers when changed.

#-----------------------------------------------------------------------------------------------------
# The hosts where the servers are running. 
# The order is the same as the ports.
LOCALHOST = 'localhost'
hosts = [LOCALHOST, LOCALHOST, LOCALHOST, LOCALHOST]

#-----------------------------------------------------------------------------------------------------
# Automatically start servers at localhost when importing or not? 
# If set to False you have to start the servers manually or make HOSTS point
# to a host where the servers are running before you can use the parser.
autostart = True
autostop  = False
timeout   = 60

#-----------------------------------------------------------------------------------------------------
# Keep logs of the requests sent to the TiMBL and MBT servers (and their response) or not?
# Logging increases the memory overhead and amounts to some extra operations during a server request,
# but there is a (small) chance the request is already in cache so we don't have to contact the server.
log = False

#-----------------------------------------------------------------------------------------------------
# As of TiMBL 6.3.0 + TiMBLServer 1.0.0, there is stable support for concurrent server requests.
# Enabling threading to contact a 6.3+ server can increase performance by 25% - 200%.
threading = False

#-----------------------------------------------------------------------------------------------------
# The folder where MBSP resides.
# By default this is the same path as config.py.
MODULE = os.path.dirname(os.path.abspath(__file__))

#-----------------------------------------------------------------------------------------------------
# If servers are run at localhost you must also set:
# - path to the local TiMBL executable and the local MBT executable, 
# - the MBLEM lemmatizer executable,
# - the folder where the training data is.
paths = dict(
    timbl  = os.path.join(MODULE, 'timbl', 'Timbl'), \
    mbt    = os.path.join(MODULE, 'mbt', 'Mbt'), \
    mblem  = os.path.join(MODULE, 'mblem', 'mblem_english_bmt'), \
    models = os.path.join(MODULE, 'models')
)

#-----------------------------------------------------------------------------------------------------
# Path to the Perl binary.
# This is deprecated, all Perl dependencies now have pure-Python implementations.
perl = '/usr/bin/perl'

#-----------------------------------------------------------------------------------------------------
# Default string encoding used with the parse() command:
encoding = 'utf-8'

#-----------------------------------------------------------------------------------------------------
# MBSP uses a / to separate tags in a tagged word.
# Slashes in the word itself are encoded (e.g. hello/goodbye => hello/UH &slash;/SYM goodbye/NN).
SLASH = "&slash;"

#-----------------------------------------------------------------------------------------------------
# If you create your own models and start the servers you may want to change 
# the settings used to start the TiMBL and MBT servers in the file server.py.

######################################################################################################
# You don't need to change anything below this line.
######################################################################################################

# Token tags:
ALL    = "all"
WORD   = "word"           # The word as it appears in the sentence.
POS    = "part-of-speech" # The part-of-speech of the word (e.g. noun, adjective).
CHUNK  = "chunk"          # The chunk tag of a group of words (e.g. noun phrase, verb phrase).
PNP    = "preposition"    # Indicates a prepositional noun phrase (e.g. with a fork)
REL    = "relation"       # Verb/argument tags (e.g. sentence subject, sentence object).
ANCHOR = "anchor"         # The chunk has prepositional noun phrases attached (e.g. eat => with a fork).
LEMMA  = "lemma"          # The base form of the word (e.g. mice => mouse).

PART_OF_SPEECH = POS
RELATION       = REL
PREPOSITION    = PNP

# Common chunk tags:
NP   = "NP"   # noun phrase
VP   = "VP"   # verb phrase
PP   = "PP"   # preposition
ADJP = "ADJP" # adjective phrase
ADVP = "ADVP" # adverb phrase
DT   = "PRT"  # determiner
CC   = "CC"   # coordinating conjunction

CHUNKS = PHRASES = [NP, VP, PP, ADJP, ADVP, DT, CC]

# Common role tags:
SBJ  = "SBJ"  # subject
OBJ  = "OBJ"  # object
PRD  = "PRD"  # predicate
CLR  = "CLR"  # closely related
DIR  = "DIR"  # direction
EXT  = "EXT"  # extent
LOC  = "LOC"  # location
PRP  = "PRP"  # purpose

ROLES = [SBJ, OBJ, PRD, CLR, DIR, EXT, LOC, PRP]

#-----------------------------------------------------------------------------------------------------

# True when running on Windows.
WINDOWS = sys.platform.startswith('win')

#-----------------------------------------------------------------------------------------------------

class adict(dict):
    """ A dictionary in which every key is available as attribute, i.e. adict.key => value.
    """
    def __setattr__(self, k, v):
        self[k] = v
    def __getattr__(self, k):
        if k in self: return self[k]
        raise AttributeError, "'adict' object has no attribute '%s'" % k 

# Events offer a simple way to customize to MBSP.
# You can inject your own functions at various stages of the parsing process
# (for example, to alter tokenization or token tags).
events = adict()
# Server event handlers take a Server object as input.
# Function format: handler(server) => None
events.server = adict.fromkeys([
    'on_register',              # When a server is registered in Servers, but before it is started.
    'on_start',                 # When a server has successfully started.
    'on_stop'                   # When a server has successfully stopped.
])
# Parser event handlers take the processed input string of MBSP.parse() at various stages.
# Function format: handler(tokenstring) => tokenstring
# The tokenstring.tags contains all tags parsed so far.
# Note: token tags cannot be added, deleted or reordered since the parser is still using them;
#       they can only be edited.
events.parser = adict.fromkeys([
    'on_tokenize',              # When the string has been tokenized.
    'on_parse_tags_and_chunks', # When the string has been parsed for part-of-speech and chunk tags.
    'on_parse_prepositions',    # When the string has been parsed for PNP-chunks.
    'on_parse_relations',       # When the string has been parsed for relation tags.
    'on_parse_pp_attachments ', # When the string has been parsed for PP-attachments.
    'on_lemmatize',             # When the string has been parsed for word lemmata.
], None)

#-----------------------------------------------------------------------------------------------------

def _executable(path):
    mode = stat.S_IXUSR | stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH | stat.S_IXGRP | stat.S_IXOTH
    if os.path.isfile(path):
        if not os.access(path, os.X_OK):
            os.chmod(path, mode)

# Ensure TiMBL, MBT and mblem are executable.
_executable(paths['timbl'])
_executable(paths['mbt'])
_executable(paths['mblem'])
