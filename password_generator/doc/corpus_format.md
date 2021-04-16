[-]: # " -*- mode: gfm; coding: utf-8 -*- "

# About corpus files:

Corpus files must be stored under `corpus/` directory, with an
extension `.corpus`. It's base name will be used in a format
specifier.

Each corpus file should be in one of the following formats.

## Bare format

The bare format accepts any simple text file in any ASCII-compatible
encoding with LF-delimited lines as a corpus.

Each word in the text (separated by SP, HT, VT, FF, CR) is taken as a
corpus entry, modulo the following exceptions:

 - Lines starting with `#` will be ignored.

 - If it contains a character other than alphabet and apostrophe,
   it is ignored.  For example, numbers are silently ignored.
   It also ignores words with accented characters etc.

 - Any words ending in apostrophe (e.g. `James'`) or apostrophe-s
   (e.g. `John's`) are ignored, treated as possessives.
 - If the line `#option no-apostroph` is found in the beginning of the
   text, all words containing an apostrophe (e.g. `O'Hare` or
   `o'clock`) is also ignored.

Duplicated words are automatically eliminated in the bare format.
This format can not provide a pronunciation hint feature.

## Packed format

Packed format is efficient for large dictionaries, and supporting
pronunciation hints.  
The corpus in this format is marked by the first
line `#format packed`, ending with LF.

Its format is binary-encoded (random-accessed with binary offsets) and
subject to change in future: it should not be edited by text editors,
and should only be generated using routines in
`password_generator/corpus_convert.py` script.

## Hinted format

_This format is obsolete: `password_generator/corpus_convert.py`
will convert this format to the packed format above._

The file is a text file in UTF-8 encoding with LF line terminators.

Corpus in the hinted format starts with a marker line
`#format hinted`, ending with LF.

After the marker line, source and copyright information should be
written directly after the above marker line, with each line starting
with `#`. An empty line shall follow them to start the main content.

In the main content, Any lines starting with '#' will be ignored.

All other lines must contain exactly two words separated by a tab
character (HT, `\x09`).  The first word, in ASCII, provides a word to
be used as a passphrase element. The latter, in UTF-8, is used as a
pronunciation corresponding to the first element.

Be careful that duplicated words are NOT (always) automatically
eliminated.

