#### MEMORY-BASED SHALLOW PARSER ######################################################################

# Copyright (c) 2003-2010 University of Antwerp, Belgium and Tilburg University, The Netherlands
# Vincent Van Asch <vincent.vanasch@ua.ac.be>, Tom De Smedt <tom@organisms.be>
# License: GNU General Public License, see LICENSE.txt

### MBSP #############################################################################################
# Python version of mbsp.sh.
# Combines the functionality of the tokenizer, MBLEM lemmatizer, MBT chunker, TiMBL relation finder 
# and TiMBL PP-attacher into the parse() function. All of these processes are started as servers
# (see server.py) and contacted by the clients (see client.py).
#
# Tags sentences with part-of-speech tags, chunk tags, relation tags, preposition anchors.
# For a full list of possible tags, see tags.py.
#
# Parsing includes the following steps:
#
# - Tokenization            : split sentence periods and punctuation marks from words.
# - Tagging                 : assign part-of-speech tags (e.g. noun, verb) to words.
# - Chunking                : assign chunk tags (e.g. noun phrase) to groups of words.
# - Verb-argument relations : find sentence subject, object and predicates.
# - Prepositions            : find prepositional noun phrases (e.g. "under the table").
# - PP-attachment           : find prepositional noun phrase anchors (e.g. "eat pizza" <=> "with fork").
# - Lemmatization           : find word lemmata (e.g. was => be).
#
# First make sure the servers are running.
# Usage:
# >>> print parse(u'Draw a red car.')
# Draw/VB/I-VP/O/VP-1/draw a/DT/I-NP/O/NP-OBJ-1/a red/JJ/I-NP/O/NP-OBJ-1/red car/NN/I-NP/O/NP-OBJ-1/car ././O/O/O/.

import os, sys, socket, time, re, subprocess, tempfile
import config
import client
import server
import tokenizer
import relationfinder
import prepositions

from config import WORD, POS, CHUNK, PNP, REL, ANCHOR, LEMMA
from config import SLASH

# Keep the last results of the parser stored in cache for faster retrieval.
from cache import Cache
cache = Cache(size=25, hashed=True)

PERL         = config.perl                       # Path to Perl (deprecated).
PERL_SCRIPTS = os.path.join(config.MODULE, 'pl') # Path to the Perl scripts included in MBSP.
MODELS       = config.paths['models']            # Path to MBSP training data.
LEMMATIZER   = config.paths['mblem']             # Path to MBLEM lemmatizer.

PORTS = dict(zip(config.servers, config.ports[:len(config.servers)]))
HOSTS = dict(zip(config.servers, config.hosts[:len(config.servers)]))

#### PARSER ##########################################################################################

def encode_entities(string):
    """ Slashes are used as metacharacters by the chunker,
        and angle brackets are used by the lemmatizer so these are reserved characters.
        For example, a string we want to parse could contain "and/or" and this slash
        conflicts with the slashes used for tags (and/CC); therefore we encode it.
    """
    return string.replace('/', SLASH).replace('<', '&lt;').replace('>', '&gt;')
    
def decode_entities(string, slashes=False):
    """ Replaces encodes &lt; &gt; and &slash; with < > /
    """
    if slashes:
        string = string.replace(SLASH, '/')
    return string.replace('&lt;', '<').replace('&gt;', '>')

#--- PERL TOKENIZER ----------------------------------------------------------------------------------
# The Perl tokenizer is deprecated; tokenization is now done in pure Python (see tokenizer.py).

def pipe(program, input=None):
    """ Executes the program and returns stdout - see Python documentation on the subprocess module.
        This is used to retrieve data from Perl scripts or from the MBLEM lemmatizer.
    """
    try:
        process = subprocess.Popen(program, 
             stdin = subprocess.PIPE, 
            stdout = subprocess.PIPE, 
            stderr = subprocess.PIPE)
    except OSError, e:
        if e.args[0] == 8:
            # Error occured in the Perl / C++ source code.
            s = 'binary %s is not working correctly, try recompiling it' % os.path.basename(program[0])
            raise Exception, s
        else:
            raise
    out, err = process.communicate(input)
    return out

