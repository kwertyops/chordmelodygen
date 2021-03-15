# chordmelodygen
A tool to generate guitar chord-melody arrangements from MusicXML leadsheets, using music21 and Lilypond.

# Installation
Requires a working installation of Lilypond. Specify the lilypond binary path in .env file, if necessary.

# Usage
Import generate_drop2 and call the generate_drop2() function:

```
generate_drop2(filepath,
                minimum_fret=5,
                maximum_fret=15,
                maj_triad='major-seven',
                min_triad='minor-seven',
                notation='tablature',
                orientation='standard')
```
