#### MEMORY-BASED SHALLOW PARSER ######################################################################

# Copyright (c) 2003-2010 University of Antwerp, Belgium and Tilburg University, The Netherlands
# Vincent Van Asch <vincent.vanasch@ua.ac.be>, Tom De Smedt <tom@organisms.be>
# License: GNU General Public License, see LICENSE.txt

### RELATION FINDER ##################################################################################
# MBSP's first step is to find the role of each word in the sentence, 
# then to find groups ("chunks") of words that belong together, 
# then to find relations between the different groups.
# The relation finder retrieves relations in the verb-argument structure (verb, object, subject, ...)
#
# This is a substitute for the Perl relation finder (relfinder.pl)
# The updated substitute makes it possible:
# - to tag ADJP-PRD's,
# - to use sentence splitting.
#
# Takes a PNP sentence:
# Make/VB/I-VP/O  an/DT/I-NP/O  oval/NN/I-NP/O  ././O/O
# and returns a REL sentence:
# Make/VB/I-VP/O/VP-1  an/DT/I-NP/O/NP-OBJ-1  oval/NN/I-NP/O/NP-OBJ-1  ././O/O
#
# RELFINDER.PL changes: 
# The known differences with relfinder.pl when composing feature vectors (instances) are:
# - commas stay commas in the instances (like in the instancebase) and are not substituted with COMMA,
# - commas are counted when computing the distance of a focus word to a verb,
# - there is no maximum distance. In relfinder.pl instances with a distance above a certaine threshold
#   are not retained.

import re
import config
import client

try:
    HOST = config.hosts[config.servers.index('relation')] # Relation server host (e.g. localhost).
    PORT = config.ports[config.servers.index('relation')] # Relation server port.
except:
    HOST = ''
    PORT = 0

#--- SPLIT TOKENS ------------------------------------------------------------------------------------

def _split(tagged_string):
    """ Takes a PNP-tagged sentence and splits tokens into a list.
        Tokens in the input string must contain word, part-of-speech, chunk and preposition tags.
        For example: "Make/VB/I-VP/O  an/DT/I-NP/O  oval/NN/I-NP/O  ././O/O"
        yields [[Make, VB, I-VP, O] ,  [an, DT, I-NP, O] , [oval, NN, I-NP, O] , [., ., O, O]]
        - token[0] = the word,
        - token[1] = the part-of-speech tag,
        - token[2] = the chunk tag,
        - token[3] = the PNP tag,
        - token[4] = original index
    """
    # Make all spaces singular.
    # Remove leading and trailing whitespace.
    s = re.sub(' +', ' ', tagged_string)
    s = s.strip()
    # Split every token into tags and append its index in the original sentence:
    T = []
    for i, token in enumerate(s.split(' ')):
        tags = token.split('/') + [i]
        if len(tags) != 5:
            # We end up here if a token is missing pos/chunk/pnp tags.
            s = 'Input of _split() is not a well-formed PNP sentence (expected WORD/POS/CHUNK/PNP tags).'
            raise Exception, s
        T.append(tags)
    return T
    
def _join(s):
    """ Converts a list of tokens from _split() back into a sentence string.
    """
    return " ".join(['/'.join(token) for token in s])

#--- STEP 1 ------------------------------------------------------------------------------------------
# Step 1 collects indices of useful words to create TiMBL lookup instances with.

def _collapse(token, map={'O':'-'}):
    """ Returns the token without I/B chunk tag prefixes, e.g. B-NP => NP.
        Chunk tags are then replaced using the given map (by default, O becomes '-').
    """
    ch = token[2].split('-')[-1]
    ch = map.get(ch, ch)
    return [token[0], token[1], ch, token[3], token[4]]    

def _np_pnp(token):
    """ Returns the token without I/B chunk tag prefixes, and replaced PNP.
    """
    if token[3] != 'O':
        return [token[0], token[1], 'PNP', token[3], token[4]]
    else:
        return _collapse(token)