def split_unicode_accents(string):
    """ Takes a unicode string and separates unicode accents from the words. Returns unicode string.
        This is required when using the Perl implementation of the tokenizer.
    """
    accents = [ u'\u0060', # grave accent
                u'\u00b4', # accute accent
                u'\u00ab', # left-pointing double angle quotation mark
                u'\u00bb', # right-pointing double angle quotation mark
                u'\u02b9', # Modifier Letter Prime
                u'\u02ba', # Modifier Letter Turned Comma
                u'\u02bb', # Modifier Letter Turned Comma
                u'\u02bc', # Modifier Letter Apostrophe
                u'\u02bd', # Modifier Letter Reversed Comma
                u'\u02be', # Modifier Letter Right Half Ring
                u'\u02bf', # Modifier Letter Left Half Ring
                u'\u02ca', # Modifier Letter Acute Accent
                u'\u02bb', # Modifier Letter Grave Accent
                u'\u02dd', # Double Acute Accent
                u'\u02ee', # Modifier Letter Double Apostrophe
                u'\u02f4', # Modifier Letter Middle Grave Accent
                u'\u02f5', # Modifier Letter Middle Double Grave Accent
                u'\u02f6', # Modifier Letter Middle Double Acute Accent
                u'\u201c', # left double quotation mark
                u'\u2018', # left single quotation mark
                u'\u201d', # right double quotation mark
                u'\u201e', # double low-9 quotation mark
                u'\u2026', # horizontal ellipsis
                u']',  
                u'[',
                u'}',  
                u'{',
                ]
    for accent in accents: string = string.replace(accent, ' '+accent+' ')
    # Remove space between accents:
    string = string.replace(u'\u0060 \u0060', u'\u0060\u0060')
    string = string.replace(u'\u00b4 \u00b4', u'\u00b4\u00b4') 
    # Only split with two spaces if the word isn't "'s".
    string = re.sub(u'\u2019(?!s\s)', u' \u2019 ', string, re.U)
    # Otherwise split with only one space.
    string = re.sub(u'\u2019(?=s\s)', u' \u2019', string, re.U)
    return string

def _perl_tokenize(string):
    """ Takes a string and tokenizes it using tokenize.pl and language set to "eng".
        Tokenization divides a sequence of characters into words and sentences,
        using regular expressions.
    """
    return pipe([PERL, 
        os.path.join(PERL_SCRIPTS, 'tokenize.pl'), '-l', 'eng', '-p', 
        os.path.join(PERL_SCRIPTS, 'resources/lists')], string)

def _perl_format(string):
    """ Reformats the output of tokenize.pl into a list of strings.
        Simple lists are split: <utt>1. foo 2. bar</utt> => ['1. foo','2.bar']
    """
    if not string:
        raise ValueError('No input or empty string for Perl tokenizer.')
    # First normalize whitespace.
    # Remove whitspace in front and after every marker.
    # Remove first <utt> and last </utt>.
    string = ' '.join(string.strip().split())
    string = re.sub(' ?<utt> ?', '<utt>', string)
    string = re.sub(' ?</utt> ?', '</utt>', string)
    string = re.sub('^<utt>', '', string)
    string = re.sub('</utt>$', '', string)
    # Split into newlines.
    strings = re.sub('</utt><utt>', '\n', string).split('\n')
    # Simple handler for lists:
    sentences = []
    for sentence in strings:
        enumeration = re.search('(\d+)\. (\w+ )+(\d+)\. ', sentence) 
        if enumeration and int(enumeration.group(3)) - int(enumeration.group(1)) == 1:
            # We have an enumeration, so split.
            # We only check the first two occurrences of numbers so
            # 1. foo 2. bar is splitted
            # 2. foo 1. bar is not splitted
            # 2. foo 1. bar 2. koo is not splitted
            parts = re.sub(' (\d+)\. ', '\n\g<1>. ', sentence).split('\n')
            for p in parts:
                sentences.append(p.strip())
        else:
            sentences.append(sentence.strip())
    return sentences

#--- PYTHON TOKENIZER --------------------------------------------------------------------------------

def _tokenize(string):
    """ Returns a string where sentences are separated by a new line.
        Tokens (i.e. individual words and punctuation marks) in a sentence are separated by a space.
    """
    # See tokenizer.py for more details.
    return '\n'.join(tokenizer.split(string))

#--- CHUNKER -----------------------------------------------------------------------------------------

def _chunk(string):
    """ Takes a tokenized and escaped string where sentences are separated by a new line.
        Returns a string where words have been tagged with their part-of-speech and chunk tags.
        Common part-of-speech tags include NN (noun), VB (verb), JJ (adjective), PP (preposition).
        Common chunk tags include NP (noun phrase), VP (verb phrase), ...
        - input: ['Draw a red car .']
        - output: Draw/VB/I-VP a/DT/I-NP red/JJ/I-NP car/NN/I-NP ././O
    """
    sentences = filter(lambda x: len(x)>0, string.splitlines())
    host = HOSTS[CHUNK]
    port = PORTS[CHUNK]
    # Send the sentences to the TiMBL server.
    # The batch() function in the client module takes care of managing server clients,
    # we simply pass it all the tagging jobs and a definition of the client we need.
    return '\n'.join(client.batch(sentences, client=(client.Mbt, host, port, CHUNK, config.log), retries=1))

#--- PREPOSITION FINDER ------------------------------------------------------------------------------

