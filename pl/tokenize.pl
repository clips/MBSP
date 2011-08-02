#!/usr/bin/perl -w
# -*- Mode: CPerl -*-

# $Source: /home/biomint/cvsrep/biomint-tool/tokenizer/src/pl/tokenize.pl,v $
# $Revision: 1.17 $
# $Author: jmeyhi $
# $Date: 2005/11/25 17:26:11 $

# tokenize: divide text in words and sentences

# 19980601 buchholz@kub.nl, erikt@uia.ua.ac.be
# version date: 20011029

use strict;
use warnings;
use Getopt::Long;
use Pod::Usage;

# {{{ variables

my $program = $0;

my $uc_alpha = "A-Z";		# definition of an upper case letter
my $lc_alpha = "a-z";		# definition of a lower case letter

my %coord = ();
my %abbr = ();
my %apo = ();
my %spec1 = ();
my %spec2 = ();
my %spec2_1 = ();
my %spec2_2 = ();
my %pref = ();
my %suff = ();
my $max_pref = 0;
my $max_suff = 0;
my %ordinals = ();
my %meas = ();
my %money = ();
my %user_defined_tags = ();
my %predefined_tags = ();

my $protein_before_singlechar_regex = "";

# default options
my $verbosity = 2;		# v : verbosity level
my $beginMarker = "<utt>";	# b : begin utterance marker
my $endMarker = "</utt>";	# e : end utterance marker
my $return = "0";		# r : print returns
my $lang = "eng";		# l : language
my $path = "resources";		# p : path to language resources

# }}}

# {{{ read Command Line options
GetOptions("help|?" => sub { pod2usage(1); },
	   "verbose=i" => \$verbosity,
	   "begin=s" => \$beginMarker,
	   "end=s" => \$endMarker,
	   "return" => \$return,
	   "language=s" => \$lang,
	   "path=s" => \$path,
          ) or pod2usage (1);
# }}}

# {{{ process CL options
if ($beginMarker eq '\n') {
  $beginMarker = "\n";
} elsif ($beginMarker eq ' ') {
  $beginMarker = "";
}
if ($endMarker eq '\n') {
  $endMarker = "\n";
} elsif ($endMarker eq ' ') {
  $endMarker = "";
}
# }}}

# {{{ runtime messages

if ( $verbosity >= 2 ) {
  print STDERR "-- $program INF: tokenizing the text.\n";
}
if ( $verbosity >= 3 ) {
  print STDERR "-- $program INF: Language is \"$lang\"\n";
  print STDERR "-- $program INF: Newline switch is \"$return\"\n";
  print STDERR "-- $program INF: Begin marker is \"$beginMarker\"\n";
  print STDERR "-- $program INF: End marker is \"$endMarker\"\n";
  print STDERR "-- $program INF: Resource path is \"$path\"\n";
}

# }}}

# {{{ Main
# {{{ initialize known lists
&initialize();
# }}}

# {{{ main variables
my ($add_end_utt,$hyphened,$line,$word,
    @last_line,@prefixes,@suffixes,@words,@words2,
    %sgml);

my $counter = 0;
my $in_utt = 0;
my $last_hyphened = "";
# }}}

# {{{ read and process STDIN
while (defined($line=<STDIN>)) {

  # {{{ counter
  $counter++;
  #print STDERR "$counter\r";
  # }}}

  # {{{ preprocessing cleanup
  chomp($line);
  $line =~ s/^\s+//;		# delete initial blanks
  $line =~ s/\s+$//;		# delete trailing blanks
  $line =~ s/\(/ \&openparen; /g;  # to work around a bug adding another <utt> at the end of a sentence
  $line =~ s/\)/ \&closeparen; /g; # this is undone by the special_words file in resources
  $line =~ s/([\s]+)(\&(open|close)paren;)(\s+)/ $2 /g; # make sure parenthesis are always surrounded by exactly 1 space
  # }}}

  @words = split(/\s+/,$line);
  @words2 = ();
  $hyphened = "";

  # {{{ process all words
  while (@words>0) {
    $word = shift(@words);
    @prefixes = ();
    @suffixes = ();
    $add_end_utt = 0;
    $word = &process_word($word); # tokenize focus
    $in_utt = &check_utt1($in_utt,$word); # insert <utt> or </utt>
    push(@words2,@prefixes,$word,@suffixes); # append new material
    $in_utt = &check_utt2($add_end_utt,$in_utt,$word); # insert </utt>
  }				# end : while (@words>0)
  # }}}

  # {{{ join hyphened word from previous line
  &check_hyphen();
  # }}}

  # {{{ process empty lines
  if ($line =~ /^\s*$/		# empty line
      and $in_utt == 1) {	# still inside utterance
    push(@last_line,"</utt>");	# marks end of utterance
    $in_utt = 0;
  }
  # }}}

  if ($#last_line >= 4 and
      $last_line[0] eq "<utt>" and $last_line[1] =~ /^[0-9]+$/ and
      $last_line[2] eq "." and $last_line[3] eq "</utt>" and
      $last_line[4] eq "<utt>") {
    # result table: added 20030918 ET
    $last_line[4] = $last_line[1].$last_line[2];
    $last_line[3] = "<utt>";
    shift(@last_line);
    shift(@last_line);
    shift(@last_line);
  }

  # {{{ print the previously processed line
  if (@last_line) {		# not defined for first line
    &print_line(@last_line);	# print previous line
  }
  # }}}

  @last_line = @words2;
  $last_hyphened = $hyphened;
}
# }}}