def _step1(s):
    """ Iterates the list of tokens from _split() and returns a reduced representation of the sentence.
        Returns a tuple with:
        1) A list of indices of verbs in the sentence. Only verb phrase heads are included.
        2) A list of indices of commas in the sentence.
        3) A list of indices. For each word, the chunk head index of the chunk this word belongs to.
        4) A list of tokens that must be taken into account when constructing the feature vectors.
           This roughly corresponds to the chunk heads.
        5) A list of indices. For each word, either -1 if the word is not represented
           in list 4) or otherwise the index of the token in 4).
        6) A list of indices of the tokens for which an instance must be made.
        7) For each word, the list contains either '' (not in any verb chunk) or an integer
           indicating that the word is in the nth verb phrase.
    """            #                                       Example: "Hello , my name is Inigo Montoya ."
    verbs     = [] # 1) A list of indices of verbs in the sentence.  [4]
    commas    = [] # 2) A list of indices of commas in the sentence. [1]
    chunks    = [] # 3) A list of indices of the chunk heads.        [0, 1, 3, 3, 4, 6, 6, 7]
    heads     = [] # 4) A list of split tokens that are chunk heads. [[',', ',', '-', 'O', 1], ['name', ...]]
    indices   = [] # 5) The index of the token in heads.             [-1, 0, -1, 1, 2, -1, 3, -1]
    instances = [] # 6) Words for which an instance must be made.    [3, 6]
    VP_chunks = [] # 7) Word belongs to the how-manieth verb phrase? ['', '', '', '', 1, '', '']
    VP_start  = True
    VP_count  = 0
    VB        = ('VB','VBZ','VBD','VBN','VBG','VBP')
    ch, prev  = [], ' '
    
    for i, token in enumerate(s):
        # 1) Collect verb indices.
        #    Only take the verb phrase heads (i.e. the last verb in the verb phrase).
        if token[2] == 'I-VP' and token[1] in VB:
            b, j = True, i+1
            while j < len(s) and s[j][2] == 'I-VP':
                if s[j][1] in VB: b = False; break
                j += 1
            if b:
                verbs.append(i)
        # 2) Collect comma indices.
        if token[0] == ',':
            commas.append(i)
        # 3) Collect chunk head indices.
        #    We are inside a chunk or PNP when: I-NP + I-NP, B-NP + I-NP or I-PP + I-NP.
        if token[2] == prev and token[2] != 'O' \
        or token[2][0] == 'I' and prev[0] == 'B' and token[2][2:] == prev[2:] \
        or token[2] == 'I-NP' and prev =='I-PP':
            ch.append(i)
        else:
            if ch: chunks.extend([ch[-1]] * len(ch))
            ch = [i]
        prev = token[2]
        # 4) Collect the tokens that must be taken into account when constructing the feature vectors.
        #    This roughly corresponds to the chunk heads:
        #    - nouns, but only the last one in a NP,
        #    - adjectives (cpm, sup), but only the last one of the ADJP chunk, and not inside a PNP,
        #    - verbs, but only the heads and inside a VP,
        #    - coordinators, personal pronouns, what, punctuation,
        #    - adverbs as long as they are not in a NP,
        #    - That + numbers, but only if the last one in a NP.
        # Collapse I/B and replace "NP" chunk tag with "PNP".
        head_index = -1
        is_head = (i+1 == len(s) or s[i+1][2] != 'I-NP') # head = the last token in NP chunk
        if token[1].startswith('N') and is_head \
        or token[1].startswith('J') and is_head and token[2] in ('I-ADJP',) and token[3] == 'O' \
        or token[1].startswith('V') and token[4] in verbs \
        or token[1] in ('CC', 'PRP', 'WP', ',', '"') \
        or token[1] in ('RB', 'RBR') and token[2] not in ('B-NP', 'I-NP') \
        or token[1] in ('CD', 'WDT') and is_head:
            heads.append(_np_pnp(token)) # Rewrite NP tag to PNP tag.
            head_index = len(heads)-1
        # 5) Collect references to the heads list in 4).
        #    Contains -1 if the word is not represented in heads,
        #    the index of the token in heads otherwise.
        indices.append(head_index)
        # 6) Collect indices of words for which to create instances.
        if token[1] in ('NN', 'NNS', 'NNP', 'NNPS', 'PRP', 'WP', 'WDT', 'CD') and is_head \
        or token[1] in ('JJ', 'JJR', 'JJS') and token[2] in ('I-ADJP',):
            instances.append(i)      
        # 7) Collect VP ordinals.
        #    For each word, the list contains either '' (not in any verb chunk) or an integer
        #    indicating that the word is in the nth verb phrase.
        if token[2] == 'I-VP':
            if VP_start:
                VP_chunks.append(VP_count+1); VP_count+=1; VP_start=False 
            else:
                VP_chunks.append(VP_count)
        else:
            VP_chunks.append(''); VP_start=True
    # Process the last pending chunk for step 3).
    if ch not in chunks:
        chunks.extend([ch[-1]] * len(ch))
    return (verbs, commas, chunks, heads, indices, instances, VP_chunks)