def _find_prepositions(string):
    """ Adds PNP-tags to the chunked words.
        The input is the string with slash-formatted tokens returned from _chunk().
        - input : Draw/VB/I-VP a/DT/I-NP red/JJ/I-NP car/NN/I-NP ././O
        - output: Draw/VB/I-VP/O a/DT/I-NP/O red/JJ/I-NP/O car/NN/I-NP/O ././O/O
    """
    # The older Perl implementation:
    #return pipe([PERL, os.path.join(PERL_SCRIPTS, 'pnpfinder.pl')], string)
    s = string.splitlines()
    # Functions to facilitate look-back and look-ahead:
    pos       = lambda T,i: i < len(T) and T[i][-3] or ""     # Part-of-speech tag in current token.
    ch        = lambda T,i: i < len(T) and T[i][-2] or ""     # Chunk tag in current token.
    ch_before = lambda T,i: i > 0 and T[i-1][-2] or ""        # Chunk tag in previous token.
    ch_after  = lambda T,i: i < len(T)-1 and T[i+1][-2] or "" # Chunk tag in next token.
    for i in range(len(s)):
        T = s[i].split(" ") # "T" stands for "a sentence as a split list of tokens".
        T = [token.split("/")+["O"] for token in T]
        j = 0
        # Traverse the tokens in the sentence.
        # The PNP-tagger is triggered when the chunk tag of a token is "PP".
        while j < len(T):
            # A PP marks the start of a new PNP chunk.
            if ch(T,j).endswith("PP"):
                k = j + 1
                while k < len(T) and ch(T,k).endswith("PP"):
                    # PP's directly following this PP are part of the PNP:
                    # due to, as with, based on, such as, ...
                    k += 1
                while k < len(T) and pos(T,k) in ('IN','TO') and ch(T,k) == "SBAR":
                    # Essentially the same as the previous rule,
                    # but it catches something like: "on/IN/PP whether/IN/SBAR users/NNS/NP".
                    k += 1
                while k < len(T) and ch(T,k).endswith("VP") and pos(T,k) == "VBG" and ch(T,k+1).endswith("NP"):
                    # A gerund following the PP is allowed if it is followed by a NP, for example:
                    # "Wolf cubs are submissive to their parents , and remain so [AFTER REACHING sexual maturity] ."
                    k += 1
                while k < len(T) and ch(T,k).endswith("NP"):
                    # NP's following a PP are part of the PNP, as long as it is not B-NP
                    # preceded by I-NP (the new noun phrase is not part of the preposition).
                    if ch(T,k) == "B-NP" and ch_before(T,k) == "I-NP": break
                    k += 1
                k -= 1
                # Tag the range, after ensuring that it ends with a NP (and thus is a P+NP).
                if k > j and ch(T,k).endswith("NP"):
                    T[j][-1] = "B-PNP"
                    for k in range(j+1, k+1): T[k][-1] = "I-PNP"
                    j = k
            j += 1
        s[i] = " ".join(["/".join(token) for token in T])
    return "\n".join(s)

#--- RELATION FINDER ---------------------------------------------------------------------------------

def _find_relations(string):
    """ Adds the relation tags to the chunked words.
        The input is the slash-formatted string of tokens returned from _find_prepositions().
        Sentence subjects get the -SBJ tag, sentence objects the -OBJ tag.
        Verbs and their arguments get the same id, for example NP-SBJ-1 and VP-1 belong together.
        - input : Draw/VB/I-VP/O a/DT/I-NP/O red/JJ/I-NP/O car/NN/I-NP/O ././O/O
        - output: Draw/VB/I-VP/O/VP-1 a/DT/I-NP/O/NP-OBJ-1 red/JJ/I-NP/O/NP-OBJ-1 car/NN/I-NP/O/NP-OBJ-1 ././O/O/O
    """
    # See relationfinder.py for more details.
    sentences = filter(lambda x: len(x)>0, string.splitlines())
    return '\n'.join([relationfinder.tag(sentence) for sentence in sentences])

#--- PP ATTACHER -------------------------------------------------------------------------------------

def _find_pp_attachments(string, format=[WORD, POS, CHUNK, PNP, REL, LEMMA]):
    """ Adds the anchor tags to the PNP-tagged sentence.
        The input is the string of tokens returned from _find_prepositions() or _find_relations().
        PNP chunks for which an anchor is found are tagged with P.
        Anchors (usually a VP) are tagged with A.
        Anchors and their related PNP's get the same id, for example A1 and P1.
    """
    # See prepositions.py for more details.
    s = string.splitlines()
    for i in range(len(s)):
        tokens = s[i].split(" ")
        tokens = [token.split("/") for token in tokens]
        attachments = prepositions.pp_attachments(s[i], format)
        # Create a list of anchor tags for each token in the sentence.
        # Anchors will get A1, A2 (or A1-A2), prepositions get P1, P2, ...
        tags = ["O" for token in tokens]
        join = lambda s1, s2: s1=="O" and s2+str(id+1) or "%s-%s%s"%(s1,s2,str(id+1))
        for id, (A,P) in enumerate(attachments):
            tags[A] = join(tags[A], "A")
            tags[P] = join(tags[P], "P")
            # Roll back to tag all preceding verbs in the same VP as anchor too.
            for j in reversed(range(A)):
                if tokens[j][2][1:] == tokens[A][2][1:]:
                    tags[j] = join(tags[j], "A")
                else:
                    break
                if tokens[j][2].startswith("B-"):
                    break
            # Roll forward to tag the NP's following the PP in the PNP too.
            for j in range(P+1, len(tokens)):
                if tokens[j][3].startswith("B-"):
                    break
                if tokens[j][3][1:] == tokens[P][3][1:]:
                    tags[j] = join(tags[j], "P")
                else:
                    break
        # Add the anchor tag to each token in the sentence.
        for j in range(len(tokens)):
            tokens[j].append(tags[j])
        s[i] = " ".join(["/".join(token) for token in tokens])
    return "\n".join(s) 

