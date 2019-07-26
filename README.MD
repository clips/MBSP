
MBSP is a text analysis system based on the
[TiMBL](http://ilk.uvt.nl/timbl/) and [MBT](http://ilk.uvt.nl/mbt/)
memory based learning applications developed at CLiPS and
[ILK](http://ilk.uvt.nl/).
It provides tools for Tokenization and Sentence Splitting, Part of Speech Tagging, Chunking, Lemmatization, Relation Finding and Prepositional Phrase Attachment.
The general English version of MBSP has been trained on data from the Wall Street Journal corpus.

![MBSP\_schema](/media/MBSP_schema.gif)

## Download

<table>
<colgroup>
<col style="width: 33%" />
<col style="width: 33%" />
<col style="width: 33%" />
</colgroup>
<tbody>
<tr class="odd">
<td><a href="/media/MBSP_1.4.zip"><img src="/sites/all/themes/clips/g/download.gif" alt="download" /></a></td>
<td><strong>MBSP for Python (1.4)</strong> | <a href="/media/MBSP_1.4.zip">download</a> (.zip, 24MB)<br />

<ul>
<li>Requires: Python 2.5+ on Unix | Mac | Cygwin.</li>
<li>Licensed under <a href="http://www.gnu.org/licenses/gpl.html">GPL</a></li>
<li>Releases: <a href="/media/MBSP_1.4.zip">1.4</a> | <a href="/media/MBSP_1.3.zip">1.3</a> | <a href="/media/MBSP_1.2.zip">1.2</a> | <a href="/media/MBSP_1.1.zip">1.1</a></li>
<li>Authors:<br />
Vincent Van Asch (<em>vincent.vanasch at uantwerpen.be</em>),<br />
Tom De Smedt (<em>tom at organisms.be</em>)</li>
</ul>
<p><span style="text-decoration: underline;">Reference</span>: Daelemans, W., &amp; Van den Bosch, A. (2005).<br />
<em>Memory-based language processing</em>. Cambridge University Press, Cambridge, UK.<br />
ISBN-13: 9780521808903 | ISBN-10: 0521808901</p>
<p><span class="grey" style="text-decoration: underline;">SHA256</span><span class="grey"> checksum of the .zip:</span><br />
<span class="grey">62be10ece640404058b607d9f15493a2a98d55b7e3a3d9becc6ed5854fa800bc</span> </p></td>
<td><a href="http://twitter.com/share" class="twitter-share-button">Tweet</a></td>
</tr>
</tbody>
</table>

-----

## Documentation

  - [Introduction](#Introduction)
  - [Installation instructions](#installation)
  - [The parser](#parser)
  - [The tokenizer](#tokenizer)
  - [The lemmatizer](#lemmatizer)
  - [The PP-attacher](#pp-attacher)
  - [Parse trees](#tree)
  - [Clients and servers](#server)
  - [Configuration](#configuration)
  - [Command-line interface](#command_line)
  - [Extending MBSP](#customization)
  - [Exporting to XML, NLTK, GraphViz](#export)
  - [Licensing](#license)



-----

## <span id="introduction"></span>Introduction

### Quick overview

MBSP parses a string of characters into words and sentences, and determines the grammatical structure of the sentence.
It is a Python module, so you'll need [Python](http://www.python.org/download/) to run it (already installed on Mac OS X).

The module uses a client-server architecture for performance.
It includes binaries ([TiMBL](http://ilk.uvt.nl/timbl/), [MBT](http://ilk.uvt.nl/mbt/) and [MBLEM](http://ilk.uvt.nl/mbma/)) precompiled for Mac OS X, so on Mac it works out-of-the-box.
Otherwise, if you're on a Unix system, the module has a setup.py file that should compile everything for you. Go to the terminal and type:

```
cd MBSP
python setup.py
```

If that doesn't work you'll need to follow the steps in the [installation instructions](/pages/MBSP#installation).

Put the MBSP folder in the same folder as your Python script and import the module. By default, the servers are configured to start automatically. Once they are up and running you can use the `parse()` command to analyze texts:

```python
import MBSP
print MBSP.parse('cats with hats')
>>> cats/NNS/I-NP/O/O/A1/cat with/IN/I-PP/B-PNP/O/P1/with hats/NNS/I-NP/I-PNP/O/P1/hat
```

Each word has been *tagged* with grammatical information. For example, MBSP determined that *cats* is a plural noun (<span class="postag">NNS</span>). It has a prepositional noun phrase (<span class="postag">PNP</span>) attached to it (<span class="postag">A1</span> is the anchor of <span class="postag">P1</span>), so the *hats* go *with* the *cats*.
For a human this might seem pretty straightforward, but consider that without any analysis, for a machine the sentence is just a sequence of characters with no meaning.

The tag codes may seem cryptic at first, but consider that it is more concise to say <span class="postag">NNS</span> than <span class="postag">PLURAL NOUN</span> over and over.
The tag codes are common in natural language processing, it's a good idea to [get acquainted with them](/pages/MBSP-tags).

Something went wrong? Probably the servers didn't have enough time to start:

```python
MBSP.start(timeout=120)
print(MBSP.parse('cats with hats'))
```

The output of the `parse()` command is a tagged string that can be manipulated in many ways.  
With the `split()` command it can be transformed into a tree of linked Python objects:

```python
s = MBSP.parse('black cats with striped hats')
s = MBSP.split(s)
for sentence in s:
    for chunk in sentence.chunks:
        print([word.lemma for word in chunk.words], chunk.attachments)
>>> [u'black', u'cat'] [Chunk('with striped hats/PNP')]
>>> [u'with'] []
>>> [u'striped', u'hat'] []
```

With the `xml()` command it can be transformed into an [XML](http://en.wikipedia.org/wiki/XML) string for processing outside of Python:

```python
s = parse('black cats with striped hats')
print xml(s)
```

### Purpose

MBSP stands for "Memory-Based Shallow Parser". [Shallow
parsing](/pages/mbsp-shallow-parsing) (i.e. automatic discovery of a
sentence constituents) is an important component of many text analysis
systems, in applications such as information extraction and summary
generation. The Memory-Based Learning (MBL) approach has the advantage
of avoiding the need for manual definition of patterns (for example,
using regular expression syntax) and of being reusable across different
corpora and sublanguages.

MBSP is a so-called *lazy learner*: it keeps all the initial training
data available (including exceptions which may sometimes be productive).
This technique has been shown to achieve higher accuracy than *eager*
(or *greedy*) methods for many language processing tasks. For the Wall
Street Journal corpus (WSJ), accuracy (Fβ=1) is 96.4% for part-of-speech
tagging, 93.8% for <span class="postag">NP</span> chunking, 94.7% for
<span class="postag">VP</span> chunking, 77.1% for
<span class="postag">SBJ</span> detection, 79.0% for
<span class="postag">OBJ</span> detection, and 82.7% for
<span class="postag">PP</span>-attachment. MBSP is based on the IB1-IG
and IGTREE algorithms bundled in our MBL software package, called TiMBL.

<span style="text-decoration: underline;">Reference</span>: Daelemans,
W., Buchholz, S., & Veenstra, J. (1999).    
*Memory-Based Shallow Parsing*. In: Proceedings of CoNLL, Bergen,
Norway.

The parser provides functionality for tokenization and sentence
splitting, part-of-speech tagging, chunking, relation finding,
prepositional phrase attachment and lemmatization.

  - **Tokenization**: splits sentence periods and punctuation marks from
    words.
  - **Tagging**: assigns part-of-speech tags to words (e.g. *cat* → noun
    → <span class="postag">NN</span>, *eat* → verb →
    <span class="postag">VB</span>).
  - **Chunking**: assigns chunk tags to groups of words (e.g. *the black
    cat* → noun phrase → <span class="postag">NP</span>).
  - **Relation finder**: finds relations between chunks, sentence
    subject, object and predicates.
  - **PNP finder**: finds prepositional noun phrases (e.g. *under the
    table*).
  - **PP-attachment**: finds prepositional noun phrase anchors (e.g.
    *eat pizza* → *with fork*).
  - **Lemmatization**: finds word lemmata (e.g. *was* → *be*).

### Grammar basics

Sentences are made up of words. Words have a syntactic role (noun, verb,
adjective, ...) depending on their location in the sentence. For
example, *can* can be a verb or a noun, depending on the context (*the
can*, *I can*).

  - **Sentence**: the basic unit of writing, expected to have a subject
    and a predicate.
  - **Word**: a string of characters that expresses a meaningful
    concept.
  - **Token**: a specific word with grammatical tags: *the
    can*/<span class="postag">NN</span>, *I
    can*/<span class="postag">VB</span>.
  - **Chunk**: a group of words (phrase) that contains a single thought
    (e.g. *a sumptuous banquet*).
  - **Head**: the word that determines the syntactic type of the chunk:
    *the black <span style="text-decoration: underline;">cat</span>* →
    <span class="postag">NP</span>.
  - **Subject**: the person/thing *doing* or *being*, usually a noun
    phrase (<span class="postag">NP</span>):
    *<span style="text-decoration: underline;">the cat</span> is black*.
  - **Predicate**: the remainder of the sentence tells us what the
    subject does: *the cat
    <span style="text-decoration: underline;">sits on the mat</span>*.
  - **Clause**: subject + predicate.
  - **Argument**: a chunk that is related to a verb in a clause, i.e.
    subject and object.
  - **Object**: the person/thing affected by the action: *the cat eats
    <span style="text-decoration: underline;">fish</span>*. Poor fish.
  - **Preposition**: temporal, spatial or logical relationship: *the cat
    sits <span style="text-decoration: underline;">on the mat</span>*.
  - **Copula**: a word used to link subject and predicate, typically the
    verb *to be*.
  - **Lemma**: canonical form of a word: *run*, *runs*, *running* are
    part of a lexeme, *run* is the lemma.
  - **POS**: part-of-speech, the syntactic role that a word or phrase
    plays in a sentence, e.g. adjective =
    <span class="postag">JJ</span>.

### Acknowledgements

This version of MBSP has been developed by the computational linguistics
group of CLiPS (Computational Linguistics & Psycholinguistics,
department of Linguistics, University of Antwerp, Belgium) on the basis
of earlier versions developed at the University of Antwerp and Tilburg
University.

Contributing authors: Walter Daelemans, Jakub Zavrel, Sabine Buchholz,
Jorn Veenstra, Antal van den Bosch, Ko van der Sloot, Bertjan Busser,
Erik F. Tjong Kim Sang, Jo Meyhi, Vincent Van Asch, Tom De Smedt.

For reference you can use:  
<span class="small">De Smedt T., Van Asch V. & Daelemans, W. (2010).
*Memory-based Shallow Parser for Python*.  
CLiPS Technical Report Series (CTRS), vol. 2.
ISSN <span style="border-collapse: collapse;">2033-3544.
\[[PDF](http://www.clips.ua.ac.be/sites/default/files/ctrs-002.pdf)\]</span></span>



-----

## <span id="installation"></span>Installation

MBSP is a [Python](http://www.python.org/download/) module. On Mac OS X,
the Python programming language is already installed. On other systems
you need to download and install it yourself, if necessary. MBSP works
with Python 2.5, but support for processes is better in version 2.6. It
should also work with version 2.4.

MBSP is bundled with three required dependencies written in C/C++ (TiMBL
6.1.5, MBT 3.1.3 and MBLEM). Binaries have been precompiled for Mac OS X
10.5, but these may not work on your machine. In that case you need to
compile binaries manually from the source code.

### Compiling with setup.py

The module comes with a `setup.py` script
that compiles the C/C++ binaries automatically. If this works for you,
you're in luck – no manual compilation is necessary. Also, if you run
`setup.py` with the
`install` argument, it will first compile
the binaries and then install a copy of MBSP in Python's
`/site-packages` folder so that the
module is available in any Python script.

```
> cd MBSP
> python setup.py install
```

### Compiling from source

 You'll need a [gcc](http://gcc.gnu.org/) compiler. On Windows you'll
need [cygwin](http://www.cygwin.com/).  
In the cygwin installer (`setup.exe`), be
sure to select the "`devel`" packages for
installation.

#### Building MBLEM

  - Go to the `MBSP/mblem` folder.
  - Delete all files with a "`.o`"
    extension + the current executable binary
    `mblem_english_bmt`.  
  - From the command line, do `make` in
    the `MBSP/mblem` folder:

<!-- end list -->

```
> cd MBSP/mblem
> make
```

#### Building TiMBL

  - Go to the `MBSP/timbl` folder.
  - Uncompress the source code from the
    `timbl-6.1.5.tar` archive.
  - From the command line, do `configure`
    and `make` in the
    `MBSP/timbl/timbl-6.1.5` folder:

<!-- end list -->

```
> cd MBSP/timbl/timbl-6.1.5
> ./configure --enable-shared=no --enable-static=no --prefix=[FOLDER]
> make install
```

  - `[FOLDER]` is an absolute path to
    the folder where Timbl will be built.
  - The Timbl executable will be in
    `[FOLDER]/bin`
    → copy it to `MBSP/timbl`.
  - Now build MBT in the same `[FOLDER]`
    location:

#### Building MBT

  - Go to the `MBSP/mbt `folder.
  - Uncompress the source code from the
    `mbt-3.1.3.tar` archive.
  - From the command line, do `configure`
    and `make` in the
    `MBSP/mbt/mbt-3.1.3` folder:

<!-- end list -->

```
> cd MBSP/mbt/mbt-3.1.3
> ./configure --enable-shared=no --enable-static=no --prefix=[FOLDER]
> make install
```

  - The Mbt executable will be in `[FOLDER]` → copy it to `MBSP/mbt`.
  - Delete the build `[FOLDER]`, it is no longer needed.

### Module folder location

To be able to `import MBSP` in your
scripts, Python needs to know where the module is located.  
There are three basic ways to accomplish this:

  - Put the MBSP folder in the same folder as your script.
  - Put the MBSP folder in the standard location for modules so it is
    available to *all* scripts.  
    The standard location depends on your operating system, for
    example:  
    `/Library/Python/2.5/site-packages/`
    on Mac,  
    `/usr/lib/python2.5/site-packages/`
    on Unix,  
    <span class="inline_code">c:\\python25\\Lib\\site-packages\\
    </span>on Windows.<span class="inline_code">  
    </span>
  - Add the location of MBSP to the
    `sys.path` list in your script,
    before importing it:

```python
>>> MODULE = '/users/tom/desktop/MBSP'
>>> import sys; if MODULE not in sys.path: sys.path.append(MODULE)
>>> import MBSP
```

### Memory usage

MBSP starts four data servers that require quite a bit of memory
(`CHUNK`: 80MB,
`LEMMA`: 10MB,
`RELATION`: 160MB,
`PREPOSITION`: 210MB). Only the
`CHUNK` server (which gives you the
part-of-speech tags) is mandatory. The optional servers can be disabled
in `config.py` to reduce the memory
usage, for example:

```python
servers = ['chunk', 'lemma']
```

### Multithreading

MBSP can be configured to work with multithreading, which can increase
performance by 25% - 200%.
`MBSP.config.threading` needs to be set
to `True`. You also need to build the
newer TiMBL 6.3+, MBT 3.2+ and TimblServer 2+ from
[source](http://ilk.uvt.nl/). The installation instructions are mostly
the same:

  - TimblServer can be compiled in the same way as MBT.
  - Put the `TimblServer` executable in
    `MBSP/timbl` instead of the
    `Timbl` executable.

Older systems may complain that
`pkg-config` is outdated. In this case,
before building Timbl, compile pkg-config 0.25+
(<http://pkgconfig.freedesktop.org>) from source with:
<span class="inline_code">sudo ./configure; sudo make; sudo make
install</span>

We have precompiled versions of TimblServer which may also work on your
system (in that case you don't need to install from source): download
for [Mac OS X 10.5](/media/MBSP-TimblServer1.0.0-OSX10.5.zip) | [Ubuntu
10.04 (64-bit)](/media/MBSP-TimblServer2.0.0-Ubuntu10.04.zip).



-----

## <span id="parser"></span>Parser

MBSP uses a client-server architecture. This way, the corpus data is
loaded only once (during server startup) and stays available while the
servers sleep in the background. Before tagging jobs can be sent to the
parser, the servers have to be started. By default, this will happen
automatically when you import MBSP in your script. Otherwise, the
`start()` command starts the four servers
(named `CHUNK`,
`LEMMA`,
`RELATION` and
`PREPOSITION`). The
`started()` command yields True if a
given server has been started. The
`stop()` command will stop the servers.

```python
MBSP.start(timeout=60)
```

```python
MBSP.started(name=ALL) # CHUNK | LEMMA | RELATION | PREPOSITION
```

```python
MBSP.stop()
```

The `parse()` command takes a string of
sentences and returns a tagged Unicode string.  
Sentences in the output are separated by newline characters.

```python
MBSP.parse(string,
     tokenize = True,
         tags = True,
       chunks = True,
    relations = True,
      anchors = True,
      lemmata = True,
     encoding = 'utf-8')
```

For example:

```python
print(MBSP.parse('I ate pizza with a fork.'))

>>> I/PRP/I-NP/O/NP-SBJ-1/O/i
    ate/VBD/I-VP/O/VP-1/A1/eat
    pizza/NN/I-NP/O/NP-OBJ-1/O/pizza
    with/IN/I-PP/B-PNP/O/P1/with
    a/DT/I-NP/I-PNP/O/P1/a
    fork/NN/I-NP/I-PNP/O/P1/fork ././O/O/O/O/.
```

Each token (i.e. tagged word) in a sentence has a number of annotations:
`tags</span><span class="inline_code">=True`
includes the word part-of-speech tag,
`chunks` the chunk tag +
<span class="postag">PNP</span> tag (prepositional noun phrase),
`relations` the chunk relation tag,
`anchors` the
<span class="postag">PNP</span> anchor tag. With
`tokenize` set to False, no tokenization
is carried out (so the input string is expected to be tokenized). The
`encoding` parameter defines the
character encoding of the input string, "utf-8" is fine in most cases.

### Parser tags

Let's examine the word *ate* and the tags assigned by the parser in the
example above:

|      |                                  |                                  |                               |                                  |                                |       |
| :--: | :------------------------------: | :------------------------------: | :---------------------------: | :------------------------------: | :----------------------------: | :---: |
| word |          part-of-speech          |              chunk               |              pnp              |             relation             |             anchor             | lemma |
| ate  | <span class="postag">VBD </span> | <span class="postag">I-VP</span> | <span class="postag">O</span> | <span class="postag">VP-1</span> | <span class="postag">A1</span> |  eat  |

The word's part-of-speech tag is <span class="postag">VBD</span>, which
means that it is a verb in the past tense. The word occurs in a
<span class="postag">VP</span> chunk, a verb phrase. It is not part of a
prepositional noun phrase. It's relation tag is
<span class="postag">VP-1</span>, which means it is linked to the words
tagged as <span class="postag">NP-SBJ-1</span> (*I*, the sentence
subject) and <span class="postag">NP-OBJ-1</span> (*pizza*, the sentence
object). Its anchor tag is <span class="postag">A1</span>, meaning it is
the anchor of the prepositional noun phrase
<span class="postag">P1</span>, *with a fork*. How did I eat pizza? →
with a fork. The base form or lemma of *ate* is *eat*.

Common part-of-speech tags include <span class="postag">NN</span>
(noun), <span class="postag">JJ</span> (adjective) and
<span class="postag">VB</span> (verb).  
Common chunk tags include <span class="postag">NP</span> (noun phrase)
and <span class="postag">VP</span> (verb phrase).  
Common relations include <span class="postag">SBJ</span> (subject) and
<span class="postag">OBJ</span> (object).

The [MBSP tags](/pages/MBSP-tags) page gives an overview of all the
possible tags generated by the parser.

A description and an example can also be acquired with the
`taginfo()` command:

```python
>>> description, example = MBSP.taginfo('NN')
>>> print(description, example)

('noun, singular or mass', 'tiger, chair, laughter')
```

### Parser shortcuts

Below is a set of concise commands that internally call
`parse()` with the required parameters.

  - The `tag()` command returns a string
    annotated with part-of-speech tags.
  - The `chunk()` command returns a
    string annotated with part-of-speech, chunk and
    <span class="postag">PNP</span> tags.
  - The `lemma()` command takes a single
    word and returns its lemma.
  - The `nouns()`,
    `verbs()` or
    `adjectives()`
    ` ` command returns a list of nouns,
    verbs or adjectives retrieved from the given string.

<!-- end list -->

```python
MBSP.tokenize(string)
```

```python
MBSP.tag(string, tokenize=True, lemmata=False)
```

```python
MBSP.chunk(string, tokenize=True, lemmata=False)
```

```python
MBSP.lemma(word)
```

```python
MBSP.nouns(string, lemmatize=False)
MBSP.verbs(string, lemmatize=False)
MBSP.adjectives(string, lemmatize=False)
```

Like `parse()`, all of these commands
have an optional `encoding` parameter
that is "utf-8" by default.

### Parser output

The output of the `parse()` command is a
string of sentences in which each token has been annotated with the
requested tags. The `pprint()` command
(extra *p* is for *pretty*) gives a good overview of the tags:

```python
s = MBSP.parse('I eat pizza.')
MBSP.pprint(s)

>>>    WORD   TAG    CHUNK   ROLE   ID     PNP    ANCHOR   LEMMA
          I   PRP    NP      SBJ    1      -      -        i
        eat   VBP    VP      -      1      -      -        eat
      pizza   NN     NP      OBJ    1      -      -        pizza
          .   .      -       -      -      -      -        .        
```

The output string is in fact a
`TokenString` object that behaves as a
Python string, but with extra functionality. Most notably it has a
`TokenString.split()` method that yields
a `TokenList` object: a list of
sentences, where each sentence is a list of tokens, in which each token
is a list of tags. This is useful when you want to [extend the
parser](/pages/MBSP#customization) and need to make some modifications
to the output.

If you want to analyze the output (i.e. examine the relations between
words and groups of words), it is more convenient to construct a [parse
tree](/pages/MBSP#tree) from the output.



-----

## <span id="tokenizer"></span>Tokenizer

MBSP includes a regular expressions-based tokenizer that divides
sequences of characters into words and sentences. Special care is given
to punctuation marks. We need to guess which punctuation marks are part
of a word (e.g. periods in abbreviations) and which mark word and
sentence breaks. Once tokenized, the [parser](/pages/MBSP#parser) can
then determine categories for words (tokens) in the string.

```python
MBSP.tokenizer.split(string, tags=False, citations=False, replace={}, ignore=[])
```

The `split()` command returns a list of
Unicode strings where punctuation marks have been split from words as
individual tokens. Each string in the list is a sentence. By default,
all SGML-tags (i.e. anything wrapped in \<...\>) are stripped from the
input string. With `citations=True`,
sentences in quoted citations are kept together. The
`replace` dictionary is used to map
unicode quotes and ellipsis to standard quotes and periods. The
`ignore` list defines ranges of words
that require special attention (for example, abbreviations and URL's –
see below).

For example:

```python
MBSP.tokenizer.split('The U.N. is considering banning "defamation of religion." The U.N. president said such a move would not limit free speech.')
[u'The U.N. is considering banning " defamation of religion . "',
 u'The U.N. president said such a move would not limit free speech .']
```

### Tokenization process

In the simplest case, words are marked by spaces. A number of exceptions
are then handled:

  - **Handle missing space**: punctuation inside a word can indicate a
    missing space.
  - **Handle punctuation**: punctuation marks at the head or tail of a
    word can indicate a sentence break, the start of a citation, the
    start of an explanation in parenthesis. In this case the punctuation
    is split from the word. Punctuation that is part of the word (e.g.
    *5p.m.*) needs to be kept intact.
  - **Handle contractions**: apostrophes in contractions (*he's*) and
    possessives (*father's*) mark word boundaries. The suffix is split
    from the word.
  - **Handle lists**: list item markers such as *1. 1) \* - a. a)* at
    the start of a new line indicate the start of a new sentence, even
    if the previous sentence did not end with a period.
  - **Handle hyphenation**: hyphens at the end of a line mark words that
    have been split across lines: *mar-* + *ket* becomes *market*,
    *Great-* + *Britain* becomes *Great-Britain*.
  - **Handle sentence breaks**: periods, exclamation marks, question
    marks and ellipsis end a sentence if they are followed by a
    capitalized letter. Parenthesis and quotes can be part of the
    sentence even if the period precedes it.

### Tokenizer word ranges

The tokenizer defines a `Range` class for
matching sets of words: all abbreviations, all numeric strings, all
hyperlinks, etc. The `Range` class is a
list of known words enriched with regular expression patterns. In the
example below, an abbreviation range is created that matches *U.K.*,
*U.N.* and any single letter abbreviation (as in *T. De Smedt*).

```python
abbreviations = MBSP.tokenizer.Range(['U.K.', 'U.N.'])
abbreviations.patterns.append(re.compile('^[A-Za-z]\.$'))
print 'U.K.' in abbreviations, 'T.' in abbreviations
>>> True True
```

Custom ranges can be passed to the
`ignore` parameter of the
`split()` command.  
By default, `split()` will use a list of
predefined ranges:

```python
MBSP.tokenizer.ignore = [abbreviations, numeric, URI, entities, biomedical]
```

Predefined ranges:

  - **Abbreviations**: the simple rule is that every point is a sentence
    break. This is 93.2% correct for Brown corpus
    \[[1](http://bulba.sdsu.edu/~malouf/ling571/13-token-bw.pdf)\].
    Fixing decimal points, single letter abbreviations, alternating
    letters and capital letter followed by consonants (*Dept.*) improves
    sentence break correctness to 97.7%. Additionally, the abbreviations
    range defines a list of other well-known abbreviations.
  - **Numeric**: matches anything starting with a digit followed by a
    chain of digits and .,:/ separators. The range will also recognize
    units of measurement (length, mass, volume, time, epoch,
    temperature, storage capacity, data transfer rate, percentage):
    US$100, 1.2MB, 31/12/2010, ...
  - **URI**: matches URL's, links and e-mail addresses.
  - **Entities**: matches HTML and Unicode entities.
  - **Biomedical**: guesses biomedical-specific words, such as
    *1',2'-trifenol*.

### Tokenizer modes

The tokenizer can be configured in different modes. By default it uses
Penn Treebank specifications for tokenization and uses special
corrections for biomedical use.

```python
MBSP.tokenizer.PENN_TREEBANK = True
MBSP.tokenizer.BIOMEDICAL = True
```

In Penn Treebank mode, only % is split from numbers and contractions are
not substituted: *won't* becomes *wo n't* instead of *will not*. In
biomedical mode, less magic is used when finding missing spaces so that
*3(R),3a(S),6a(R)-bis-tetrahydrofuranylurethane* is not split at the
comma or the parenthesis.

-----

## <span id="lemmatizer"></span>Lemmatizer

MBSP uses the MBLEM C module for word lemmatization. MBLEM (Memory-Based
Lematization) transforms a word form into a canonical lexical form:
*was* → *be*, *booking* → *book*.

```python
>>> print MBSP.lemmatize("The cats were sleeping.", tokenize=True)

the cat be sleep .
```
The goal of lemmatization is to provide better (generalizable) lexical
information that can be used by other components in the pipeline, and
(possibly) also for indexing the processed text in a search engine.
Lemmatization is not to be confused with *stemming*, in which frequent
suffixes such as *-ing* and *-ed* are simply removed: *having* is
stemmed to *hav*, while it is lemmatized to *have*.

### Lemmatization process

Words can have more than one lemma. The lemmatizer's task is to find the
most suitable:

  - **Find lemmata**: determines for each word in a sentence which
    lemmata it could be mapped to. The word *saw* is lemmatized to the
    noun lemma *saw* and the verb lemma *see*. In case of producing more
    than one lemma, the lemmatizer is unable to determine which lemma is
    appropriate in the current sentence, as it does not use context.

  - **Disambiguate**: consults the output of the part-of-speech tagger.
    If the tagger has identified *saw* as a past-tense verb form
    (<span class="postag">VBD</span>), MBLEM concludes that the
    appropriate lemma is *see*, and selects this one as the correct
    output. MBLEM therefore always generates a single lemma per word.

MBLEM is trained on the CELEX English lexical database, and will simply
retrieve the lemmatizations of words that occur in the database. Words
in the text that are not in CELEX (so-called "unknown" words, typically
constituting 5% of the words in a text) are lemmatized by analogy to
stored word lemmatizations.

<span class="small"><span style="text-decoration: underline;">Reference</span>:
Van den Bosch, A., & Daelemans, W. (1999).  
*Memory-based morphological analysis*, In: Proceedings of the 37th
annual meeting of the Association for Computational Linguistics on
Computational Linguistics, pp. 285-292.</span>

-----

## <span id="pp-attacher"></span>PP-attacher

A shallow parsing approach sometimes has its shortcomings, an important
one being that prepositional phrases, which contain important semantic
information for interpreting events (e.g. *I sleep* vs. *I sleep
<span style="text-decoration: underline;">under a bridge</span>*), are
left unattached. MBSP comes with a memory-based PP-attacher (MBPA)
trained on sections 2 through 21 of the Penn Treebank II Wall Street
Journal corpus (WSJ). It will link <span class="postag">PNP</span>
chunks to other “anchor” chunks.

With the PP-attacher enabled, performance is slower but you gain a lot
of useful information.

```python
s = MBSP.parse('I sleep under a bridge', anchors=True)
s = MBSP.split(s)
print(s[0].pnp)
print(s[0].pnp[0].anchor)

>>> [Chunk('under a bridge/PNP')]
>>> sleep
```

### PP-attachment process

A <span class="postag">PNP</span>-chunk can be attached to different
candidate chunks. However, there is a semantic difference between *I eat
<span style="text-decoration: underline;">pizza with olives</span>* and
*I <span style="text-decoration: underline;">eat</span> pizza
<span style="text-decoration: underline;">with olives</span>*. Which one
is correct? And which one is correct here: *I
<span style="text-decoration: underline;">eat</span> pizza
<span style="text-decoration: underline;">with a fork</span>* or *I eat
<span style="text-decoration: underline;">pizza with a fork</span>*?

  - **Find prepositional noun phrases**: these are retrieved by a
    regular expression-like algorithm. All
    <span class="postag">PP</span> + <span class="postag">NP</span>
    sequences are considered to be <span class="postag">PNP</span>’s.
    Two exceptions: <span class="postag">PP</span> + **“** +
    <span class="postag">NP</span> (e.g. *in “modest amounts”*) and
    <span class="postag">PP</span> + <span class="postag">VBG</span> +
    <span class="postag">NP</span> (*in making paper*) are also
    considered <span class="postag">PNP</span>’s.   

  - **Classify**: the core of the PP-attacher is a memory-based
    classifier. Candidate anchors are the
    <span class="postag">NP</span>’s and
    <span class="postag">VP</span>’s of the sentence that are not part
    of the <span class="postag">PNP</span> itself. For example, *I eat a
    pizza with olives* induces three classification tasks (*I-with,
    eat-with*, *pizza-with*) in which the machine learner will have to
    decide if the pair suggests a true anchor or not – taking into
    account the distance to the candidate anchor and intermediary
    punctuation, the number of intermediary
    <span class="postag">NP</span>’s, and so on.
  - **Heuristic decision making**: when the classifier identifies
    multiple anchor candidates, an extra step is taken to pick one
    unique anchor, using a baseline and entropy algorithm (details are
    summarized in the reference paper).

In 50% of the cases a noun phrase (<span class="postag">NP</span>) is
chosen as anchor, in about 45% a verb phrase
(<span class="postag">VP</span>).

<span class="small"><span style="text-decoration: underline;">Reference</span>:
Van Asch, V., & Daelemans, W. (2009).  
*Prepositional Phrase Attachment in Shallow Parsing*. In: Proceedings of
the 7th International Conference on Recent Advances in Natural Language
Processing (RANLP), pp. 12-17.</span>

-----

## <span id="tree"></span>Parse trees

A parse tree stores a parsed string as a network of linked Python
objects that can be traversed to analyze the sentences in the string.
The output of the [parser](/pages/MBSP#parser) can be passed to the
`split()` command, which produces a
`Text` object. Essentially, a
`Text` is a list of
`Sentence` objects. Each
`Sentence` consists of
`Word` objects.
`Word` objects are also grouped in
`Chunk` objects, which are related to
other `Chunk` objects in various ways.

```python
MBSP.split(parsed_string, token=[WORD, POS, CHUNK, PNP, RELATION, ANCHOR, LEMMA])
```

We'll run the sentence "*The cat sat on the mat.*" through the parse
tree:

```python
s = MBSP.parse('The cat sat on the mat.')
s = MBSP.split(s)
print(repr(s))

[Sentence(
 """The/DT/B-NP/O/NP-SBJ-1/O/the
  cat/NN/I-NP/O/NP-SBJ-1/O/cat
  sat/VBD/B-VP/O/VP-1/A1/sit
  on/IN/B-PP/B-PNP/PP-CLR/P1/on
  the/DT/B-NP/I-PNP/NP-CLR/P1/the
  mat/NN/I-NP/I-PNP/NP-CLR/P1/mat
  ././O/O/O/O/.""")]
```

```python
print(s[0].chunks)

>>> [Chunk('The cat/NP-SBJ-1'),
     Chunk('sat/VP-1'),
     Chunk('on/PP-CLR'),
     Chunk('the mat/NP-CLR')]
```

### Text

A `Text` is a list of
`Sentence` objects.

```python
text = MBSP.Text(parsed_string, token=[WORD, POS, CHUNK, PNP, REL, ANCHOR, LEMMA])
```

```python
text = MBSP.Text.from_xml(xml)
```

```python
text.string                # 'The cat sat on the mat .'
text.sentences             # [Sentence('The cat sat on the mat .')]
text.append(sentence)
text.copy()
```

```python
text.xml
```

Since `Text` behaves as a Python list it is
easy to traverse all the contained sentences:

```python
for sentence in text:
    print(sentence)
```

### Sentence

A `Sentence` is a list of
`Word` objects, with attributes and
methods that organize words in `Chunk`
objects.

```python
sentence = MBSP.Sentence(string="", token=[WORD,POS,CHUNK,PNP,REL,ANCHOR,LEMMA])
```

```python
sentence = MBSP.Sentence.from_xml(xml)
```

```python
sentence.parent            # Slices refer to the sentence they are part of.
sentence.id                # Unique for each sentence.
sentence.start             # 0
sentence.stop              # 6
sentence.token             # [WORD, POS, CHUNK, PNP, REL, ANCHOR, LEMMA]
```

```python
sentence.string            # 'The cat sat on the mat .'
sentence.words             # [Word('The/DT'), Word('cat/NN'), ... ]
sentence.lemmata           # [u'the', u'cat', u'sit', u'on', u'the', u'mat', u'.']
sentence.tagged            # [(u'The', u'DT'), (u'cat', u'NN'), ... ]
sentence.parts_of_speech   # [u'DT', u'NN', u'VBD', u'IN', u'DT', u'NN', u'.']
```

```python
sentence.chunks            # [Chunk('The cat/NP-SBJ-1'), Chunk('sat/VP-1'), ... ]
sentence.subjects          # [Chunk('The cat/NP-SBJ-1')]
sentence.objects           # []
sentence.verbs             # [Chunk('sat/VP-1')]
sentence.relations         # {'SBJ': {1: Chunk('the cat/NP-SBJ-1')},
                           #   'VP': {1: Chunk('sat/VP-1')},
                           #  'OBJ': {}}
```

```python
sentence.pnp               # [Chunk('on the mat/PNP')]
sentence.anchors           # [Chunk('sat/VP-1')]
```

```python
sentence.constituents(pnp=False)
```

```python
sentence.get(index, tag=LEMMA)
sentence.loop(tag1, tag2, ...)
sentence.indexof(value, tag=WORD)
```

```python
sentence.slice(start, stop)
sentence.copy()
```

```python
sentence.xml
sentence.nltk_tree()
```

  - `Sentence.constituents()` returns an
    in-order list of `Word` and
    `Chunk` objects.  
    With `pnp=True`, also groups
    into `PNPChunk` objects whenever
    possible.
  - <span class="inline_code" style="font-family: Courier, monospace; font-size: 12px;">Sentence.get()</span> returns
    the requested tag of the word at the given index.  
    The tag can be `WORD`,
    `LEMMA`,
    `POS`,
    `CHUNK`,
    `PNP`,
    `RELATION`,
    `ROLE`,
    `ANCHOR` or a custom word tag.
  - `Sentence.loop()` is an iterator over
    a list of tuples containing the requested tags for each word.
  - `Sentence.indexof()` returns the
    indices of words for which the given tag equals the given value.
  - For example, <span class="inline_code">Sentence.indexof("NN\*",
    tag=POS)</span> returns a list of indices of the words whose
    part-of-speech is <span class="postag">NN</span>,
    <span class="postag">NNS</span>, <span class="postag">NNP</span> or
    <span class="postag">NNPS</span>.
  - `Sentence.slice() `returns a new,
    partial sentence starting with the word at index
    `start` and containing all the words
    up to (before) index `stop`.

#### Creating a sentence

Normally, a sentence is constructed from the output of the
`parse()` command. Since this output is a
[TokenString](/pages/MBSP#extending) which stores the order in which
tags appear in a token, `Sentence` can
figure out how to construct a parse tree by itself. If you want to
construct sentences from a different source, you need to specify the
`token` parameter in the constructor, or
use `Sentence.append()` to add words
manually. If you have tokens in a slash-formatted string like MBSP (e.g.
"cats/<span class="postag">NNS</span>/<span class="postag">I-NP</span>/<span class="postag">O</span>/<span class="postag">O</span>/<span class="postag">O</span>/cat")
you can use `Sentence.parse_token()`,
which returns the arguments for
`Sentence.append()`.

```python
sentence.append(word,
       lemma = None,
        type = None,
       chunk = None,
        role = None,
    relation = None,
         pnp = None,
      anchor = None,
         iob = None,
      custom = {})
```

```python
sentence.parse_token(token, tags=[WORD, POS, CHUNK, PNP, REL, ANCHOR, LEMMA])
```

For example:

```python
s = MBSP.Sentence('cats/NNS', token=[MBSP.WORD, MBSP.POS])
print(s.words)

>>> [Word('cats/NNS')]
```

```python
s = MBSP.Sentence()
s.append(word='cats', lemma='cat', type='NNS', chunk='NP')
print(s.words)

>>> [Word('cats/NNS')]
```

```python
s = MBSP.Sentence()
s.append(*s.parse_token('cats/NNS/I-NP/O/O/O/cat'))
print(s.words)

>>> [Word('cats/NNS')]
```

### Sentence words

A `Sentence` is made up of
`Word` objects, which are also grouped in
`Chunk` objects:

```python
word = MBSP.Word(sentence, string, lemma=None, type=None, index=0)
```

```python
word.sentence              # Sentence object (e.g. 'The cat sat on the mat .')
word.index                 # 2
word.string                # 'sat'
word.lemma                 # 'sit'
word.type                  # 'VBD'
word.chunk                 # Chunk('sat/VP-1').
word.pnp                   # None
```

```python
word.custom_tags           # User-defined tags, e.g. {SENTIMENT: 'lazy'}
```

```python
word.tags()                # ['sat', 'VBD', 'B-VP', 'O', 'VP-1', 'O', 'sit']
```

  - `Word.type` is an alias for
    `Word.part_of_speech`.
  - `Word.pnp` is an alias for
    `Word.prepositional_noun_phrase`.
  - The `word.custom_tags` is a
    dictionary of additional, user-defined tags that can occur when the
    parser has been [extended](/pages/MBSP#customization). If the word
    has (for example) an additional *sentiment* tag, it is also
    available as `Word.sentiment`.
  - The `Word.tags()` method returns a
    list of token tags as they appear in the output of the parser.  
    The order of tags is determined by the
    `Sentence.token` attribute.

### Sentence chunks

A `Chunk` is a list of
`Word` objects that belong together.  
Chunks can be part of a `PNPChunk`, which
starts with a <span class="postag">PP</span> chunk followed by
<span class="postag">NP</span> chunks.

```python
chunk = MBSP.Chunk(sentence, words=[], type=None, role=None, relation=None)
```

```python
chunk.sentence             # Sentence object (e.g. 'The cat sat on the mat .')
chunk.start                # 0
chunk.stop                 # 2
```

```python
chunk.string               # 'The cat'
chunk.words                # [Word('The/DT'), Word('cat/NN')]
chunk.lemmata              # ['the', 'cat']
chunk.tagged               # [(u'The', u'DT'), (u'cat', u'NN')]
chunk.head                 # Word('cat/NN')
```

```python
chunk.type                 # 'NP'
chunk.role                 # 'SBJ'
chunk.relation             # 1
chunk.relations            # [(1, u'SBJ')]
chunk.related              # [Chunk('sat/VP-1')]
chunk.subject              # None
chunk.object               # None
chunk.verb                 # Chunk('sat/VP-1')
chunk.modifiers            # []
chunk.conjunctions         # []
```

```python
chunk.pnp                  # None
chunk.anchor               # None
chunk.attachments          # [Chunk('on the mat/PNP')]
```

```python
chunk.append(word)
```

```python
chunk.previous(type=None)  # None
chunk.next(type=None)      # Chunk('sat/VP-1')
chunk.nearest(type="VP")   # Chunk('sat/VP-1')
```

  - `Chunk.head` yields the last (i.e.
    principal) `Word` in the chunk.
  - `Chunk.relations` contains *all* relations the chunk is involved in.  
    Some chunks (about 15%) have multiple relations, for example functioning as both <span class="postag">SBJ</span> and <span class="postag">OBJ</span>, or being the <span class="postag">OBJ</span> of multiple <span class="postag">VP</span> chunks.
  - For <span class="postag">VP</span> chunks, `Chunk.modifiers is a list of nearby adjectives and adverbs with no relations.  
    For example: in '*the cat really wants out*', *really* and *out* are <span class="postag">ADVP</span> with no relations.  
    The parse tree will assume that they have something to do with the <span class="postag">VP</span> *wants*.  
    What does the cat want? → out.  
    How badly does the cat want out? → really.
  - `Chunk.conjunctions is a list of chunks linked by "and" or "or" to this chunk.  
    For example: in '*going up and down*', the up chunk has conjunctions: \[(Chunk('down'), AND)\].
  - `Chunk.pnp is an alias for the
    parent `Chunk.prepositional_noun_phrase`.
  - `Chunk.attachments contains related
    prepositional noun phrases
  - `Chunk.anchor references the chunk
    that is the anchor of this <span class="postag">PNP</span>.

### Prepositional noun phrases

`PNPChunk is a subclass of
`Chunk, it has the same attributes and
methods.  
It groups multiple chunks in a prepositional noun phrase
(<span class="postag">PNP</span>).

```python
pnp = MBSP.PNPChunk(sentence, words=[], type=None, role=None, relation=None)
```

```python
pnp.string                 # 'on the mat'
pnp.chunks                 # [Chunk('on/PP-CLR'), Chunk('the mat/NP-CLR')]
pnp.preposition            # Chunk('on/PP-CLR')
pnp.anchor                 # Chunk('sat/VP-1')
```

```python
pnp.guess_anchor()         # Returns the nearest VP chunk.
```

Words and chunks that are part of a <span class="postag">PNP</span> will
have their `Word.pnp and
`Chunk.pnp attribute set.  
All the prepositional noun phrases in a sentence can be retrieved with
`Sentence.pnp.



-----

## <span id="server"></span>Clients and servers

MBSP uses a client-server architecture so that the data only has to be loaded once.
From then on it is available as a server that can be contacted with the TCP protocol. MBSP has a `Client and a `Server class that communicate using the Python `socket module.
`Server is a wrapper around `subprocess.Popen and starts TiMBL or MBT as a background process.

MBSP starts four servers:

|                                                    |                |                                         |                                                                       |
| -------------------------------------------------- | -------------- | --------------------------------------- | --------------------------------------------------------------------- |
| <span class="smallcaps">Name </span>               | Address        | <span class="smallcaps">Process </span> | <span class="smallcaps">Description </span>                           |
| `MBSP.CHUNK        | localhost:6061 | MBT                                     | Server  for finding part-of-speech and chunk tags.                    |
| `MBSP.LEMMA        | localhost:6062 | TiMBL                                   | Server used by [MBLEM](http://ilk.uvt.nl/mbma/) to find word lemmata. |
| `MBSP.RELATION     | localhost:6063 | TiMBL                                   | Server for finding verb-argument chunk relations.                     |
| `MBSP.PREPOSITION </span> | localhost:6064 | TiMBL                                   | Server for finding <span class="postag">PNP anchors.           |

**TiMBL**: memory-based learning is an elegantly simple and robust
machine-learning method applicable to a wide range of tasks in Natural
Language Processing.

<http://ilk.uvt.nl/timbl/>

**MBT**: a memory-based tagger-generator and tagger in one. MBT can, for instance, be used to generate part-of-speech taggers or chunkers for natural language processing. <http://ilk.uvt.nl/mbt/>

### Client

The `Client base class can be used to contact a TiMBL or MBT server running at a given host address, at a given TCP communication port.
`Client</span> is then subclassed with `Timbl and <span class="inline_code">Mbt classes.

```python
client = MBSP.Client(
        host = LOCALHOST,
        port = 6060,
        name = None,
         log = False,
     request = lambda v:v.strip()+'\n',
    response = lambda v:v)
```

```python
client.name
client.host
client.port
client.connected # True after Client.connect() is called.
```

```python
client.connect()
client.send(request, timeout=None)
client.disconnect()
```

  - `Client.connect() raises a
    `ServerConnectionError if the server
    can't be contacted.
  - `ServerConnectionError.code can
    contain additional information, such as
    `CONNECTION_RESET_BY_PEER,
    `CONNECTION_REFUSED or
    `BROKEN_PIPE.
  - `Client.send() prepares the request,
    sends it to the server and returns the response.  
    `Client.send() raises a
    `ClientDisconnectedError if
    `Client.connect() is not called
    first.  
    If `timeout` is given and no response
    is returned in the given time, a
    `ClientTimeoutError` is raised.
  - Make sure to clean up with
    `Client.disconnect() when the client
    is no longer needed.

#### Request and response formatters

Note the `request` and `response` parameters in the
`Client` constructor. These are formatter
functions that will be called by
`Client.send()` to 1) prepare the data
before sending it to the server and 2) to clean up the server response
before returning it.

For example, if we send a raw request to the chunk server:

```python
>>> chunker = MBSP.Client(port=6061)
>>> print chunker.send('cat')

cat/NN/I-NP -utt-
```

The MBT server's response ends with a delimiter which we may want to
clean from the output.  
This can be achieved by using a response formatter:

```python
>>> chunker = MBSP.Client(port=6061, response=lambda v: v.rstrip(' -utt-\n'))
>>> print chunker.send('cat')

cat/NN/I-NP
```

<span class="small"><span style="text-decoration: underline;">Note</span>:
in reality, MBT's delimiter is a *utt* tag (so *utt* enclosed in \< and
\>) but </span><span class="small">in this example
</span><span class="small">we use *-utt-* instead to avoid the browser
thinking it's a HTML-tag. </span>

### TiMBL and MBT client

MBSP has a `Timbl` and a `Mbt` class: subclasses of `Client`, with the right request and response formatters.

```python
timbl = MBSP.Timbl(host=LOCALHOST, port=6060, name=None, log=False, verbosity=[])
```

```python
mbt = MBSP.Mbt(host=LOCALHOST, port=6060, name=None, log=False)
```

TiMBL's output depends on the way the server *verbosity*
(`+v`) is configured. In MBSP it
typically it yields a category string:
"`CATEGORY {NP-SBJ} `". Depending on the
verbosity it can also yield different output. For example, verbosity
option  `+v di+db `yields a **
category-distance-distribution string:  
"<span class="inline_code">CATEGORY {VP} DISTRIBUTION { VP 3.11506, n-VP
2.58232 } DISTANCE {2.02066} </span>".

The TiMBL client has an additional
`verbosity` parameter which can be used
to format the response:

```python
>>> timbl = MBSP.Timbl(port=6064, verbosity=['di','db'])
>>> print timbl.send('0 0 2 - eat VBP pizza NN with fork NN 1 0')

['VP', 2.0206599999999999, {'VP': 3.1150600000000002, 'n-VP': 2.5823200000000002}]
```

The server at port 6064 is the preposition server, which loads with
option `+v di+db`, so responses include
distance and distribution metrics. The TiMBL client in this example sets
the right verbosity options so that distance is correctly parsed as a
float, and distribution as a dictionary.

See the [TiMBL
manual](http://ilk.uvt.nl/downloads/pub/papers/Timbl_6.2_Manual.pdf) for
all verbosity options.

### Client batch requests

Since the servers are multithreaded, multiple request can be sent at the
same time to speed up the lookup process. MBSP's client module has a
`client.batch()` command to achieve this.
It takes a list of requests (i.e. instances) and a "client definition".
This definition is a tuple with the necessary parameters that allows the
`batch()` command to generate threaded
`Client` objects. The
`client.define()` command can be used to
generate the tuple.

```python
MBSP.client.batch(instances, client, timeout=None, retries=1)
```

```python
MBSP.client.define(client, host=LOCALHOST, port=6060, name=None, log=False)
```

For example:

```python
>>> from MBSP.client import batch, define, Mbt
>>> print batch(['cat', 'sat', 'mat'], client=define(Mbt, port=6061))

['cat/NN/I-NP', 'sat/VBN/I-VP', 'mat/NN/I-NP']
```

### Client request log

If `config.log=True`, all client requests
and server responses are logged. This is useful for evaluation. Also,
when logs are enabled, a cached request can be reused without having to
contact the server. The performance hit is negligible however – except
for very repetitive texts.

The log is a dictionary indexed by server name
(`CHUNK`,
`LEMMA`,
`RELATION` and
`PREPOSITION`).  
Each individual server log in the dictionary is an ordered dictionary
that stores the last 1000 requests.

```python
MBSP.client.log
```

For example:

```python
>>> MBSP.config.log = True
>>> MBSP.parse('I eat pizza with a fork.')
>>> print MBSP.client.log[MBSP.RELATION]

{'-1 0 0 eat VBP - - - - - - - I PRP NP VBP VP ?': 'CATEGORY {NP-SBJ}\n',
  '1 0 0 eat VBP - - - eat VBP VP - pizza NN NP NN PNP ?': 'CATEGORY {NP-OBJ}\n',
  '2 0 0 eat VBP eat VBP VP pizza NN NP - fork NN PNP - - ?': 'CATEGORY {-}\n'}
```

Three requests were sent to the relation server to find the sentence
<span class="postag">SBJ</span> and <span class="postag">OBJ</span>.  
More complex sentences require more lookup requests and more complex
request with more instance features require more time.

### Server

MBSP has a `Server` class that is used to
start TiMBL or MBT as a background process. A server can be queried by
creating a client. Typically, servers run locally on your own machine
(e.g. at "localhost") but they can also be configured to work with an
IP-address over a network. You can also create new servers from scratch
and work with their responses in Python code.

```python
server = MBSP.Server(
        name,
        host = LOCALHOST,
        port = 6060,
     process = TIMBL,
        ping = None,
    features = {})
```

```python
server.name                # LEMMA
server.host                # LOCALHOST
server.port                # 6062
server.process             # TIMBL
server.features            # {'-f': '/models/em.data', '-m': 'M', '-w': 2, '-k-: 5}
server.ping                # ('c = = = = = = = = = = = = = = = = = = = B ?\n',
                           #  'CATEGORY {ABB-X}\n')
```

```python
server.program             # The shell command used to start the process.
server.pid                 # Process id, needed when stop() is called.
```

```python
server.started             # True when ping request yields ping response.
```

```python
server.start(timeout=60)
server.stop()
```

  - `Server.features` specifies the
    training data file and various options (see the [TiMBL
    manual](http://ilk.uvt.nl/downloads/pub/papers/Timbl_6.2_Manual.pdf)).` `
  - `Server.start()` raises a
    `ServerTimeoutError` when the server
    doesn't start in the given time.  
    `Server.start()` will continually
    check `Server.started` until it
    returns True.
  - `Server.started` determines if the
    server is up and running by sending a ping request.
  - `Server.ping` is a tuple with a
    sample request and its desired (e.g. correct) response.  
    If it is None, `Server.started` just
    sends "`x ?`" and accepts whatever
    response.  
    Sending a sample request and validating the response is the only
    safe way to figure out you are addressing the right server.

#### Stopping a server

When a server is stopped, the background process is killed. The
`Server.pid` process id is stored as a
temporary file so that MBSP can retrieve which servers are up and
running across Python sessions – you don't need to stop and restart a
server each time you run a new Python script.

If the process id is lost (for example, the system did a cleanup of
temporary files), the server background process will have to be killed
manually. The server module has a
`force_quit()` that terminates all
running TiMBL and MBT processes:

```python
MBSP.server.force_quit(processes=(TIMBL, MBT))
```

This only works on Unix-systems though. Otherwise, the TiMBL and MBT
processes will have to be terminated manually from the Windows Task
Manager or Mac OS X's Activity Monitor.

MBSP can also be [configured](/pages/MBSP#configuration) to
automatically stop its servers when Python exits.



-----

## <span id="configuration"></span>Configuration

A number of settings in config.py can be adjusted. Most notably, IP
addresses for the [servers](/pages/MBSP#server)
(`CHUNK`,
`LEMMA`,
`RELATION`,
`PREPOSITION`) can be defined in the
`config.hosts` list, so MBSP can be
configured to work over a network.

By default, the servers will start automatically when MBSP is imported.
Servers are always started at localhost, i.e. the
`config.hosts` list contains the
addresses needed for the *clients*. So if your MBSP is set up to contact
servers over a network,
`config.autostart` should be set to False
so that no servers are started on your own machine. Servers can also be
configured to stop automatically when Python exits, by setting
`config.</span><span class="inline_code">autostop`
to True.

The `config.log` option controls whether
client requests and the servers' responses are logged in the
`MBSP.client.log` dictionary.

### config.py options

<table>
<colgroup>
<col style="width: 33%" />
<col style="width: 33%" />
<col style="width: 33%" />
</colgroup>
<tbody>
<tr class="odd">
<td><span class="smallcaps">Option </span></td>
<td><span class="smallcaps">Default </span></td>
<td><span class="smallcaps">Description </span></td>
</tr>
<tr class="even">
<td>`MODULE`</td>
<td>`os.path.dirname(os.path.abspath(__file__))`</td>
<td>MBSP folder path.</td>
</tr>
<tr class="odd">
<td>`LOCALHOST `</td>
<td>`'localhost' `</td>
<td>Localhost IP address.</td>
</tr>
<tr class="even">
<td>hosts</td>
<td>`[LOCALHOST, LOCALHOST, LOCALHOST, LOCALHOST]`</td>
<td>Server IP addresses. </td>
</tr>
<tr class="odd">
<td>`ports`</td>
<td>`[6061, 6062, 6063, 6064]  `</td>
<td>Server ports.</td>
</tr>
<tr class="even">
<td>`autostart `</td>
<td>`True `</td>
<td>Automatically start servers?</td>
</tr>
<tr class="odd">
<td>`autostop `</td>
<td>`False `</td>
<td>Automatically stop servers? </td>
</tr>
<tr class="even">
<td>`log `</td>
<td>`False `</td>
<td>Log server requests?</td>
</tr>
<tr class="odd">
<td>`verbose`</td>
<td>`True  `</td>
<td>Server startup message? </td>
</tr>
<tr class="even">
<td>`paths `</td>
<td><span class="inline_code">{'timbl': MODULE+'/timbl/Timbl'),<br />
   'mbt': MODULE+'/mbt/Mbt'),<br />
 'mblem': MODULE+'/mblem/mblem_english_bmt'),<br />
'models': MODULE+'/models')} </span></td>
<td>Binaries and training data.</td>
</tr>
<tr class="odd">
<td>`threading`</td>
<td>`False`</td>
<td>See <a href="/pages/MBSP#installation">installation instructions</a>.</td>
</tr>
<tr class="even">
<td>`encoding `</td>
<td>`'utf-8' `</td>
<td>Default character encoding.</td>
</tr>
</tbody>
</table>



-----

## <span id="command_line"></span>Command-line interface

The parser can be run from the command-line by invoking mbsp.py inside
the MBSP library folder. The parsed output is printed in the terminal
window. Note that the servers will not be started automatically, so you
have to start them manually:

```
> cd MBSP
> python mbsp.py start
> python mbsp.py parse -f camelot.txt
> python mbsp.py parse -s "It's only a model."
> python mbsp.py parse xml -s 'It is a silly place.'
> python mbsp.py stop
```

### Command-line options

If no options are given a full parse is executed (i.e. tokenization,
tagging, chunking, relations, prepositions and lemmata). Otherwise, you
need to explicitly list every required option:

|                                      |                                              |                                                |
| ------------------------------------ | -------------------------------------------- | ---------------------------------------------- |
| \-O                                  | \--tokenize                                  | Tokenize the input.                            |
| `-T </span> | <span class="inline_code">--tags `     | Parse part-of-speech tags.                     |
| `-C</span>  | <span class="inline_code">--chunks `   | Parse chunks and PNP tags.                     |
| `-R</span>  | <span class="inline_code">--relations` | Find verb/predicate relations.                 |
| `-A </span> | <span class="inline_code">--anchors`   | Find PP-attachments.                           |
| `-L</span>  | <span class="inline_code">--lemmata `  | Find word lemmata.                             |
| `-f </span> | <span class="inline_code">--file`      | Input filename.                                |
| \-s                                  | `--string `   | Input string.                                  |
| `-e</span>  | <span class="inline_code">--encoding`  | Specify character encoding (utf-8 by default). |
| `-v ` | \--version                                   | Current version of MBSP.                       |

Short options can be concatenated, e.g.:
<span class="inline_code">python mbsp.py parse -OTL -f
camelot.txt</span>



-----

## <span id="customization"></span>Extending MBSP

### Event framework

MBSP has a built-in event framework that offers a convenient way to
customize the module. For example, each completed step in the
[parser](/pages/MBSP#parser) fires an event. A user-defined event
handler can be assigned to an event, instead of messing around in the
source code.

Server event handlers take a `Server`
object as input. Events are fired when a server is registered in a
`Servers` group (see below), or when a
server is successfully started or stopped.

```python
def event_handler(server):
    return None
```

```python
MBSP.events.server.on_register = event_handler
MBSP.events.server.on_start = event_handler
MBSP.events.server.on_stop = event_handler
```

Parser event handlers take a
`TokenString` object (see below) as input
and return the modified `TokenString`.
Events are fired when each step in the parsing process is completed (for
example, tokenization is done).

```python
def event_handler(tokenstring):
    return tokenstring
```

```python
MBSP.events.parser.on_tokenize = event_handler
MBSP.events.parser.on_parse_tags_and_chunks = event_handler
MBSP.events.parser.on_parse_prepositions = event_handler
MBSP.events.parser.on_parse_relations = event_handler
MBSP.events.parser.on_parse_pp_attachments = event_handler
MBSP.events.parser.on_lemmatize = event_handler
```

### Customizing the parser

Suppose you need to correct some part-of-speech tags. Since the
part-of-speech tag influences the relation and anchor tag annotation,
you'd need to do this somewhere halfway down the parsing process. This
is possible by injecting an event handler – without modifying the source
code and thus keeping it easy to install package updates:

```python
>>> def my_tagger_chunker(tokenstring):
>>>     T = tokenstring.split()
>>> i = T.tags.index(MBSP.PART_OF_SPEECH)
>>> for sentence in T:
>>> for token in sentence:
>>> print token[i] # modify POS-tag here
>>> return T.join()
>>>
>>> MBSP.events.parser.on_parse_tags_and_chunks = my_tagger_chunker
```

Since the output of the event handler is then processed further, it
needs to maintain the order of tags and it can't delete tags (they are
still needed by the parser to determine other tags).

### Customizing the parser output

The output of the `parse()` command is a
string of sentences in which each token has been annotated with the
requested tags. This string is in fact a
`TokenString` object that behaves as a
Python string, but with extra functionality. Most notably, it has a
`TokenString.split()` method that yields
a `TokenList` object: a list of
sentences, where each sentence is a list of tokens, in which each token
is a list of tags.

```python
tokenstring = MBSP.TokenString(string, tags=[WORD])
```

```python
tokenstring.tags              # [WORD, POS, CHUNK, PNP, RELATION, ANCHOR, LEMMA]
tokenstring.split(sep=TOKENS) # Yields a TokenList.
tokenstring.copy()
```

```python
tokenlist = MBSP.TokenList(sentences, tags)
```

```python
tokenlist.tags
tokenlist.tags.insert(i, tag, values=None)
tokenlist.tags.append(tag, values=None)
tokenlist.tags.remove(tag)
tokenlist.tags.pop(i)
tokenlist.tags.swap(tag1, tag2)
```

```python
tokenlist.join()              # Yields a TokenString.
tokenlist.copy()
tokenlist.reduce(tags=[])
tokenlist.filter(
        word = None,
         tag = None,
       chunk = None,
    relation = None,
      anchor = None,
       lemma = None)
```

The `TokenString` facilitates the
conversion from a tagged string to a list – where tokens can then be
manipulated. The `TokenList.tags` list
not only stores the order of tags in each token, it also keeps the
tokens in synch. If you delete an item from
`TokenList.tags`, all tokens in each
sentence are automatically modified as well. In the same way,
`TokenList.tags.append()` has an
additional `values` parameter where you
can enter the values of the new tag for each token in each sentence
(<span class="postag"> </span>by default,
<span class="postag">O</span>).

For example:

```python
>>> s = MBSP.parse('I eat pizza')
>>> s = s.split()
>>> s.tags.append('semantic', values=[['person', 'action', 'food']])
>>> s = s.join()
>>> print s

I/PRP/I-NP/O/NP-SBJ-1/O/i/person eat/VBP/I-VP/O/VP-1/O/eat/action
pizza/NN/I-NP/O/NP-OBJ-1/O/pizza/food
```

When you create a [parse tree](/pages/MBSP#tree) from this output, the
*semantic* tag will end up in
`Word.custom_tags`.

If you want to insert a tag from one
`TokenString` into another, you can use
`TokenString1.tags.pop()`. It extracts
(and removes) the tag value from each token. You can use this return
value for the `values` parameter in the
other `TokenString2.tags.append()`.

`TokenList.reduce()` returns a copy with
the given tags removed from all tokens. <span class="inline_code">  
TokenList.filter()</span> returns a list of all tokens that match the
given criteria. Wildcards can be used at the head, tail or middle of a
constraint:

```python
>>> s = MBSP.parse('I eat pizzas with a fork.')
>>> print s.split().filter(tag="NN*")

[[u'pizzas', u'NNS', u'I-NP', u'O', u'NP-OBJ-1', u'O', u'pizza'],
 [u'fork', u'NN', u'I-NP', u'I-PNP', u'O', u'P1', u'fork']]
```

### Customizing the servers

MBSP's servers are grouped in a `Servers`
object: a Python list with some additional functionality:

  - `Servers` can automatically start and
    stop a [server](/pages/MBSP#server) (i.e.
    `Server` object) that is added to the
    group.
  - `Servers` will check that all servers
    in the group use a different port and a different name.
  - ` `When a server is added, its
    `Server.group` attribute will refer
    to the `Servers` object.
  - When a server is added, the `on_register` event will be fired.

<!-- end list -->

```python
servers = MBSP.Servers(start=False, stop=False)
```

```python
servers.append(server)
```

```python
servers.[server_name]      # Retrieve a server by name.
```

```python
servers.started            # True when all servers in the group have started.
servers.start(timeout=60)
servers.stop()
```

The correct way to install a custom server is to add it to the module's
`active_servers` group to ensure that it
is started and stopped together with the other servers (e.g. when
`MBSP.stop()` is called).

Assume we have a tagger trained for biomedical use that overrides the
default part-of-speech tags:

```python
>>> import MBSP
>>> MBSP.active_servers.append(
>>>    MBSP.Server(
>>>            name = 'biomedical_pos',
>>>            port = 6065,
>>>         process = MBSP.MBT,
>>>        features = {'-s' : 'biopos/biopos.settings')}))
```

We can contact the server with an event, after MBSP is done tagging and
chunking:

```python
def update_pos(tokenstring):
>>>     client = MBSP.Mbt(port=6065)
>>>     s1 = tokenstring.split()
>>>     s2 = s1.reduce([MBSP.WORD])
>>>     s2 = MBSP.TokenString(client.send(s2.join()), tags=[MBSP.WORD, MBSP.POS])
>>>     s2 = s2.split()
>>>     s2.tags.append(MBSP.CHUNK, values=s1.tags.pop(s1.tags.index(MBSP.CHUNK)))
>>>     client.disconnect()
>>>     return s2.join()
>>>
>>> MBSP.events.parser.on_parse_tags_and_chunks = update_pos
```

We have installed a new server and then contact it in the
`update_pos()` event, right after MBSP
has finished tagging and chunking with the default servers. The event
extracts the original words in the sentence and feeds them to our
biomedical MBT server. We append the original chunk tags to the updated
output and pass it back to MBSP. MBSP will continue to look for
relations and prepositions with the updated tags.

#### Replacing a default server before it starts

Assume you want to *replace* a default server with one of your own. If
MBSP's servers are [configured](/pages/MBSP#configuration) to start
automatically, there is no way to stop them from loading before you can
replace them. The way to do this is to disable MBSP's
`autostart` feature, add replacement
servers to `active_servers`, and then
implement your own autostart in your own script.



-----

## <span id="export"></span>Exporting to XML and NLTK

With the `xml()` command the output of
the `parse()` command can be dumped as an
XML string:

```python
MBSP.xml(string, token=[WORD, POS, CHUNK, PNP, RELATION, ANCHOR, LEMMA])
```

```python
MBSP.Text.xml           # Returns the Text as an XML string.
```

```python
MBSP.Text.from_xml(xml) # Returns a new Text from the given XML string.
```

The XML output is
a <span class="inline_code" style="font-family: Courier, monospace; font-size: 12px;">\<text\></span> element
consisting of one or
more <span class="inline_code" style="font-family: Courier, monospace; font-size: 12px;">\<sentence\></span> elements.
Each \<sentence\> has a
unique <span class="inline_code" style="font-family: Courier, monospace; font-size: 12px;">id</span>attribute,
a <span class="inline_code" style="font-family: Courier, monospace; font-size: 12px;">token</span> descriptor
and consists
of <span class="inline_code" style="font-family: Courier, monospace; font-size: 12px;">\<chunk\></span> and <span class="inline_code" style="font-family: Courier, monospace; font-size: 12px;">\<chink\></span> elements.
A <span class="inline_code" style="font-family: Courier, monospace; font-size: 12px;">\<chunk\></span> can
have
a <span class="inline_code" style="font-family: Courier, monospace; font-size: 12px;">type</span> attribute
(e.g.<span class="postag" style="font: normal normal bold 0.85em/normal Arial; padding-top: 0px; padding-right: 1px; padding-bottom: 0px; padding-left: 1px;">NP</span>, <span class="postag" style="font: normal normal bold 0.85em/normal Arial; padding-top: 0px; padding-right: 1px; padding-bottom: 0px; padding-left: 1px;">VP</span>)
and/or
a <span class="inline_code" style="font-family: Courier, monospace; font-size: 12px;">relation</span> attribute
(e.g. <span class="postag" style="font: normal normal bold 0.85em/normal Arial; padding-top: 0px; padding-right: 1px; padding-bottom: 0px; padding-left: 1px;">SBJ</span>).
In this case it can also have
an <span class="inline_code" style="font-family: Courier, monospace; font-size: 12px;">of</span> attribute
with
the <span class="inline_code" style="font-family: Courier, monospace; font-size: 12px;">id</span> of
the
related <span class="postag" style="font: normal normal bold 0.85em/normal Arial; padding-top: 0px; padding-right: 1px; padding-bottom: 0px; padding-left: 1px;">VP</span>chunk.
 A <span class="inline_code" style="font-family: Courier, monospace; font-size: 12px;">\<chunk
type=”PNP”\></span> element can also have
an <span class="inline_code" style="font-family: Courier, monospace; font-size: 12px;">of</span> attribute,
with
the <span class="inline_code" style="font-family: Courier, monospace; font-size: 12px;">anchor</span> of
the chunk to which it is attached.
A <span class="inline_code" style="font-family: Courier, monospace; font-size: 12px;">\<chunk\></span> consists
of <span class="inline_code" style="font-family: Courier, monospace; font-size: 12px;">\<word\></span> elements,
or
other <span class="inline_code" style="font-family: Courier, monospace; font-size: 12px;">\<chunk\></span> elements
in the case of
a <span class="postag" style="font: normal normal bold 0.85em/normal Arial; padding-top: 0px; padding-right: 1px; padding-bottom: 0px; padding-left: 1px;">PNP</span>.
A <span class="inline_code" style="font-family: Courier, monospace; font-size: 12px;">\<word\></span> element
contains the actual word and can have
a <span class="inline_code" style="font-family: Courier, monospace; font-size: 12px;">type</span> attribute
(e.g. <span class="postag" style="font: normal normal bold 0.85em/normal Arial; padding-top: 0px; padding-right: 1px; padding-bottom: 0px; padding-left: 1px;">NN</span>)
and
a <span class="inline_code" style="font-family: Courier, monospace; font-size: 12px;">lemma</span> attribute.
If MBSP was extended with custom tags these will be listed in
the <span class="inline_code" style="font-family: Courier, monospace; font-size: 12px;">\<sentence\>
token</span> attribute and
as <span class="inline_code" style="font-family: Courier, monospace; font-size: 12px;">\<word\></span> attributes.

For example:

```python
s = MBSP.parse('I eat pizza with a fork.')
print(MBSP.xml(s))
```

<span class="inline_code">\<?xml version="1.0" encoding="UTF-8"?\>  
</span><span style="font-family: Courier, monospace; font-size: 12px;">\<text\>  
</span><span style="font-family: Courier, monospace; font-size: 12px;">\<sentence
id="1"   
</span><span style="font-family: Courier, monospace; font-size: 12px;">  
    token="word, part-of-speech, chunk, preposition, relation, anchor,
lemma"\>  
</span><span style="font-family: Courier, monospace; font-size: 12px;">  
 \<chunk type="NP" relation="SBJ" of="1.1"\>  
</span><span style="font-family: Courier, monospace; font-size: 12px;">  
     \<word type="PRP" lemma="i"\>I\</word\>  
</span><span style="font-family: Courier, monospace; font-size: 12px;">  
 \</chunk\>  
</span><span style="font-family: Courier, monospace; font-size: 12px;">  
 \<chunk type="VP" id="1.1" anchor="1.A1"\>  
</span><span style="font-family: Courier, monospace; font-size: 12px;">  
     \<word type="VBP" lemma="eat"\>eat\</word\>  
</span><span style="font-family: Courier, monospace; font-size: 12px;">  
 \</chunk\>  
</span><span style="font-family: Courier, monospace; font-size: 12px;">  
 \<chunk type="NP" relation="OBJ" of="1.1"\>  
</span><span style="font-family: Courier, monospace; font-size: 12px;">  
     \<word type="NN" lemma="pizza"\>pizza\</word\>  
</span><span style="font-family: Courier, monospace; font-size: 12px;">  
 \</chunk\>  
</span><span style="font-family: Courier, monospace; font-size: 12px;">  
 \<chunk type="PNP" of="1.A1"\>  
</span><span style="font-family: Courier, monospace; font-size: 12px;">  
     \<chunk type="PP"\>  
</span><span style="font-family: Courier, monospace; font-size: 12px;">  
         \<word type="IN" lemma="with"\>with\</word\>  
</span><span style="font-family: Courier, monospace; font-size: 12px;">  
     \</chunk\>  
</span><span style="font-family: Courier, monospace; font-size: 12px;">  
     \<chunk type="NP"\>  
</span><span style="font-family: Courier, monospace; font-size: 12px;">  
         \<word type="DT" lemma="a"\>a\</word\>  
</span><span style="font-family: Courier, monospace; font-size: 12px;">  
         \<word type="NN" lemma="fork"\>fork\</word\>  
</span><span style="font-family: Courier, monospace; font-size: 12px;">  
     \</chunk\>  
</span><span style="font-family: Courier, monospace; font-size: 12px;">  
 \</chunk\>  
</span><span style="font-family: Courier, monospace; font-size: 12px;">  
 \<chink\>  
</span><span style="font-family: Courier, monospace; font-size: 12px;">  
     \<word type="." lemma="."\>.\</word\>  
</span><span style="font-family: Courier, monospace; font-size: 12px;">  
 \</chink\>  
</span><span style="font-family: Courier, monospace; font-size: 12px;">\</sentence\>  
</span><span style="font-family: Courier, monospace; font-size: 12px;">\</text\></span>

### Exporting to NLTK

The `MBSP.tree` module has
an `nltk_tree()` command that returns
an `nltk.tree.Tree` object from the given
`MBSP.Sentence` object. This way the
output from MBSP can be integrated into [NLTK](http://nltk.org) for
further processing.

```python
s = MBSP.parse('I eat pizza with a fork.')
s = MBSP.split(s)
print MBSP.tree.nltk_tree(s.sentences[0])

>>> (S
      (NP (PRP I))
      (VP (VBP eat) (PNP (PP (IN with)) (NP (DT a) (NN fork))))
      (NP (NN pizza)))
```

</div>

NLTK needs to be installed on your system for this to work.

### Exporting to GraphViz

The `MBSP.tree` module has a
`graphviz_dot()` command that returns a
string in the DOT language (a simple way to describe graphs) from the
given `MBSP.Sentence` object. DOT files
can be visualized with [GraphViz](http://graphviz.org), a free
application for drawing graphs and exporting them as images (PDF, PNG,
...)

```python
>>> s = MBSP.parse('I eat pizza with a fork.')
>>> s = MBSP.split(s)
>>> f = open('pizza.dot', 'w')
>>> f.write(MBSP.tree.graphviz_dot(s.sentences[0])
>>> f.close()
```

When `pizza.dot` is then openend in
GraphViz it displays the following syntax tree:

![](/media/MBSP_graphviz.jpg)

-----

## <span id="license"></span>Licensing

MBSP uses a duel license model and offers licenses for two distinct
purposes – commercial and open source development.

  - **Open source**: for open source purposes MBSP uses the GNU General
    Public License version 3
    ([GPLv3](http://www.gnu.org/licenses/gpl.html)). It requires that
    you contribute to the open source community by placing your
    application that uses MBSP under an open source license (e.g.
    GPLv3). This option secures all users the rights to obtain the
    application's full source code, modify it, and redistribute it.

<!-- end list -->

  - **Commercial**: for commercial purposes you can directly contact
    prof. Walter Daelemans (*walter.daelemans at uantwerpen.be*). This
    requires that you contribute to the continued development of the
    product by purchasing a commercial license. This option secures you
    the right to distribute your application under the license terms of
    your choice
