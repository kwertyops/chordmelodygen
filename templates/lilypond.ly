\version "2.20" 

\header {
    {{{ header }}}
}

{{{ fretboard_templates }}}
 
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
          {{#interval_names}}
          \override FretBoard.fret-diagram-details.finger-code = #'in-dot
          \override FretBoard.fret-diagram-details.fret-label-horizontal-offset = #0.5
          \override FretBoards.FretBoard.size = #'1.2
          {{/interval_names}}
          {{^interval_names}}
          \override FretBoard.fret-diagram-details.finger-code = #'none
          {{/interval_names}}
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