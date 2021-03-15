#!/usr/bin/python
# -*- coding: utf-8 -*-
from music21_tools import *
from dotenv import load_dotenv
import chevron
import os
import sys

def generate_drop2(filepath,
                   minimum_fret=5,
                   maximum_fret=15,
                   maj_triad='major-seven',
                   min_triad='minor-seven',
                   notation='tablature',
                   orientation='standard'):

    filename = filepath.split('/')[-1]
    src = converter.parseFile(filepath)

    load_dotenv()
    environment.UserSettings()['lilypondPath'] = os.environ.get('LILYPOND_PATH')

    measures = src.parts[0].getElementsByClass('Measure')  # # get the measures
    harmony.realizeChordSymbolDurations(measures)  # # need this to see how long chords are

    # we don't currently support anacrusis (pickup measures)
    for m in measures:
        if m.duration.quarterLength < m.barDuration.quarterLength:
            raise AnacrusisException

    # TODO: Should also add an exception for Chords that aren't ChordSymbols


    ######
    # get all the musical elements into a big list by offset
    #
    all_chord_symbols = {}
    all_notes = {}
    for i, m in enumerate(measures):
        chords = m.getElementsByClass('Chord')
        notes = m.getElementsByClass(['Note', 'Rest'])
        for c in chords:
            all_chord_symbols[m.offset + c.offset] = c
        for n in notes:
            all_notes[m.offset + n.offset] = n

    offsets = sorted(list(set(list(all_chord_symbols.keys()) + list(all_notes.keys()))))


    ######
    # figure out the melody for each chord, and the chord for each note
    #
    melody_for_chord = {}
    chord_for_note = {}

    for o in offsets:
        # note and chord change together
        if o in all_notes and o in all_chord_symbols:
            chord_for_note[o] = all_chord_symbols[o]
            if all_notes[o].isRest:
                try:
                    melody_for_chord[o] = melody_for_chord[list(melody_for_chord.keys())[-1]]
                except:
                    melody_for_chord[o] = None
            else:
                melody_for_chord[o] = all_notes[o]
        # note change without chord (use previous chord)
        elif o in all_notes:
            try:
                chord_for_note[o] = chord_for_note[list(chord_for_note.keys())[-1]]
            except:
                chord_for_note[o] = None
        # chord change without note (use previous note)
        elif o in all_chord_symbols:
            try:
                melody_for_chord[o] = melody_for_chord[list(melody_for_chord.keys())[-1]]
            except:
                melody_for_chord[o] = None


    ######
    # build out processed chords
    #
    all_chords_drop2 = {} # for fretboard diagrams
    for o in all_chord_symbols.keys():
        cs = all_chord_symbols[o]
        mel = melody_for_chord[o]

        if '/' in cs.figure:
            noslash = harmony.ChordSymbol(cs.figure.split('/')[0])
            for n in cs.notes:
                cs.remove(n)
            for n in noslash.notes:
                cs.add(n)

        extensions = []

        # for "add __" chords, just get rid of the last note
        if 'add' in cs.figure and len(cs.notes) == 4:
            # print('Found an add chord with only 4 notes!')
            new_c = chord.Chord(cs.notes[0:min(len(cs.notes),3)])
            extensions += [cs.notes[3]]
        else:
            new_c = chord.Chord(cs.notes[0:min(len(cs.notes),4)])
            extensions += cs.notes[4:] if len(cs.notes) > 4 else []

        fnc = expandToFourNoteChord(new_c, cs.chordKind, maj_triad=maj_triad, min_triad=min_triad)
        mc = addMelodyToChord(fnc, mel)
        red = reduceToFourNoteChord(mc, cs, mel)

        if mel is not None:
            inversion = matchInversionToMelody(red, mel)
        else:
            inversion = increaseChordOctave(red, minimum_fret)
        d2c = drop2(inversion)
        
        final = addExtensions(d2c, cs, extensions, mel)

        all_chords_drop2[o] = final


    ######
    # figure out chord positions and melody string nums
    #
    chord_positions = {}
    note_positions = {}
    melody_string_nums = {}
    current_pos = minimum_fret
    prev_chord = None
    melody_string = 0
    for o in offsets:
        if o in all_chords_drop2:
            c = all_chords_drop2[o]
            melody_string, current_pos = positionForChord(c, minimum_fret, maximum_fret, prev_chord, -1 * (melody_string) + 5)
            chord_positions[o] = current_pos
            melody_string_nums[o] = melody_string + 1
            prev_chord = c
        if o in all_notes:
            note_positions[o] = current_pos

    ######
    # build voices for final output
    #
    voice_melody = stream.Voice()
    voice_chords_root = stream.Voice()
    voice_chords_drop2 = stream.Voice()

    for i, m in enumerate(measures):
        measure_melody = stream.Measure()
        measure_melody.number = m.number
        if i == 0:
            measure_melody.insert(0.0, m.keySignature)
            measure_melody.insert(0.0, m.timeSignature)
            measure_melody.insert(0.0, m.clef)
        for n in m:
            if 'SystemLayout' in n.classes:
                sl = layout.SystemLayout(isNew=True)
                measure_melody.append(sl)

        measure_chords_root = copy.deepcopy(measure_melody)
        measure_chords_drop2 = copy.deepcopy(measure_melody)

        for n in m:
            o = n.offset + m.offset
            if 'Note' in n.classes or 'Rest' in n.classes:
                n.lyrics = []
                measure_melody.insert(n.offset, n)
            elif 'Chord' in n.classes:
                measure_chords_root.insert(n.offset, all_chord_symbols[o])
                measure_chords_drop2.insert(n.offset, all_chords_drop2[o])

        voice_melody.insert(m.offset, measure_melody)
        voice_chords_root.insert(m.offset, measure_chords_root)
        voice_chords_drop2.insert(m.offset, measure_chords_drop2)

    voice_chords_root = realizeChordDurations(voice_chords_root)
    voice_chords_drop2 = realizeChordDurations(voice_chords_drop2)

    ############
    ############

    # Lilypond Post-processing
    #
    #

    # fretboard diagrams
    lilychords = stream.Score()  # # create a stream to put everything in
    for m in voice_chords_drop2:
        lilychords.insert(m.offset, m)

    # chord symbols
    lilychordsroot = stream.Score()
    for m in voice_chords_root:
        lilychordsroot.insert(m.offset, m)

    # melody
    lilymelody = stream.Score()
    lilymelody.streamStatus.beams = False
    lilymelody.metadata = src.parts[0].metadata
    for m in voice_melody:
        lilymelody.insert(m.offset, m)

    # create a lilypond converter
    lpc = lily.translate.LilypondConverter()

    # Get the lilypond text for the melody content
    lpc.context = lily.lilyObjects.LyMusicList()
    lpc.appendObjectsToContextFromStream(lilymelody)
    melody_content = str(lpc.context).split('\n')
    melody_content.insert(0, f'\\set Score.currentBarNumber = #{measures[0].number}')

    # Get the lilypond text for the drop2 chord content
    lpc.context = lily.lilyObjects.LyMusicList()
    lpc.appendObjectsToContextFromStream(lilychords)
    chord_content = str(lpc.context).split('\n')
    chord_content = [s for s in chord_content if not s.startswith('\\')]

    # Get the lilypond text for the root chord content
    lpc.context = lily.lilyObjects.LyMusicList()
    lpc.appendObjectsToContextFromStream(lilychordsroot)
    root_chord_content = str(lpc.context).split('\n')
    root_chord_content = [s.replace('r','s') for s in root_chord_content if not s.startswith('\\')]

    # Append string numbers to chord notes in drop 2's
    i = 0
    cc = copy.deepcopy(chord_content)
    for j, l in enumerate(cc):
        if '<' not in l or '>' not in l:
            continue
        notes = l.split('  ')
        notes[3] = notes[3] + '\\' + str(melody_string_nums[list(melody_string_nums.keys())[i]])
        notes[2] = notes[2] + '\\' + str(melody_string_nums[list(melody_string_nums.keys())[i]] + 3)
        notes[1] = notes[1] + '\\' + str(melody_string_nums[list(melody_string_nums.keys())[i]] + 1)
        notes[0] = notes[0] + '\\' + str(melody_string_nums[list(melody_string_nums.keys())[i]] + 2)
        chord_content[j] = '  '.join(notes)
        i += 1

    # convert melody to tab with positions
    if notation == 'tablature':
        mel_i = 0
        for i, l in enumerate(list(melody_content)):
            if ('\\' not in l and
                    '{' not in l and
                    '}' not in l and
                    l.strip() != ''):
                p = note_positions[list(note_positions.keys())[mel_i]]
                melody_content.insert(i + mel_i, f'\\set TabStaff.minimumFret = #{p}')
                mel_i += 1

    # build header
    header = []
    if src.metadata.title is not None: header += [f'title = "{src.metadata.title}"'];
    if src.metadata.composer is not None: header += [f'composer = "{src.metadata.composer}"'];
    header += [f'tagline = ##f']

    # build paper block
    paper = []

    # final template values
    vals = {}
    vals['header'] =             '\n    '.join(header)
    vals['chord_symbols'] =      '\n              '.join(root_chord_content)
    vals['orientation'] =        '\\override FretBoard.fret-diagram-details.orientation = #\'landscape' if orientation == 'landscape' else ''
    vals['fretboard_diagrams'] = '\n          '.join(chord_content)
    vals['staff_type'] =         'TabStaff' if notation == 'tablature' else 'Staff'
    vals['staff_headers'] =      '\\set TabStaff.restrainOpenStrings = ##t' if notation == 'tablature' else ''
    vals['melody'] =             '\n          '.join(melody_content)
    vals['paper'] =              '\n    '.join(paper)

    # write the final lilypond file from template
    with open('templates/lilypond.ly', 'r') as f:
        final = chevron.render(f, vals)
        lilyfile = filename.replace('.mxl', '.ly')
        lilyfile = "data/output/" + lilyfile
        with open(lilyfile, 'w') as lf:
            print(f'writing {lilyfile}')
            lf.write(final)

    # typeset the lilypond into PDF
    os.system(f'{os.environ.get("LILYPOND_PATH")} -o {lilyfile.replace(".ly", "")} {lilyfile}')
