#!/usr/bin/perl -w
# -*- Mode: CPerl -*-

# $Revision: 1.4 $
# $Author: jmeyhi $
# $Date: 2005/11/25 17:25:06 $

# pnpfinder: attach pp chunks to np chunks with regular expressions
# 20030506 erikt@uia.ua.ac.be

use strict;
use warnings;
use Getopt::Long;
use Pod::Usage;

# {{{ variables
my $program = $0;
my $count = 0;
my $verbosity = 0;

my ($i,$j,$utt,
    $chunk,$line,$ppStart,$delete,
    @chunkStart,@chunkType,@pnpTags,@tags,@tokens,@words);
# }}}

# {{{ get command line parameters
GetOptions("help|?" => sub { pod2usage(2); },
	   "verbose=i" => \$verbosity,
	   "delete" => \$delete,
          ) or pod2usage (1);
# }}}

# {{{ runtime message

if ( $verbosity >= 2 ) {
  print STDERR "-- $program INF: grouping PNP's \n";
}

# }}}

# {{{ Main
while (<STDIN>) {
  $line = $_;

  # {{{ clean up and split line
  chomp($line);
  @tokens = split(/\s+/,$line);
  # }}}

  # {{{ remove preceding and trailing space (if any)
  if (defined $tokens[0] and $tokens[0] eq "") {
    shift(@tokens);
  }
  if (defined $tokens[$#tokens] and $tokens[$#tokens] eq "") {
    pop(@tokens);
  }
  # }}}

  # {{{ process all "O" chunks
  for ($i=0;$i<=$#tokens;$i++) {
    #       print STDERR "\$tokens[$i] = $tokens[$i]\n";
    ($words[$i],$tags[$i],$chunk) = split(/\/+/,$tokens[$i]);
    if ($chunk eq "O") {
      $chunkStart[$i] = "O"; $chunkType[$i] = "";
    } else {
      ($chunkStart[$i],$chunkType[$i]) = split(/-+/,$chunk);
    }
    $pnpTags[$i] = "O";
    if ($chunkType[$i] ne "") {
      $tokens[$i] = "$words[$i]/$tags[$i]/$chunkStart[$i]-$chunkType[$i]";
    } else {
      $tokens[$i] = "$words[$i]/$tags[$i]/$chunkStart[$i]";
    }
  }
  # }}}

  # {{{ process all other chunk types

  $ppStart = -1;
  for ($i=0;$i<=$#tokens;$i++) {
    if ($chunkType[$i] eq "PP" and
	($ppStart < 0 or ($ppStart >= 0 and $chunkStart[$i] ne "I"))) {
      $ppStart = $i;
    }
    if ($ppStart >= 0 and $chunkType[$i] eq "NP") {
      $j = -1;
      # repeat for non-initial PP words
      while ($i+$j-1 >= 0 and	# not first word sentence
	     $chunkStart[$i+$j] ne "B" and # not first word PP
	     $chunkType[$i+$j-1] eq "PP") { # not first word PP
	$pnpTags[$i+$j] = "I-PNP";
	$j--;
      }
      $pnpTags[$i+$j] = "B-PNP"; # first word PP
      $pnpTags[$i] = "I-PNP";	# first word NP
      $j = 1;
      # repeat for all non-initial NP words
      while ($i+$j <= $#words and # not final word sentence
	     $chunkStart[$i+$j] ne "B" and # still in NP
	     $chunkType[$i+$j] eq "NP") { # still in NP
	$pnpTags[$i+$j] = "I-PNP";
	$j++;
      }
    } 
    if ($chunkType[$i] ne "PP") {
      $ppStart = -1;
    }
  }

  # }}}

  $line = "";

  # {{{ -delete option
  for ($i=0;$i<=$#tokens;$i++) {
    $chunk = ($chunkType[$i] ne "") ? "$chunkStart[$i]-$chunkType[$i]" :
      $chunkStart[$i];
    if (not defined $delete or $pnpTags[$i] eq "O") {
      $line .= "$tokens[$i]/$pnpTags[$i] ";
    }
  }
  # }}}

  # {{{ remove trailing spaces and print out

  $line =~ s/\s+$//;
  print "$line\n";

  # }}}

  # {{{ counter
  unless ( $line =~ /^\s*$/ ) {
    $count++;
  }
  # }}}
}
# }}}

# {{{ make sure input was not empty
if ( $count <= 0 ) {
  die "!! $program ERR: no input on STDIN";
}
# }}}

exit(0);

# {{{ POD Manpage
__END__

=head1 NAME

B<pnpfinder.pl> - attaches pp chunks to np chunks with regular expressions

=head1 SYNOPSIS

B<pnpfinder.pl> [-help] [options] < INPUT

=head1 DESCRIPTION

B<pnpfinder.pl> reads in plain text tagged for POS and chunks by Mbt in the
format TOKEN/POS/CHUNK and by means of regular expressions tries to attach
PP's to NP chunks.

=head1 OPTIONS

=over

=item -?, -h, -help, --help

prints the help message.

=item -v #int, -verbose #int, --verbose=#int

sets the verbosity level for the script. Defaults to 2.

=item -d, -delete, --pdelete

makes pnp be deleted.

=back

=head1 INSTALLATION

No need to do anything for installation. Just make sure Perl is correctly installed and this script has execute permissions.

=head1 TODO

 * loads of stuff probably ;)

=head1 AUTHOR

Jo Meyhi <jo.meyhi@ua.ac.be>

=head1 COPYRIGHT

Copyright 2005 Jo Meyhi.

=cut

# }}}
