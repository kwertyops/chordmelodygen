\version "2.20" 

\header {
    {{{ header }}}
}
 
\score  { 
<<
     \new ChordNames {
          \chordmode {
              {{{ chord_symbols }}}
          }
     }
     \new FretBoards {
          \override FretBoard.fret-diagram-details.number-type = #'arabic
          \override FretBoard.fret-diagram-details.fret-label-vertical-offset = #-0.5
          {{{ orientation }}}
          {{{ fretboard_diagrams }}}
     }
     \new {{{ staff_type }}} { 
          {{{ staff_headers }}}
          {{{ melody }}}
     } 
>>
} 
 
\paper {
    print-page-number = ##f
    {{{ paper }}}
}
\layout {
  \context {
    \override VerticalAxisGroup #'remove-first = ##t
  }
}