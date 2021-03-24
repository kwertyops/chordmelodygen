# chordmelodygen
A tool to generate guitar chord-melody arrangements from MusicXML leadsheets, using music21 and Lilypond.

# Installation
Requires a working installation of Lilypond. Specify the lilypond binary path in .env file, if necessary.

# Usage
Import generate_chordmelody and call the generate_arrangement() function:

```
generate_arrangement(filepath,
                     minimum_fret=5,
                     maximum_fret=15,
                     maj_triad='major-seven',
                     min_triad='minor-seven',
                     notation='tablature',
                     orientation='standard',
                     interval_names='intervals_off',
                     drop_type='drop2')
```

The resulting PDF will be written to data/output.