#--- STEP 2 ------------------------------------------------------------------------------------------
# Step 2 collects distances between verbs and other words (specifically commas and other verbs).

def _step2(verbs, commas, chunks, sentence_length):
    """ Returns a (distance, comma, verb)-tuple of dictionaries.
        The keys of each dictionary are the verb indices.
        For each sentence word you can then look up the number of commas between the word and a verb.
        For example: "Hello , my name is Inigo Montoya ."
          { 4: [-3, -2, -1, -1, 0, 1, 1, 2] } => The distance between "hello" and "is" is -3 (3 before).
          { 4: [1, '-', 0, 0, '-', 0, 0, 0] } => There is one comma between "hello" and "is".
          { 4: [0, 0, 0, 0, '-', 0, 0, 0]   } => There are no verbs between "hello" and "is".
        The given parameters verbs, commas, chunks can be acquired from _step1().
    """
    distance = {} # 1) Distance from verb to word.
    comma    = {} # 2) Number of commas between verb and word.
    verb     = {} # 3) Number of verbs between verb and word.
    
    for i in verbs:
        # 1) Distance from verb to each other word.
        D = [0]
        if i != len(chunks)-1: 
            n, prev = 0, ''
            for j in range(i+1, len(chunks)): # Traverse words after the verb.
                if chunks[j] != prev:
                    D.append(n+1); n+=1; prev=chunks[j]
                else:
                    D.append(n)
        if i != 0:             
            n, prev = 0, chunks[i]
            for j in reversed(range(0,i)):    # Traverse words in front of verb.
                if chunks[j] != prev:
                    D.insert(0, -1*(n+1)); n+=1; prev=chunks[j]
                else:
                    D.insert(0, -1*n)
        distance[i] = D
        # 2) Number of commas between verb and word.
        C = ['-']
        V = ['-']
        nc, nv = 0, 0 # comma/verb count
        for j in range(i+1, sentence_length): # Traverse words after verb.
            if j in commas:
                C.append('-'); nc+=1
            elif j in verbs:
                C.append('-')
            else:
                C.append(nc)
            if j in verbs:
                V.append('-'); nv+=1
            else:
                V.append(nv)
        nc, nv = 0, 0
        for j in reversed(range(0,i)):        # Traverse words in front of verb.
            if j in commas:
                C.insert(0,'-'); nc +=1
            elif j in verbs:
                C.insert(0,'-')
            else:
                C.insert(0,nc)
            if j in verbs:
                V.insert(0,'-'); nv+=1
            else:
                V.insert(0,nv)
        comma[i] = C
        verb[i] = V
    return (distance, comma, verb)

#--- REL INSTANCES -----------------------------------------------------------------------------------