#--- LEMMATIZER --------------------------------------------------------------------------------------

# Overrides MBLEM.
# Entries have the following form: {'saw\tVBD\tsaw' : 'saw\tVBD\tsee'}
_lemmatizer_exceptions = {}

def _lemmatize_prepare(string):
    """ Reformats the chunked string so it can be used by _lemmatize().
        To make this function work correctly, every sentence must be on a new line, 
        and the word must at the first position and the part-of-speech tag must be at 
        the second position of the slash-formatted token.
        - input: Draw/VB/I-VP/O/VP-1 a/DT/I-NP/O/NP-OBJ-1 red/JJ/I-NP/O/NP-OBJ-1 car/NN/I-NP/O/NP-OBJ-1 ././O/O/O
        - output:
          Draw	    VB
          a         DT
          red	    JJ
          car       NN
          .	        .
    """
    s = string.replace('\n', ' <utt>\n') # Lemmatizer assumes sentences are delimited with <utt>.
    tabbed = ''
    for word in s.split():
        tabbed += '\t'.join(word.split('/')[0:2]) + '\n' # Draw/VB/I-VP/O/VP-1 => Draw  VB
    return tabbed
    
def _lemmatize(string):
    """ Returns the lemmata from the output of _lemmatize_prepare() using MBLEM.
        MBLEM is a local lexicon of lemmata.
        MBLEM will also contact the TiMBL lemma server for extra information
        (server is assumed to be up and running).
        - input:
          Draw	    VB
          a         DT
          red	    JJ
          car       NN
          .	        .
        - output:
          Draw  	VB	draw
          a	        DT	a
          red	    JJ	red
          car	    NN	car
          .	        .	.
    """
    # Create a temporary file with the input string.
    f, fname = tempfile.mkstemp()
    os.write(f, string)
    os.close(f)
    # Contact the MBLEM lemmatizer.
    # MBLEM will read the temporary file and create a new file with its answer.
    pipe([LEMMATIZER, fname,
        str(HOSTS['lemma']),
        str(PORTS['lemma']),
        os.path.join(MODELS, 'em.lex'),
        os.path.join(MODELS, 'em_mblem.transtable')
    ])
    out = open(fname+'.tl').read()
    os.remove(fname)
    os.remove(fname+'.tl')
    return out

def _lemmatize_merge(string, lemmata):
    """ Combines the output of _find_relations() and _lemmatize() into one slash formatted string,
        with every sentence on a newline.
        - string:
          Draw/VB/I-VP/O/VP-1 a/DT/I-NP/O/NP-OBJ-1 red/JJ/I-NP/O/NP-OBJ-1 car/NN/I-NP/O/NP-OBJ-1 ././O/O/O
        - lemmata:
          Draw  	VB	draw
          a	        DT	a
          red	    JJ	red
          car	    NN	car
          .	        .	.
        - output:
          Make/VB/I-VP/O/VP-1/make a/DT/I-NP/O/NP-OBJ-1/a 
          red/JJ/I-NP/O/NP-OBJ-1/red car/NN/I-NP/O/NP-OBJ-1/car ././O/O/O/.
    """
    string = string.split('\n')
    lemmata = lemmata.split('<utt>\n')
    assert len(string) == len(lemmata)
    sentences = []
    for i, sentence in enumerate(string):
        words = sentence.split()
        lemma = lemmata[i].strip().split('\n')
        lemma = [_lemmatizer_exceptions.get(x,x) for x in lemma]
        assert len(words) == len(lemma) # Something is wrong in mbsp.py source code if this occurs.
        s = []
        for j, word in enumerate(words):
            s.append('%s/%s' % (word, lemma[j].split('\t')[-1]))
        sentences.append(' '.join(s))
    return '\n'.join(sentences)       

#--- PARSER ------------------------------------------------------------------------------------------

def _handle_event(name, string, format, language="en"):
    # The events.parser dict in config.py defines functions to run after a specific job in the parser.
    # This way, users can customize the parser from the outside.
    # If the given event name (e.g. "on_lemmatize") is not None, 
    # its associated function is applied to the current slash-formatted string in the parser.
    # Before the string is passed to the event, it is prepared as a TokenString,
    # with the token tags that have been parsed so far.
    handler = config.events.get("parser", {}).get(name, None)
    if handler is not None:
        a = TokenString(string, tags=format, language=language)
        b = handler(a)
        # The parse() function is very strict about the tags it needs and what order they are in.
        # Tags can be edited, but not swapped / removed / extended.
        assert a.tags == b.tags, \
            "Event 'parser.%s' changed tag order or deleted tags that are needed by the parser" % name
        return b
    return string

