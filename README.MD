## MBSP for Python 2.5

MBSP is an approach to text analysis based on the TiMBL and MBT memory based learning applications developed at the Computational Linguistics & Psycholinguistics Group, University of Antwerp, Belgium and the Induction of Linguistics Research Group, Tilburg University, The Netherlands. It provides tools for Tokenization and Sentence Splitting, Part of Speech Tagging, Chunking, Lemmatization, Relation Finding and Prepositional Phrase Attachment. The general English version of MBSP has been trained on data from the Wall Street Journal corpus.
http://www.clips.ua.ac.be/pages/MBSP

Reference:
```
Daelemans, W. and A. van den Bosch (2005)
"Memory-Based Language Processing."
Cambridge: Cambridge University Press.
```

### Version

1.4

### License

GNU General Public License, see LICENSE.txt for further details.

### Acknowledgements

This version of MBSP has been developed by the computational linguistics group of CLiPS (Computational Linguistics & Psycholinguistics, department of Linguistics, University of Antwerp, Belgium) on the basis of earlier versions developed at the University of Antwerp and Tilburg University.

Contributing authors:
- Walter Daelemans
- Jakub Zavrel
- Sabine Buchholz
- Jorn Veenstra
- Antal van den Bosch
- Ko van der Sloot
- Bertjan Busser
- Erik F. Tjong Kim Sang
- Jo Meyhi
- Vincent Van Asch
- Tom De Smedt

Many thanks go to the people who have contributed by giving us feedback and reporting bugs:
Frederik Vaassen, Max De Wilde, Rob Speer, Jamison Miller, Avishay Zilka.

### Modes

You have two options if you want to use MBSP.
Run the TiMBL and MBT servers locally or use servers on another host.
You can set host IP-addresses in config.py.

### Binaries

This MBSP distribution contains compiled TiMBL, MBT and MBLEM binaries for Mac OS X 10.5 but this may not work on your machine.
See 1. and 2. if this is the case.
Otherwise you can skip this section.

MBT is a memory-based tagger-generator and tagger in one. The tagger-generator part can generate a sequence tagger on the basis of a training set of tagged sequences; the tagger part can tag new sequences. MBT can, for instance, be used to generate part-of-speech taggers or chunkers for natural language processing.
http://ilk.uvt.nl/mbt/

TIMBL: Memory-Based Learning (MBL) is a robust machine-learning method applicable to a wide range of tasks in Natural Language Processing (NLP) and other areas.
http://ilk.uvt.nl/timbl/

1. Everything on localhost
- You need to compile the MBLEM lemmatizer.
- See README in the /mblem directory.
- MBSP will start servers locally on your machine, so you need TiMBL and MBT.
- See README in the folders /timbl and /mbt to compile the binaries.
- You can also try to run setup.py, which compiles everything automatically.

2. Use servers running on another host
- You need to compile the lemmatizer.
- See README in the lemmatizer directory.
- You don't need TiMBL and MBT.

### Python

Python-scripts are written for Python version 2.5 and up.
Version 2.4 should work as well.

### Configuration

Always check `config.py` to see if the settings are configured to your needs.

MBSP starts four data servers (CHUNK: 80MB, LEMMA: 10MB, RELATION: 160MB, PREPOSITION: 210MB) but only the CHUNK server (which gives you the part-of-speech tags) is mandatory. The optional servers can be disabled in config.py to reduce the memory usage, for example:
`>>> servers = ['chunk', 'lemma']`

### Usage

MBSP for Python 2.5+ is a Python package so you can import it into your python scripts if the folder is placed in your python path. Normally, you want to place it in the folder called /site-packages inside your python distribution.

Start your python interpreter and begin testing:
```python
import MBSP

MBSP.parse('The red cat has a nice hat.')
>>> u'The/DT/I-NP/O/NP-SBJ-1/the red/JJ/I-NP/O/NP-SBJ-1/red cat/NN/I-NP/O/NP-SBJ-1/cat
has/VBZ/I-VP/O/VP-1/have a/DT/I-NP/O/NP-OBJ-1/a nice/JJ/I-NP/O/NP-OBJ-1/nice hat/N
N/I-NP/O/NP-OBJ-1/hat ././O/O/O/.'
```

The parser returns unicode strings.

The TiMBL and MBT servers are started automatically on the first run. This can be configured in config.py.
If you also want them to stop automatically when Python quits, this can be configured too.

Otherwise you need to kill them manually when you are done:
```python
import MBSP
MBSP.stop()
```

# Contact

Vincent Van Asch, vincent.vanasch@ua.ac.be
Tom De Smedt, tom@organisms.be
