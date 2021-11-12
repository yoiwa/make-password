[-]: # " -*- mode: gfm; coding: utf-8 -*- "

# Packed corpus format, version 3

Note (as written in corpus_format.md) that this corpus format is
subject to change at any time.

The notation "`\x??`" will indicate a single-octet control character.
The notation "`\n`" stands for the octet "`\x0a`", a linefeed (LF) control.
Unless otherwise noted, a literal space will stand for a single
"`\x20`" octet.

In this document, "a line" means a sequence of octets terminated by
a LF control character.

# Overall structure

A packed corpus file is UTF-8 encoded without byte order markers,
though these will be handled using binary offsets and not editable as
a text file.  Currently it must be smaller than 100MiB.

The content of a corpus file is a sequence of the following sections:

	Initial header
	Comment section (optional)
	Second header
	Corpus data source
	Index table
	Final signature

# Initial header

An initial header consists of two lines.  The first line will be
exactly the octets "`#format packed\n`" (15 octets).  If a file does
not contain this initial octets, the file will not be treated as a
packed corpus.

Immediately following it, the second line (56 octets) will contain
five numbers (_a_ to _e_) in 8-digit hexadecimal format, as follows.

        #!!PCK!! aaaaaaaa bbbbbbbb cccccccc dddddddd eeeeeeee !\n

The numbers are as follows.

 * _a_: a magic number for this format, 0x03b9c787.
 * _b_: the version number of this format, 0x00000003.
 * _c_: the length of the following comment section in octets.
 * _d_: the length of the corpus data source section in octets.
 * _e_: the number of corpus entries in this file.

# Comment section and second header

After this second header line, an arbitrary comment (such as copyright
notices) can be placed.  Its length, in octets, is described by number _c_.
If _c_ is zero, there is no comment.

Immediately after a comment, a second header, which is a single line
containing "`#_-_-_-\n`" (8 octets) follows.

# Corpus data source

After the second header, a source data section for corpus content
follows.  The length of this section is determined by number _d_.

Each word contained in this section is encoded in UTF-8 and followed
by a LF character ("`\n`").  _Every octet in this area can be used for
two or more words in corpus_, as long as properly followed by a LF.
For example, when a file contains the sequence "`redistribution\n`",
it can be used for corpus entries `redistribution`, `distribution`,
`ion`, and `on`.  The order of word data in this area is arbitrary.

# Index table

Immediately after the corpus data section, an index table is
presented.  The table's length is calculated as (16 _d_ + 8) octets.
The initial 8 octets of the table must be seven hexadecimal digits
followed by LF, and it should contain the magic number above
(0x3b9c787).  After that, entries of 16 bytes each represents _d_
entries of the words in corpus.  Each 16-byte entry has a format of
"`xxxxxxx yyyyyyy\n`", where both _x_ and _y_ are 7-digit hexadecimal
numbers indicating zero-origin octet offsets from the beginning of the
corpus data source area. The number _x_ indicates the location of a
corpus word in the data source section, and _y_ indicates a location
for the hint text (e.g. a kanji representation) for that word.

For example, when the data source area begins with the octet sequence
"`redistribution\n`",

 * the offset value 0000000 stands for a word `redistribution`.
 * the offset value 0000002 stands for a word `distribution`.
 * the offset value 000000b stands for a word `ion`.
 * the offset value 000000c stands for a word `on`.

The order of the corpus words specified by the index must be in
ascending order in ASCII/UTF-8 character codes.  The corpus must
contain at least two words.

# Final signature

After the index table, the file must be terminated by a single line
containing "`#_-_-_-\n`" (8 octets).  No excess data is allowed.