def parse(string, tokenize=True, tags=True, chunks=True, relations=True, anchors=True, lemmata=True, encoding=config.encoding):
    """ Takes a string of sentences and returns a tagged Unicode string. 
        Sentences in the output are separated by newline characters. 
        The input must be a unicode object. If it is a string it will be decoded using config.encoding.
        - tokenize     : if False no tokenization is carried out (the input must be tokenized already).
        - tags         : if False doesn't add the part-of-speech tags  (e.g. NN) to the output.
        - chunks       : if False doesn't add the chunk (e.g. NP) and PNP tags to the output.
        - relations    : if False doesn't search for relations (-SBJ etc.)
        - anchors      : if False doesn't search for PNP anchors.
        - lemmata      : if False doesn't search for lemmata.
        - encoding     : encoding used to decode the input.
    """
    # We expect to start from unicode input. Decode the byte string if needed.
    # An exception is raised otherwise.
    if isinstance(string, str):
        s = string.decode(encoding)
    elif isinstance(string, unicode):
        s = string
    else:
        raise TypeError('input string must be a string or unicode')
    # Disable options for which the servers are missing.
    # The chunk server should always be running.
    if 'lemma' not in HOSTS:
        lemmata = False
    if 'relation' not in HOSTS:
        relations = False
    if 'preposition' not in HOSTS:
        anchors = False
    # Construct the format of a token in the parsed output.
    # Knowing the format allows a Sentence (see tree.py) to figure out the order of the tags.
    # Trees are used to find preposition anchors, for example.
    format = [WORD]
    if tags      : format.append(POS)
    if chunks    : format.extend((CHUNK, PNP))
    if relations : format.append(REL)
    if anchors   : format.append(ANCHOR)
    if lemmata   : format.append(LEMMA)
    # Normalize whitespace.
    s = ' '.join(s.strip().split())
    if s.strip() == "": 
        return TokenString(u"")
    # Try to load from cache before contacting the servers.
    # The cache key is the input string and all the function settings.
    # If we ever did a full parse of the string (i.e. all parameters = True) that can be reused as well.
    k1 = s + "".join((str(p) for p in (tokenize, tags, chunks, relations, anchors, lemmata, encoding)))
    if k1 in cache:
        return cache[k1]
    k2 = s + "True"*6 + config.encoding
    if k2 in cache:
        s = cache[k2]
        s = TokenString(s).split() # Remove the tags from the full parse we don't need this time.
        for tag in list(s.tags):   # Copy TokenList.tags as it will change after TokenList.remove().
            if not tag in format: s.tags.remove(tag)
        return s.join()
    # Tokenize if asked for.
    if tokenize:
        # Below are the calls needed to contact the Perl implementation of the tokenizer.
        # tokenize.pl can't handle unicode accents very well so split them.
        # Make sure we pass a utf-8 bytestring to tokenize.pl.
        #s = split_unicode_accents(s) 
        #s = s.encode('utf-8')
        #s = _perl_tokenize(s)
        #s = _perl_format(s)
        #s = '\n'.join(s)
        #s = s.decode("utf-8")
        f = [WORD]
        s = _tokenize(s)
        s = _handle_event("on_tokenize", s, format=f)
    # Encode as a Python byte string.
    # The MBT and TiMBL clients communicate with socket.send(), which is an octet (byte) stream.
    s = encode_entities(s)
    s = s.encode("utf-8")
    # Tag for part-of-speech tags and chunks.
    if tags or chunks or relations or anchors or lemmata:
        f = [WORD, POS, CHUNK]
        s = _chunk(s)
        s = _handle_event("on_parse_tags_and_chunks", s, format=f)
    # Find PNP chunks.
    if chunks or relations or anchors:
        f = [WORD, POS, CHUNK, PNP]
        s = _find_prepositions(s)
        s = _handle_event("on_parse_prepositions", s, format=f)
    # Find relations.
    if relations:
        f = [WORD, POS, CHUNK, PNP, REL]
        s = _find_relations(s)
        s = _handle_event("on_parse_relations", s, format=f)
    # Find lemmata.
    if lemmata or anchors:
        f = [WORD, POS, CHUNK, PNP] + (relations and [REL] or []) + [LEMMA]
        s = _lemmatize_merge(s, _lemmatize(_lemmatize_prepare(s)))
        s = _handle_event("on_lemmatize", s, format=f)
    # Find PP anchors.
    if anchors:
        f = [WORD, POS, CHUNK, PNP] + (relations and [REL] or []) + [LEMMA, ANCHOR]
        s = _find_pp_attachments(s, format=f)
        s = _handle_event("on_parse_pp_attachments", s, format=f)
    # Tag juggling.
    # 1) The parsed string is more readable if the lemmata is at the back,
    #    but we need the lemmata to find PNP anchors (works 5x faster than using the word),
    #    so the order of these tags needs to be swapped.
    # 2) Remove tags that were parsed but weren't asked for.
    #    For relations and preposition we always need the chunk and PNP tags, 
    #    for lemmata the part-of-speech tags, but we need to remove these if tags=False or chunks=False.
    if len(format) > 1 and (not tags or not chunks or not lemmata or anchors):
        s = [[t.split('/') for t in s.split(" ")] for s in s.split('\n')]
        def __pop(s, i): 
            for sentence in s: 
                for token in sentence: 
                    del token[i]
        def __swap(s, i, j):
            for sentence in s: 
                for token in sentence: 
                    token[i], token[j] = token[j], token[i]
        if anchors and lemmata:
            __swap(s, -2, -1) # Move lemmata tags to the back of the token.
        if anchors and not lemmata:
            __pop(s, -2) # Remove lemmata.
        if not chunks and (relations or anchors):
            __pop(s, 3)  # Remove PNP tags.
        if not chunks:
            __pop(s, 2)  # Remove chunk tags.
        if not tags:
            __pop(s, 1)  # Remove part-of-speech tags.
        s = '\n'.join([" ".join(["/".join(t) for t in s]) for s in s])
    # Return a splitable unicode TokenString that stores all the tags that were parsed.
    # Store the tagged string in the cache.
    s = s.strip()
    s = decode_entities(s, slashes=False)
    s = s.decode('utf-8')
    s = TokenString(s, format, language="en")
    cache[k1] = s
    return s