def _instances(index, distance, verbs, verb_map, comma_map, heads, head_index, sentence):
    """ Makes lookup instances of the token at index for the relation server.
        Returns a tuple of two lists (instances, indices of verb).
        An instance looks like:
        distance, VC, comma, verb, verb_pos, -2 word, -2 pos, -2 chunk, -1 word, -1 pos, -1 chunk, f prep, f word, f pos, f chunk, +1 pos, +1 chunk  ?
        0         1   2      3     4            5        6       7         8        9       10       11      12      13     14        15      16     17
    """
    def _tag(position, index, verb_index):
        # Yields token[index] tag for the token at the given position.
        i = head_index + position
        if 0 <= i < len(heads):
            if heads[head_index][4] < verb_index:
                return heads[i][index]
            elif heads[i][4] < verb_index:
                return '-'
            else:
                return heads[i][index]
        return '-'
    # Make an instance for every verb.
    instances = []
    indices = []
    for i in verbs:
        instance = ['-']*17 + ['?']
        instance[0]  = str(distance[i][index])  # Distance.
        instance[1]  = str(verb_map[i][index])  # Verb count.
        instance[2]  = str(comma_map[i][index]) # Comma.
        instance[3]  = sentence[i][0].lower()   # Verb.
        instance[4]  = sentence[i][1]           # Verb part-of-speech.
        instance[5]  = _tag(-2,0,i) # The word before the previous.
        instance[6]  = _tag(-2,1,i) # The word before the previous, part-of-speech.
        instance[7]  = _tag(-2,2,i) # The word before the previous, chunk tag.
        instance[8]  = _tag(-1,0,i) # Previous word.
        instance[9]  = _tag(-1,1,i) # Previous word's part-of-speech
        instance[10] = _tag(-1,2,i) # Previous word's chunk tag.
        instance[11] = '-'          # Focus preposition - XXX This should be implemented.
        instance[12] = _tag(0,0,i)  # Focus word.
        instance[13] = _tag(0,1,i)  # Focus word's part-of-speech.
        instance[14] = _tag(0,2,i)  # Focus word's chunk tag.
        instance[15] = _tag(1,1,i)  # Next word's part-of-speech.
        instance[16] = _tag(1,2,i)  # Next word's chunk tag.
        instances.append(' '.join(instance))
        indices.append(i)
    return (instances, indices)

#--- TAG ---------------------------------------------------------------------------------------------

def tag(tagged_string):
    """ Takes a PNP-tagged sentence and returns a tagged sentence with the added relation tags.
        Tokens in the input string must contain WORD, POS, CHUNK and PNP tags.
        Example relation tags: NP-SBJ-1, VP-1, NP-OBJ-1, NP-SBJ-2, ADJP-CLR, ... (see tags.py)
        Note 1: on rare occasions words can be tagged with multiple relations (e.g. NP-OBJ-1*NP-OBJ-3).
        Note 2: the separator for multiple relation can be "*" OR ";".
    """
    s = _split(tagged_string)
    verbs, commas, chunks, heads, indices, instance_candidates, VP_chunks = _step1(s)
    distance, comma_map, verb_map = _step2(verbs, commas, chunks, len(s))
    tags = []
    V = [] # Verb indices collected from _instance().
    I = [] # Instance index per tag.
    for i in instance_candidates:
        instances, verb_indices = _instances(i, distance, verbs, verb_map, comma_map, heads, indices[i], s)
        instances = [x.replace('/','*') for x in instances]
        tags.extend(instances)
        V.extend(verb_indices)
        I.extend([i] * len(instances))
    # The client.batch() function in the client module takes care of managing server clients,
    # we simply pass it all the tagging jobs and a definition of the client we need.
    tags = client.batch(tags, client=(client.Timbl, HOST, PORT, config.RELATION, config.log), retries=1)    
    # Getting tags for complete chunks:
    chunk_dict = {}
    for i, tag in enumerate(tags):
        ch = chunks[I[i]]
        vp = str(VP_chunks[V[i]])
        if tag != '-':
            if ch in chunk_dict.keys():
                new_tag = '-'.join([tag, vp])
                # Do not append a tag referencing to the same verb twice.
                # Taking the first occurence:
                new_tag_vp = new_tag.split('-')[-1]
                linked_vps = [x.split('-')[-1] for x in chunk_dict[ch].split('*')]
                if new_tag_vp not in linked_vps:
                    chunk_dict[ch] += '*' + new_tag
            else:
                chunk_dict[ch] = '-'.join([tag, vp])
    # Collect NP-SBJ, NP-OBJ etc. relations and add the VP relations.
    # Place the relation tags in the sentence.
    relations = []
    for i, chunk in enumerate(chunks):
        if chunk in chunk_dict:
            relations.append(chunk_dict[chunk])
        elif VP_chunks[i]:
            relations.append('VP-%d' % (VP_chunks[i]))
        else:
            relations.append('O')
    for i in range(len(s)):
        s[i][4] = relations[i]
    return _join(s)