# {{{ handle hyphenation at end of last line
if ($last_hyphened ne "") { # no real hyphenation possible on last line
  $last_line[$#last_line] .= " -"; # add separated -
}
# }}}

&print_line(@last_line);	# print last line of document
# }}}

exit(0);

# {{{ Subs

# {{{ abbr(): read in the known abbreviations

sub abbr {
  my ($line);

  open(FH,"<$path/$lang/abbr") or 
    die "!! $program ERR: Cannot open $path/$lang/abbr!\n";
  while (defined($line=<FH>)) {
    if (substr($line,0,1) eq "#") {
      next;
    }				# comment line
    chomp($line);
    $abbr{$line} = 1;
  }
  close(FH);
}

# }}}

# {{{ protein_before_singlechar()

sub protein_before_singlechar {
  my ($line);

  open(FH,"<$path/$lang/protein_before_singlechar") or 
    die "!! $program ERR: Cannot open $path/$lang/protein_before_singlechar!\n";
  while (defined($line=<FH>)) {
    if (substr($line,0,1) eq "#") {
      next;
    }				# comment line
    chomp($line);
    $protein_before_singlechar_regex .= "|$line";
  }
  close(FH);
   
  # Remove first '|'
  $protein_before_singlechar_regex =~ s/^\|//;

  #   print STDERR "$protein_before_singlechar_regex\n";

}

# }}}

# {{{ apostrof(): read in the known words starting with "'"

# e.g. 's morgens => 's morgens
sub apostrof {
  my ($line);
  open(FH,"<$path/$lang/apostrophe") or 
    die "!! $program ERR: Cannot open $path/$lang/apostrophe!\n";
  while (defined($line=<FH>)) {
    if (substr($line,0,1) eq "#") {
      next;
    }				# comment line
    chomp($line);
    $apo{$line} = 1;
  }
  close(FH);
}

# }}}

# {{{ apply_files()
sub apply_files {
  my ($i,$p,$s,$word);

  $word = shift(@_);
  # {{{ special suffixes
  #                   it's => it 's / Peter's => Peter 's / 
  #                   dat-ie => dat ie/hij
  for ($i=1;$i<=$max_suff and $i<length($word);$i++) {
    $s = substr($word,length($word)-$i);
    if (exists($suff{$s})) {
      unshift(@suffixes,$s);	# store suffix
      $word = substr($word,0,length($word)-$i);
      last;
    }
  }
  # }}}
  # {{{ special prefixes: l'avoir => l' avoir
  for ($i=1;$i<=$max_pref and $i<length($word);$i++) {
    $p = substr($word,0,$i);
    if (exists($pref{$p})) {
      push(@prefixes,$p);	# store prefix
      $word = substr($word,$i);
      last;
    }
  }
  # }}}
  # {{{ split f5,-   hfl50   DM0,50   BEF7,50
  if (($word =~ /^([a-zA-Z]+)(\.*)([0-9][-=0-9.,]*)$/ or
       $word =~ /^([a-zA-Z]+)(\.*)([-=0-9.,]*[0-9])$/) and
      exists($money{$1})) {
    push(@prefixes,"$1$2");
    $word = $3;
  }
  # }}}
  # {{{ split 180C  350F  12oz  375g  2.5cm  450-900g  1-2lb  170,500km  etc.
  if ($word =~ /^([-0-9.,]+)([a-zA-Z]+)$/
      and (exists($meas{$2})
           or exists($money{$2}) ) ) {
    unshift(@suffixes,$2);
    $word = $1;
  }
  # }}}
  # {{{ split 450-900 etc.
  if ($word =~ /^('?[0-9.,]+)(-+)('?[0-9.,]+([.,]-)?)$/) {
    unshift(@suffixes,$3);
    unshift(@suffixes,$2);
    $word = $1;
  }
  # }}}

  return($word);
}
# }}}

# {{{ check_utt1()
sub check_utt1 {
  my ($in_utt,$word);

  $in_utt = shift(@_);
  $word = shift(@_);
  if (not &is_tag($word)) {	# word
    if ($in_utt == 0) {		# outside utterance
      push(@words2,"<utt>");	# word starts an utterance
      $in_utt = 1;
    }
  } else {			# tag
    if ($in_utt == 1		# still inside utterance
	and $sgml{&is_tag($word)} eq "ends_utt") { 
      # tag marks end of utterance
      if (@words2 == 0) {	# tag is first in line
	push(@last_line,"</utt>"); # insert marker on previous line
      } else {
	push(@words2,"</utt>");	# insert marker on same line
      }
      $in_utt = 0;
    }
  }
  return($in_utt);
}
# }}}

# {{{ check_utt2()
sub check_utt2 {
  my ($add_end_utt,$in_utt,$word);

  $add_end_utt = shift(@_);
  $in_utt = shift(@_);
  $word = shift(@_);
  if (not &is_tag($word)) {	# focus is word
    if ($add_end_utt == 1) {	# word was sentence final punctuation
      push(@words2,"</utt>");	# word ends an utterance
      $in_utt = 0;
    }
  }
  return($in_utt);
}
# }}}

# {{{ check_hyphen()
sub check_hyphen {
  if ($last_hyphened ne "") {
    if (@words2 == 0) {		# empty line
      $last_line[$#last_line] .= " -"; # add separated -
    } elsif (exists($coord{lc($words2[0])}) # "netto- en bruttoloon"
	     or ($words2[0] =~ /^(.+)-/
		 and exists($coord{lc($1)}))) {	# "schiet- en-vechtgeval"
      $last_line[$#last_line] .= "-"; # don't separate -
    } elsif ($last_hyphened =~ /[$uc_alpha]$/) { # ending in upper case: 
      # "DEA-invloed"
      pop(@last_line);		# delete word in
      # last sentence
      $words2[0] = $last_hyphened."-".$words2[0]; # append at current 
      # sentence
    } elsif ($words2[0] =~ /^[$lc_alpha]/) { # normal case: "ka- \n mer"
      # -> "kamer"
      pop(@last_line);
      $words2[0] = $last_hyphened.$words2[0];
    } elsif ($words2[0] =~ /^[0-9$uc_alpha]/) {	# starting with upper case:
      # "Groot-Brittannie"
      pop(@last_line);
      $words2[0] = $last_hyphened."-".$words2[0];
    } else {			# hyphen used as punctuation
      $last_line[$#last_line] .= " -"; # add separated -
    }
  }
}
# }}}

# {{{ coord(): read in the known coordinations: netto- [en] bruttoloon
sub coord {
  my ($line);

  open(FH,"<$path/$lang/coord") or 
    die "!! $program ERR: Cannot open $path/$lang/coord!\n";
  while (defined($line=<FH>)) {
    if (substr($line,0,1) eq "#") {
      next;
    }				# comment line
    chomp($line);
    $coord{$line} = 1;
  }
  close(FH);
}
# }}}

# {{{ initialize()
sub initialize {
  &coord();			# netto- [en] bruttoloon
  &abbr();			# ds ir
  &protein_before_singlechar(); # peri-kappa B
  &apostrof();			# 's 't
  &spec();			# cannot
  &prefixes();			# (not used)
  &suffixes();			# -ie
  &ordinals();			# e de ste
  &measures();			# cm kg
  &money();			# hfl DM
  &sgmltags();			# b p br
  &sgmlentalpha();		# eacute Acirc
  &sgmlentnonalpha();		# nbsp gt
}
# }}}

# {{{ is_abbreviation(): special problem of period: abbreviation or punctuation?
sub is_abbreviation {
  my ($tmp1,$tmp2);

  $tmp1 = shift(@_);
  $tmp2 = shift(@_);

  #   print STDERR "\$tmp1 = $tmp1\n";
  #   print STDERR "\$tmp2 = $tmp2\n";

  # punctuation is period
  if ($tmp2 eq "."
       # no abbreviation-period if other punctuation in front
       and $tmp1 !~ /[-#`'"(){}\[\]!?:;,@\$%^&*+|=~<>\/\\_]$/
       # list of known abbreviations with period
       and (exists($abbr{$tmp1})
           # probably abbreviation if next word (if it exists) 
           # starts with at least 2 lower case letters # not: bla. <p>
           # and if the current word contains no more than 4 characters
           or (@words>0 and 
	       $tmp1 !~ /^.{4,}$/ and
               $words[0] =~ /^[-`'"(){}\[\]!?:;,@\$%^*+|=~>\/\\]*[a-z]{2}/) #'`
           # one single capital letter is probably second initial,
	   # unless it is preceded by (part of) a protein name
           or (($tmp1 =~ /^[A-Z]$/) and
               ((@words2>0 and 
		 ! &is_protein_before_singlechar($words2[$#words2])) or
		((@words2 == 0) and (@last_line>0 and 
		 ! &is_protein_before_singlechar($last_line[$#last_line])))
		)
              )
           # probably abbreviation if one of ,;:?! follows
           or (@suffixes>0 and $suffixes[0] =~ /^,;:?!$/)
           # probably abbreviation if another period inside word: e.g. A.M.
           or $tmp1 =~ /^[A-Za-z]+(\.[-A-Za-z])+$/
           # special case of ordinal numbers (if indicated in file "ordinals")
           or (exists($ordinals{"."}) and $tmp1 =~ /^[0-9]+$/)
          )
      ) {
    return 1;
  } else {
    return 0;
  }
}
# }}}

# {{{ is_protein_before_singlechar()
sub is_protein_before_singlechar {
  my ($previous) = @_;

  if ($previous =~ m/(${protein_before_singlechar_regex})$/io) {
    return 1;
  } else {
    return 0;
  }
}
# }}}

# {{{ is_tag()
sub is_tag {
  my ($word);

  $word = shift(@_);
  if ($word =~ /^<([^<>]*)>$/) {
    return(lc($1));
  } else {
    return(0);
  }
}
# }}}

# {{{ measure(): read in the known measurements
# e.g. 5km => 5 km
sub measures {
  my ($line);

  open(FH,"<$path/etc/measure") or 
    die "!! $program ERR: Cannot open $path/etc/measure!\n";
  while (defined($line=<FH>)) {
    if (substr($line,0,1) eq "#") {
      next;
    }				# comment line
    chomp($line);
    $meas{$line} = 1;
  }
  close(FH);
}
# }}}

# {{{ missing_space(): punctuation with missing space
#
# e.g.
# gerekend.Het
# gerekend.''Het
# gerekend''.Het
# gerekend).Het
#
# house,and
# house;and
# house:and
# etc.
#
# not: U.S.   i.e.   S.Buchholz@kub.nl
sub missing_space {
  my ($word,$first,$last);

  $word = shift(@_);
  if ($word !~ /@|www|http|ftp|gopher|URL|htm/i and
      not exists($abbr{$word}) and
      ($word !~ /^[\"\']/ and $word !~ /[\"\']$/) and
      # no internet adres (like S.Buchholz@kub.nl)
      $word =~ /^([^.]*[0-9$lc_alpha$uc_alpha])([\)'"]*\.[\)'"]*)([$uc_alpha][^.]*)$/o) {
    # abc.Abc # added first uc_alpha 20021226
    unshift(@words,$3);
    $word = $1.$2;	   # split punctuation from word in later step
  }
  if ($word !~ /@|www|http|ftp|gopher|URL|htm/i and
      not exists($abbr{$word})) {
    # 20021011 ET always separate word-internal period before two chars
    #      while ($word =~ /^(.*\.)([A-Za-z][A-Za-z].*)$/) {
    #        unshift(@words,$2);
    #        $word = $1;
    #     }
    # 20020919 ET separate word-internal period string
    if ($word =~ /^([^\.]+)(\.\.+)([^\.]*)$/) {
      unshift(@words,$3);
      unshift(@words,$2);
      $word = $1;
    }
    # 20020919 ET separate word-internal period after parenthesis
    if ($word =~ /^(.*\))(\.)(.*)$/) {
      unshift(@words,$3);
      unshift(@words,$2);
      $word = $1;
    }
    if ($word =~ /^(.*\.)(--+)(.+)$/) {
      unshift(@words,$3);
      unshift(@words,$2);
      $word = $1;
    }
    # 20020918 ET always separate word-internal punctuation
    if ($word !~ /^[0-9]+:[0-9]+$/) {
      if ($word =~ /^([^:;]+[:;])(.+)$/) {
	unshift(@words,$2);
	$word = $1;
      }
    }
    # 20020918 ET always separate word-internal period before capital
    if ($word !~ /^[A-Z\.]*$/ and $word !~ /^[A-Z].*\..*\./) {
      while ($word =~ /^(.*\.)([A-Z].+)$/) {
	unshift(@words,$2);
	$word = $1;
      }
    }
  }
 LOOP1: while ($word =~ /^(.+),(.+)$/) {
    $first = $1;
    $last = $2;
    if ($first !~ /[0-9]$/ or $last !~ /^[0-9]/) {
      unshift(@words,$last);
      $word = "$first,";
    } else {
      last LOOP1;
    }
  }
  #   if ($word =~ /^([^\(]*)(\))(.+)$/) {
  #      unshift(@words,$3);
  #      $word = $1.$2;
  #   }

  #   if (not exists($abbr{$word}) and          # third item addded 20030623 ET
  #       ($word !~ /^[\"\']/ and $word !~ /[\"\']$/) and $word !~ /\..*\./ and
  #       ($word =~ /^(\S*[$uc_alpha$lc_alpha])([\(\)'"!?]*[,:\.!?\)\("][\)'"]*)([0-9$uc_alpha$lc_alpha]\S*)$/o or
  #        $word =~ /^(\S*[$uc_alpha$lc_alpha])([\(\)'"!?][,:\.!?\)\(\."][\)'"]*)([0-9$uc_alpha$lc_alpha]\S*)$/o
  #      )) {
  #      unshift(@words,$3);
  #      $word = $1.$2;          # split punctuation from word in later step
  #   }
  if ($word =~ 
      /^([^&]*[$uc_alpha$lc_alpha])([\)'"]*;[\)'"]*)([$uc_alpha$lc_alpha]\S*)$/o
     ) {
    unshift(@words,$3);
    $word = $1.$2;	   # split punctuation from word in later step
  }
  # 20020918 ET split sport results ?!
  # if ($word =~ /^([A-Z].+[-])([A-Z].+)$/) {
  #    unshift(@words,$2);
  #    $word = $1;
  # }
  return($word);
}
# }}}

# {{{ money(): read in the known currency names
# e.g. f5,- => f 5,-
sub money {
  my ($line);

  open(FH,"<$path/etc/money") or 
    die "!! $program ERR: Cannot open $path/etc/money!\n";
  while (defined($line=<FH>)) {
    if (substr($line,0,1) eq "#") {
      next;
    }				# comment line
    chomp($line);
    $money{$line} = 1;
  }
  close(FH);
}
# }}}

# {{{ ordinals(): read in the known suffixes for ordinals
# 1e en 2de => 1e en 2de
sub ordinals {
  my ($line);

  open(FH, "<$path/$lang/ordinals") or 
    die "!! $program ERR: Cannot open $path/$lang/ordinals!\n";
  while (defined($line=<FH>)) {
    if (substr($line,0,1) eq "#") {
      next;
    }				# comment line
    chomp($line);
    $ordinals{$line} = 1;
  }
  close(FH);
}
# }}}

# {{{ prefixes(): read in the known special prefixes
# e.g. l'avoir => l' avoir
sub prefixes {
  my ($line);

  $max_pref = 0;
  open(FH,"<$path/$lang/prefixes") or 
    die "!! $program ERR: Cannot open $path/$lang/prefixes!\n";
  while (defined($line=<FH>)) {
    if (substr($line,0,1) eq "#") {
      next;
    }				# comment line
    chomp($line);
    if ($line =~ /^(\S+)\s+(\S+)$/) {
      $pref{$1} = $2;
      if (length($1)>$max_pref) {
	$max_pref = length($1);
      }
    } else {
      if ( $verbosity >= 3 ) {
	print STDERR "!! $program INF: Illegal line in file prefixes: $line\n";
      }
    }
  }
  close(FH);
}
# }}}

# {{{ print_line()

sub print_line {
  my ($word);

  while (@_>0) {
    $word = shift(@_);
    if ($word eq "<utt>") {
      print $beginMarker;
    } elsif ($word eq "</utt>") {
      print $endMarker;
    } else {
      print "$word ";
    }
  }
  if ($return == 1) {
    print "\n";
  }
}

  # }}}

# {{{ process_word()
  sub process_word {
    my ($word);

    $word = shift(@_);
    if ($word =~ /^[$uc_alpha$lc_alpha]+$/o) { 
      # focus does only consist of letters -> less to do
      $word = special_words($word);
      return($word);
    }
    $word = &replace_sgml_entities($word);
    $word = &split_sgml($word);
    if (not &is_tag($word)) {	# focus is not a tag
      $word = &missing_space($word);
      $word = &split_special_characters($word);      
      # should all of these be separated???  e.g. C&A -> C & A ?
      $word = &punct_at_beginning($word);	
      $word = &punct_at_end($word);
      $word = &apply_files($word);
    }
    $word = special_words($word);
    return($word);
  }
# }}}

# {{{ punct_at_beginning(): word starts with punctuation
# don't separate ,, ... -- '' etc.
sub punct_at_beginning {
  my ($tmp1,$tmp2,$word);

  $word = shift(@_);
  while ($word =~ 
	 /^([#"(){}\[\]!?:;@\$%^&*+|=~<>\/\\_]|\.+|,+|-+|`+|'+)(.+)$/ ) {
    $tmp1 = $1;
    $tmp2 = $2;
    if (exists($apo{$word})	# 's morgens
	or ( $tmp1 eq "(" and 
	     ($tmp2 =~ /\)[A-Za-z]/ or $tmp2 =~ /\)-[^\s]*[A-Za-z]/))
	# (oud-)student, (her)-introductie
	or ( $tmp1 eq "." and $tmp2 =~ /^[0-9]/ ) # kaliber .22
	or ( $tmp1 eq "'" and $tmp2 =~ /^[0-9][0-9](-|$)/ ) # '93 '93-'94
	or ( $tmp1 eq "&" and $tmp2 =~ /^[A-Za-z]+;/ )      
	# &aacute; and other accents
	or $word =~ /^(\.+|,+|-+|`+|'+|\*+)$/ # don't split --- etc. #`
       ) {
      last;			# don't separate punctuation
    } else {
      push(@prefixes,$tmp1);
      $word = $tmp2;
    }
  }
  return($word);
}
# }}}

# {{{ punct_at_end(): word ends in punctuation
# don't separate ,, ... -- '' 5,- etc.
sub punct_at_end {
  my ($tmp1,$tmp2,@word);

  $word = shift(@_);		# added ... 20020318 ET
  if ($word eq "." or $word eq "!" or $word eq "?" or $word eq "...") {
    $add_end_utt = 1;
    return($word);
  }
  while ($word =~ 
	 /^(.+?)([#"(){}\[\]!?:;@\$%^&*+|=~<>\/\\_]|\.+|,+|-+|`+|'+|\.-|,-|\.=|,=)$/
	) {
    $tmp1 = $1;
    $tmp2 = $2;
    if (is_abbreviation($tmp1,$tmp2)                  # etc.   e.g.
          or ( $tmp2 eq '"' and $tmp1 =~ /[0-9]$/ )      # 14" scherm
          or ( $tmp2 eq ")" and $tmp1 =~ /[A-Za-z]\(/ )  # koning(in)
          or ( $tmp2 eq ";" and $tmp1 =~ /&[A-Za-z]+$/ ) # &aacute; and 
                                                        # other accents
          or $word =~ /^(\.+|,+|-+|`+|'+|\*+)$/         # don't split 
                                                        # --- etc. #`
          or ( ($tmp2 eq ".-" or $tmp2 eq ",-"
                or $tmp2 eq ".=" or $tmp2 eq ",=")
                and $tmp1 =~ /[0-9]$/)                   # f5,-
	   ) {
      last;
    }				# don't separate
    elsif ($tmp2 eq "-") {	# special case of hyphens
      if (@words == 0 and @suffixes == 0) { # at end of line
	$word = $1;		# provisionally remove hyphen
	$hyphened = $1;		# store for later check
	last;
      } elsif (@words>0 and exists($coord{lc($words[0])}) 
	       # "netto- en bruttoloon"
	       or (@suffixes == 1
		   and $suffixes[0] eq ",")) { # "vecht- , horror-
	# en pornogenre"
	last;			# don't separate
      } else {
	if ( $verbosity >= 3 ) {
	  print STDERR "!! $program INF: Strange hyphen: $word\n";
	}
	unshift(@suffixes,$tmp2); # separate punctuation from rest
	$word = $tmp1;
      }
    } else {			# separate punctuation from rest
      if ($tmp2 eq "." or $tmp2 eq "...") { 
	# separated period always ends utterance
	$add_end_utt = 1;
      } elsif ($tmp2 eq "!" or $tmp2 eq "?" ) {  
	# ! and ? may end utterance
	if (@suffixes == 0	# "Stop!" "dat ze in Gimmick! zaten"
	    or $suffixes[0] eq "\'" 
	    # "'Scare 'em to death!' luidt hun motto."
	    or $suffixes[0] eq "\'\'"
	    or $suffixes[0] eq '"') {
	  if (@words == 0       # nothing follows
	      or $words[0] =~ /^[^$lc_alpha]/) { 
	    # lower case letter follows
	    $add_end_utt = 1;	# end of utterance
	  }
	} elsif ($suffixes[0] ne ","               
		 # "wil hij met met Naar de klote!, die uitkomt in"
		 and $suffixes[0] ne ")") {          
	  # "geloof (!) en vrienden" "brigade (zonder 
	  # helikopters!) was"
	  $add_end_utt = 1;	# end of utterance
	}
      }
      unshift(@suffixes,$tmp2);	# separate punctuation from rest
      $word = $tmp1;
    }
  }
  return($word);
}
# }}}

# {{{ replace_sgml_entities(): replace sgml entities (e.g. &aacute;) by one ASCII character
sub replace_sgml_entities {
  my ($key,$prefix,$suffix);

  $prefix = shift(@_);
  $suffix = "";
  while ($prefix =~ /(.*)&([a-zA-Z]+);(.*)/) {
    $prefix = $1;
    $key = substr($2,0,1).lc(substr($2,1));
    if (exists($user_defined_tags{$key})) {
      $suffix = $user_defined_tags{$key} . $3 . $suffix;
    } elsif (exists($predefined_tags{$key})) {
      $suffix = $predefined_tags{$key} . $3 . $suffix;
    } else {
      $suffix = "&$2;" . $3 . $suffix;
    }
  }
  return("$prefix$suffix");
}
# }}}

# {{{ sgmlentalpha(): read in HTML special characters, e.g. &aacute;
sub sgmlentalpha {
  my ($line,@tmpAccents);

  open(FH,"<$path/etc/sgml.ent.alpha") or 
    die "!! $program ERR: Cannot open $path/etc/sgml.ent.alpha!@\n";

  # to display & enter accented chars in emacs, do:
  # M-x load-library iso-transl
  # M-x standard-display-european

  # niet aanwezige accenten:
  # typos: eaigu, guml, uuol, gacute, eacutg, euol, ewml
  # typos zijn opgenomen in hash met als resultaat het goede symbool ...

  # *slash
  # Yuml

  while (defined($line=<FH>)) {
    if (substr($line,0,1) eq "#") {
      next;
    }
    chomp($line);
    @tmpAccents = split(/\s+/,$line);
    if (@tmpAccents == 3) {	# lines with only two fields 
      # contain spelling errors
      if (substr($tmpAccents[0],0,1) =~ /[A-Z]/) {
	# e.g. "Ccedil" is upper case letter because "C" is upper case
	$uc_alpha .= $tmpAccents[1];
      } else {
	$lc_alpha .= $tmpAccents[1];
      }
    }
    $user_defined_tags{$tmpAccents[0]} = $tmpAccents[1];
  }
  close(FH);
  ### to print the tag2symbol table (%user_defined_tags) (on STDERR):
  ### uncomment following 3 lines
  ###     while (($key, $value) = each(%user_defined_tags)) {
  ###         print STDERR "tag: $key \t symbol: $value \n";
  ###     }
}
# }}}

# {{{ sgmlentnonalpha(): read in sgml entities which are not part of a word
# e.g. nbsp gt
sub sgmlentnonalpha {
  my ($line,@list);

  open(FH,"<$path/etc/sgml.ent.nonalpha") or 
    die "!! $program ERR: Cannot open $path/etc/sgml.ent.nonalpha!\n";
  while (defined($line=<FH>)) {
    if (substr($line,0,1) eq "#") {
      next;
    }				# comment line
    chomp($line);
    @list = split(/\t+/,$line);
    $predefined_tags{$list[0]} = $list[1];
  }
  close(FH);
}
# }}}

# {{{ sgmltags(): read in the known SGML tags
sub sgmltags {
  my ($line);

  open(FH,"<$path/etc/sgml.tags") or 
    die "!! $program ERR: Cannot open $path/etc/sgml.tags!\n";
  while (defined($line=<FH>)) {
    if (substr($line,0,1) eq "#") {
      next;
    }				# comment line
    chomp($line);
    if ($line =~ /^(\S*)\s+ends_utt$/) {
      $sgml{$1} = "ends_utt";
    } else {
      $sgml{$line} = "-";
    }
  }
  close(FH);
}
# }}}

# {{{ spec(): read in the known special words
# e.g. haste => hast du / nen => einen / ie => hij / 
#      zum => zu dem / cannot => can not
sub spec {
  my ($line);
  open(FH,"<$path/$lang/special_words") or 
    die "!! $program ERR: Cannot open $path/$lang/special_words!\n";
  while (defined($line=<FH>)) {
    if (substr($line,0,1) eq "#") {
      next;
    }				# comment line
    chomp($line);
    if ($line =~ /^(\S+)\s+(\S+)$/) {
      $spec1{$1} = $2;
    } elsif ($line =~ /^(\S+)\s+(\S+)\s+(\S+)$/) {
      $spec2{$1} = 1;
      $spec2_1{$1} = $2;
      $spec2_2{$1} = $3;
    } else {
      if ( $verbosity >= 3 ) {
	print STDERR "!! $program INF: Illegal line in file special_words: $line\n";
      }
    }
  }
  close(FH);
}
# }}}

# {{{ special_words(): e.g. haste => hast du / nen => einen / 
#                     ie => hij / zum => zu dem / cannot => can not
sub special_words {
  my ($word);

  $word = shift(@_);
  if (exists($spec1{$word})) {
    $word = $spec1{$word};
  } elsif (exists($spec2{$word})) {
    unshift(@suffixes,$spec2_2{$word});	# store second part
    $word = $spec2_1{$word};
  }
  return($word);
}
# }}}

# {{{ split_sgml(): et: not sure if this one is doing something useful
sub split_sgml {
  my ($pretag,$posttag,$tag,$tagtext,$word);

  $word = shift(@_);
 LOOP: while ($word =~ /^([^<>]*)(<\/?([^<>]+)>)(.*)$/) {
    # e.g. im<I>por</I>tant (meaning "por" is in italics)
    $pretag = $1;
    $tag = $2;
    $tagtext = $3;
    $posttag = $4;
    $tag =~ s/\s.*$/>/;
    $tagtext =~ s/\s.*$//;
    if (not exists($sgml{lc($tagtext)})) {
      print STDERR "Found tag not in list: $tag\n";
      $word = "$pretag$posttag";
    } elsif ($sgml{lc($tagtext)} ne "ends_utt") { 
      $word = "$pretag$posttag";
    } elsif ($pretag or $posttag) {
      if ($posttag) {
	unshift(@words,$posttag);
      }
      if ($pretag) { 
	unshift(@words,$tag);
	$word = $pretag;
      } else {
	$word = "$tag";
      }
    } else {
      last LOOP;
    }
  }
  return($word);
}
# }}}

# {{{ split_special_characters()
sub split_special_characters {
  my ($word);

  $word = shift(@_);
  if ($word =~ /^([^&]*)&([a-zA-Z]+);(.*)$/) { 
    # e.g. 36&pound;   H&amp;M   i&gt;10
    if (not(exists($user_defined_tags{$2}) # &Aacute; &aacute
	    or exists($user_defined_tags{substr($2,0,1).lc(substr($2,1))}))) {
      # &AaCUTE; -> &Aacute;
      if (exists($predefined_tags{$2})
	  or $2 eq "nbsp") {
	if (length($3)>0) {	# text after special character
	  unshift(@words,$3);
	}
	if (length($1)>0) {	# text in front of special character
	  $word = $1;
	  unshift(@words,"&$2;");
	} else {	       # no text in front of special character
	  $word = "&$2;";
	}
      } else {
	if ( $verbosity >= 3 ) {
	  print STDERR "!! $program INF: Found character not in list: &$2; (" .
	    substr($2,0,1).lc(substr($2,1)).")\n";
	}
      }
    }
  }
  # 20011106 et removed *
  # 20020429 et added /
  # 20021119 et removed &
  # e.g. H&M   1<3 # not: + =
  elsif ($word !~ /http/i and $word !~ /www/i and $word !~ /ftp/i) {
    while ($word =~ /^(\S+)([<>\/])(\S+)$/) {
      if (length($3)>0) {	# text after special character
	unshift(@words,$3);
      }
      if (length($1)>0) {	# text in front of special character
	$word = $1;
	unshift(@words,$2);
      } else {		       # no text in front of special character
	$word = $2;
      }
    }
  }
  return($word);
}
# }}}

# {{{ suffixes(): read in the known special suffixes
# e.g. it's => it 's / Peter's => Peter 's / dat-ie => dat ie/hij
sub suffixes {
  my ($line);

  $max_suff = 0;
  open(FH,"<$path/$lang/suffixes") or 
    die "!! $program ERR: Cannot open $path/$lang/suffixes!\n";
  while (defined($line=<FH>)) {
    if (substr($line,0,1) eq "#") {
      next;
    }				# comment line
    chomp($line);
    if ($line =~ /^(\S+)\s+(\S+)$/) {
      $suff{$1} = $2;
      if (length($1)>$max_suff) {
	$max_suff = length($1);
      }
    } else {
      if ( $verbosity >= 3 ) {
	print STDERR "!! $program INF: Illegal line in file suffixes: $line\n";
      }
    }
  }
  close(FH);
}
# }}}

# }}}

# {{{ POD Manpage
__END__

=head1 NAME

B<tokenize.pl> - tokenizes text read from STDIN

=head1 SYNOPSIS

B<tokenize.pl> [-help] [options] < INPUT

=head1 DESCRIPTION

B<tokenize.pl> reads in plain text from STDIN and prints out tokenized text to STDOUT. Sentences are
marked at beginning and end with a chosen marker.

=head1 OPTIONS

=over

=item -?, -h, -help, --help

prints the help message.

=item -v #int, -verbose #int, --verbose=#int

sets the verbosity level for the script. Defaults to 2.

=item -b STRING, -begin STRING, --begin=STRING

sets the string to use as a begin marker of a sentence. Defaults to <utt>.

=item -e STRING, -end STRING, --end=STRING

sets the string to use as an end marker of a sentence. Defaults to </utt>.

=item -r, -return, --return

force a return to be printed after each processed line. Default off.

=item -l LANGUAGE, -lang LANGUAGE, --lang=LANGUAGE

specifies the language of the input. By default only support for English is deliverd with this script. Defaults to 'eng'.

=item -p PATH, -path PATH, --path=PATH

sets the path where to look for the known lists for the used language. Defaults to './resources'.

=back

=head1 INSTALLATION

No need to do anything for installation. Just make sure Perl is correctly installed and this script has execute permissions.

=head1 EXAMPLES

 * nog nooit de eer gehad hem te ontmoeten , smaalde de vroeg -
   negentiende-eeuwse conservatief Joseph de Maistre over de Rechten

 * die jaren - was de eigentijdse verwoording van het vroeg -
   anarchistische verlangen naar een kleinschalige en

 * Jeruzalem-syndroom * Waarom het onmogelijk is een joods -
   islamitische stadsgids te schrijven * De Jezus-gekte *

 * Dan C & A. Die is er een stuk deftiger op geworden . <utt>

 * oeverweide aan de Alt Ausee viel me in , die zei : & uml;Dat is
   het eigenaardige , dat je het nooit op - geeft&!uml ; '

 * verschijning op deze T&T-avonden , leer ik . <utt> Slechts een op de
 * verschijning op deze T & T-avonden , leer ik . <utt> Slechts een op de

 * negatieve vorm van kwetsbaarheid te associ & eumlren . <utt> Dat is de enige

 * de wens om potenti & eumlle aanranders te slim af te zijn voor slechts

 * door Vita Sackville-West ge & iumlnspireerde Orlando , Gertrude Stein ,

 * als parano & iumlde querulant . <utt> Niemand wenste te geloven dat hij het

=head1 KNOWN PROBLEMS

 * inclusief de '20.000 gedocumenteerde gevallen'
   vs.
 * in '40-'45 was geen schande voor een lid van de
 -> at the moment: separate ' from number except if number has exactly two digits

 * 1. Het gaat slecht met de economie.
   vs.
 * MDA was de originele 'Love Drug' van 1968.
 -> at the moment: always separate "." from number unless "." is mentioned in file "ordinals"

 * een peiler van de maatschappij met -ei- in plaats van met -ij-.
 * Niet alle actrices hoeven in relatiedrama's of -komedies
 # vs.
 * Joegoslavi&euml; -het land van de zuid-Slaven- is ontstaan rond
 -> at the moment: separate - at beginning and end
    exception: hyphenation at end of line

 * Jason Epstein zegt dat zijn (inmiddels ex-)vrouw
 * Een psychoanalytische studie van Irvine Schiffer over de rol van charisma in onze massa- (en media-)maatschappij
 -> at the moment: problem...

 * Ach, Rudy, ik zou nog uren door kunnen gaan met het zingen van mijn honds roem zonder aan zijn onreinheid iets af te doen. (Was jij trouwens twee keer per etmaal je voeten?) Maar als je me vraagt naar het
 -> at the moment: no </utt> after "?)"

 * kunnen maken als er weer een pulp-event (de dood van Jomanda? Katja Schuurman stapt uit GTST? Willem-Alexander is homo?) of een non-event dreigt te worden opgeblazen
 -> at the moment: </utt>s after first two "?"

=head1 TODO

 * try and find some more rules that fix inconsystencies without breaking too much other things
 * loads of other stuff probably ;)

=head1 AUTHOR

Jo Meyhi <jo.meyhi@ua.ac.be>

=head1 COPYRIGHT

Copyright 2005 Jo Meyhi.

=cut

# }}}