#### TOKEN STRING #####################################################################################
# Facilitates conversion between slash-formatted string and list of tokens.
# The purpose of TokenString is to bundle the tagged string with a tag representation,
# The purpose of TokenList is to facilitate tag juggling in tokens when extending the parser.

TOKENS = "tokens"

class TokenString(unicode):
    
    def __new__(self, string, tags=[WORD], language="en"):
        """ The output of the parse() function is a unicode string,
            in which each sentence appears on a new line,
            and the tags in a token are separated with a slash ("/").
        """
        if isinstance(string, TokenString): 
            tags, language = string.tags, string.language
        s = unicode.__new__(self, string)
        s._tags = list(tags)
        s.language = language
        return s

    @property
    def tags(self):
        return list(self._tags) # Return a copy, tags list on a TokenString can't be edited.

    @property
    def tokens(self):
        """ Returns a list of sentences. Each item in a sentence (a token) is a list of tags.
            The order of the tags in a token can be retrieved from TokenString.tags.
        """
        f = lambda token: [decode_entities(tag, slashes=True) for tag in token.split("/")]
        s = [[f(token) for token in sentence.split(" ")] for sentence in self.split("\n")]
        return TokenList(s, self._tags, self.language)

    def split(self, sep=TOKENS):
        return sep == TOKENS and self.tokens or unicode.split(self, sep)

    def copy(self):
        return TokenString(self, self.tags, self.language)

    def __str__(self):
        return self.encode("utf-8")
            
#--- TOKEN LIST --------------------------------------------------------------------------------------

class TokenList(list):
    
    def __init__(self, sentences, tags, language="en"):
        """ The output of TokenString.tokens is a list of sentences. 
            Each item in a sentence (a token) is a list of tags.
            The order of the tags in a token can be retrieved from TokenList.tags.
        """
        if isinstance(sentences, TokenList): tags = sentences.tags
        list.__init__(self, [[[tag for tag in token] for token in sentence] for sentence in sentences])
        self.tags = TokenTags(self, tags) # See below; keeps the tags in each token in synch.
        self.language = language

    @property
    def string(self):
        """ Returns a unicode TokenString in which each sentence appears on a new line,
            with the tags in a token separated by a slash ("/").
        """
        f = lambda token: "/".join([encode_entities(tag) for tag in token])
        s = "\n".join([" ".join([f(token) for token in sentence]) for sentence in self])
        return TokenString(s, list(self.tags), self.language)
        
    def join(self):
        return self.string
        
    def filter(self, word=None, tag=None, chunk=None, relation=None, anchor=None, lemma=None):
        """ Returns a list of tokens that match the given tags.
            For example, TokenList.filter(tag="NN*") returns all the nouns in the text.
        """
        m = ((WORD,word), (POS,tag), (CHUNK,chunk), (REL,relation), (ANCHOR,anchor), (LEMMA,lemma))
        m = filter(lambda (k,v): v is not None and k in self.tags, m)
        m = [(self.tags.index(k),v) for k,v in m]
        candidates = []
        for sentence in self:
            for token in sentence:
                if len([False for i,v in m if not _match(v, token[i])]) == 0:
                    candidates.append(token)
        return candidates
        
    def reduce(self, tags=[]):
        """ For each token, remove all but the given tags.
        """
        x = self.copy(); x.tags.reduce(tags); return x
    
    def copy(self):
        return TokenList(self, self.tags, self.language)

def _match(string1, string2):
    """ Returns True if string1 equals string2.
        A wildcard can be used in string1: *tail, head*, *inside*, a*round.
    """
    x = string1.split("*")
    return (len(x) == 1 and string2 == x[0]) \
        or (len(x) == 2 and string2.startswith(x[0]) and string2.endswith(x[1])) \
        or (len(x) == 3 and x[1] in string2)

#--- TOKEN TAGS --------------------------------------------------------------------------------------

class TokenTags(list):
    
    def __init__(self, parent, tags):
        """ The TokenList.tag property, with additional functionality for tag juggling.
            Tags in tokens in the sentences of the parent TokenList are kept in synch.
        """
        list.__init__(self, tags)
        self.parent = parent
    
    def insert(self, index, tag, values=None):
        """ Inserts the given tag at the given position.
            If values is None, inserts "O" in each token in each sentence in the parent TokenList.
            If values is given, it is a list of lists (one for each sentence) of values
            (one tag value for each token in each list).
        """
        for i, sentence in enumerate(self.parent):
            for j, token in enumerate(sentence):
                try: v = values and values[i][j] or "O"
                except IndexError:
                    raise IndexError, "TokenList.tags.insert(index, tag, values): wrong number of values"
                token.insert(index, v) 
        list.insert(self, index, tag)

    def append(self, tag, values=None):
        try: self.insert(len(self), tag, values)
        except IndexError:
            raise IndexError, "TokenList.tags.append(tag, values): wrong number of values"
    
    def extend(self, tags, values=None):
        # We can't disambiguate the format of the nested lists in the values parameter.
        raise AttributeError, "'TokenList' object has no attribute 'extend'"

    def __delitem__(self, index):
        # Delete the tag at given index from each token in each sentence.
        for i, sentence in enumerate(self.parent):
            self.parent[i] = [token[:index]+token[index+1:] for token in sentence]
        list.__delitem__(self, index)

    def remove(self, tag):
        """ Removes the given tag from the list.
            Removes the given tag from each token in each sentence in the parent TokenList.
        """
        try: i = self.index(tag)
        except:
            raise ValueError, "TokenList.tags.remove(x): x not in list"
        self.__delitem__(i)
    
    def pop(self, i):
        """ Removes the tag at the given index from the list.
            Returns the tag value for each token tag in each sentence.
            This is a list of lists than can be passed as values parameter in TokenList.insert().
        """
        values = [[token[i] for token in sentence] for sentence in self.parent]
        self.__delitem__(i)
        return values

    def reduce(self, tags=[]):
        """ Removes all tags except those given from the list.
            Removes all tags except those given from each token in each sentence in the parent TokenList.
        """
        indices = [self.index(tag) for tag in tags]
        for i, sentence in enumerate(self.parent):
            for j, token in enumerate(sentence):
                self.parent[i][j] = [token[x] for x in indices]
        [list.pop(self, x) for x in reversed(range(len(self))) if x not in indices]

    def swap(self, tag1, tag2):
        """ Swaps tag1 and tag2 in the list.
            Swaps tag1 and tag2 in each token in each sentence in the parent TokenList.
        """
        if not tag1 in self: raise ValueError, "TokenList.tags.swap(x,y): x not in list"
        if not tag2 in self: raise ValueError, "TokenList.tags.swap(x,y): y not in list"
        i = self.index(tag1)
        j = self.index(tag2)
        for sentence in self.parent:
            for token in sentence:
                token[i], token[j] = token[j], token[i]
        self[i], self[j] = tag2, tag1
    
    def sort(self):
        for i, sentence in enumerate(self.parent):
            sentence = [list(enumerate(token)) for token in sentence]
            sentence = [sorted(token, key=lambda x: self[x[0]]) for token in sentence]
            sentence = [[x[1] for x in token] for token in sentence]
            self.parent[i] = sentence
        list.sort(self)
    
    def reverse(self):
        for i, sentence in enumerate(self.parent):
            self.parent[i] = [reversed(token) for token in sentence]
        list.reverse(self)

#######################################################################################################
# A few handy commands based on the parse() command.

def tokenize(string, encoding=config.encoding):
    """ Tokenizes the string by separating sentences with a new line and splitting punctuation from words.
    """
    return parse(string,
       tokenize = True,
           tags = False,
         chunks = False,
      relations = False,
        anchors = False,
        lemmata = False,
       encoding = encoding)

def tag(string, tokenize=True, lemmata=False, encoding=config.encoding):
    """ Tokenizes the string and adds the part-of-speech tags.
    """
    return parse(string,
       tokenize = tokenize,
           tags = True,
         chunks = False,
      relations = False,
        anchors = False,
        lemmata = lemmata,
       encoding = encoding)
    
def chunk(string, tokenize=True, lemmata=False, encoding=config.encoding):
    """ Tokenizes the string and adds the part-of-speech and chunk tags.
    """
    return parse(string, 
       tokenize = tokenize,
           tags = True,
         chunks = True,
      relations = False,
        anchors = False,
        lemmata = lemmata,
       encoding = encoding)
    
def lemma(word, encoding=config.encoding):
    """ Returns the lemma of the word.
    """
    return parse(word,
       tokenize = False,
           tags = False,
         chunks = False,
      relations = False,
        anchors = False,
        lemmata = True,
       encoding = encoding).split("/")[-1]
       
def lemmatize(string, tokenize=True, encoding=config.encoding):
    """ Returns the string with all words lemmatized.
    """
    return parse(string,
       tokenize = tokenize,
           tags = False,
         chunks = False,
      relations = False,
        anchors = False,
        lemmata = True,
       encoding = encoding).split().reduce([LEMMA]).join()

def nouns(string, lemmatize=False, encoding=config.encoding):
    return [t[lemmata and -1 or 0] for t in chunk(string, lemmatize, encoding).split().filter(tag="NN*")]

def adjectives(string, lemmatize=False, encoding=config.encoding):
    return [t[lemmata and -1 or 0] for t in chunk(string, lemmatize, encoding).split().filter(tag="JJ*")]
    
def verbs(string, lemmatize=False, encoding=config.encoding):
    return [t[lemmata and -1 or 0] for t in chunk(string, lemmatize, encoding).split().filter(tag="VB*")]

#### COMMAND LINE #####################################################################################
# Command line interface for MBSP.
# Since mbsp.py is called directly, the servers will not start automatically.
# >>> cd MBSP
# >>> python mbsp.py start
# >>> python mbsp.py parse -f camelot.txt
# >>> python mbsp.py parse -s "It's only a model."
# >>> python mbsp.py parse xml -s "It is a silly place."
# >>> python mbsp.py stop
#
# Options:
# If no options are given a full parse (tokenize/tags/chunks/relations/anchors/lemmata) will happen.
# Otherwise, you need to explicitly list everything you want.
# -O --tokenize  : tokenize the input
# -T --tags      : parse part-of-speech tags
# -C --chunks    : parse chunk and PNP tags
# -R --relations : find verb/predicate relations.
# -A --anchors   : find PP-attachments.
# -L --lemmata   : find word lemmata.
# -e --encoding  : specify character encoding (utf-8 by default).
# -v --version   : current version of MBSP.
# Options can be concatenated, e.g. -OTL

def main():

    import optparse

    p = optparse.OptionParser()
    p.add_option("-f", "--file", dest="file", action="store", help="text file to parse", metavar="FILE")
    p.add_option("-s", "--string", dest="string", action="store", help="text string to parse", metavar="STRING")
    p.add_option("-O", "--tokenize", dest="tokenize", action="store_true", help="tokenize the input")
    p.add_option("-T", "--tags", dest="tags", action="store_true", help="parse part-of-speech tags")
    p.add_option("-C", "--chunks", dest="chunks", action="store_true", help="parse chunk tags")
    p.add_option("-R", "--relations", dest="relations", action="store_true", help="find verb/predicate relations")
    p.add_option("-P", "--anchors", dest="anchors", action="store_true", help="find PP-attachments")
    p.add_option("-L", "--lemmata", dest="lemmata", action="store_true", help="find word lemmata")
    p.add_option("-e", "--encoding", dest="encoding", action="store_true", default="utf-8", help="character encoding")
    p.add_option("-v", "--version", dest="version", action="store_true", help="version info")
    options, arguments = p.parse_args()

    # Either a text file (-f) or a text string (-s) must be supplied.
    sentences = options.string
    if options.file:
        import codecs
        sentences = codecs.open(options.file, "r", options.encoding).read()

    # The servers need to be started before anything can be parsed.
    # Otherwise, a ServerConnectionError will be raised.
    if "start" in arguments:
        import server
        server.servers.start()
    
    # Just for decorational purposes:
    if "parse" in arguments:
        pass

    # The given text can be parsed in two modes: 
    # - implicit: parse everything (tokenize, tag/chunk, find relations and anchors, lemmatize).
    # - explicit: define what to parse manually.
    if sentences:
        explicit = False
        for option in [
            options.tokenize, 
            options.tags, 
            options.chunks, 
            options.relations, 
            options.anchors, 
            options.lemmata]:
            if option is not None: explicit = True; break
        if explicit:
            attributes = {
                "tokenize" : options.tokenize or False,
                    "tags" : options.tags or False,
                  "chunks" : options.chunks or False,
               "relations" : options.relations or False,
                 "anchors" : options.anchors or False,
                 "lemmata" : options.lemmata or False,
                "encoding" : options.encoding
            }
        else:
            attributes = {"encoding": options.encoding}
            
        # If a ServerConnectionError occurs,
        # this likely means the servers need to be started first.
        # We can start them automatically if config.autostart=True.
        try:
            s = parse(sentences, **attributes)
        except client.ServerConnectionError:
            if config.autostart:
                import server
                server.servers.start()
                s = parse(sentences, **attributes)
            else:
                raise server.ServerError("the servers have not been started")
        
        # The output can be either slash-formatted string or XML.
        # If it is XML, we need to deduct the token format from the options
        # (e.g. does a token include relation tag, anchor tag, ...)
        if "xml" in arguments:
            from tree import Text
            s = Text(s, s.tags).xml
        
        print s
    
    # Kill the server processes.
    # This happens when explicitly requested by the user or when config.autostop=True.
    if "stop" in arguments or config.autostop:
        import server
        server.servers.stop()
    
    # Version info.
    if options.version:
        from __init__ import __version__
        print __version__
    
if __name__ == "__main__":
    main()
