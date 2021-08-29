#!/usr/bin/python
# -*- coding: utf-8 -*-
from music21_tools import *
from dotenv import load_dotenv
import chevron
import os
import sys
import re

def generate_arrangement(filepath,
                   minimum_fret=5,
                   maximum_fret=15,
                   maj_triad='major-seven',
                   min_triad='minor-seven',
                   notation='tablature',
                   orientation='standard',
                   interval_names='intervals_off',
                   drop_type='drop2'):

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
    all_chords_drop = {} # for fretboard diagrams
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

        dc = drop_chord(inversion, drop_type)
        
        final = addExtensions(dc, cs, extensions, mel)

        all_chords_drop[o] = final


    ######
    # figure out chord positions and melody string nums
    #
    chord_neck_positions = {}
    melody_neck_positions = {}
    chord_note_frets = {}
    melody_string_nums = {}
    chord_interval_names = {}
    current_pos = minimum_fret
    prev_chord = None
    melody_string = 0
    for o in offsets:
        if o in all_chords_drop:
            try:
                c = all_chords_drop[o]
                melody_string, np = positionForChord(c, minimum_fret, maximum_fret, prev_chord, -1 * (melody_string) + 5, drop_type)
                current_pos = int(min(np))
                chord_note_frets[o] = np
                cs = all_chord_symbols[o]
                chord_interval_names[o] = intervalNamesForChord(c, cs)
                chord_neck_positions[o] = current_pos
                melody_string_nums[o] = melody_string + 1
                prev_chord = c
            except NoteTooLowForChord:
                r = note.Rest()
                r.duration = all_chords_drop[o].duration
                all_chords_drop[o] = r
                prev_chord = None
        if o in all_notes:
            melody_neck_positions[o] = current_pos

    ######
    # build voices for final output
    #
    voice_melody = stream.Voice()
    voice_chords_root = stream.Voice()
    voice_chords_drop = stream.Voice()

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
            if 'TimeSignature' in n.classes and i != 0:
                measure_melody.append(n)

        measure_chords_root = copy.deepcopy(measure_melody)
        measure_chords_drop = copy.deepcopy(measure_melody)

        for n in m:
            o = n.offset + m.offset
            if 'Note' in n.classes or 'Rest' in n.classes:
                n.lyrics = []
                measure_melody.insert(n.offset, n)
            elif 'Chord' in n.classes:
                measure_chords_root.insert(n.offset, all_chord_symbols[o])
                measure_chords_drop.insert(n.offset, all_chords_drop[o])

        voice_melody.insert(m.offset, measure_melody)
        voice_chords_root.insert(m.offset, measure_chords_root)
        voice_chords_drop.insert(m.offset, measure_chords_drop)

    voice_chords_root = realizeChordDurations(voice_chords_root)
    voice_chords_drop = realizeChordDurations(voice_chords_drop)

    ############
    ############

    # Lilypond Post-processing
    #
    #

    # fretboard diagrams
    lilychords = stream.Score()  # # create a stream to put everything in
    for m in voice_chords_drop:
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

    # Get the lilypond text for the drop chord content
    lpc.context = lily.lilyObjects.LyMusicList()
    lpc.appendObjectsToContextFromStream(lilychords)
    drop_chord_content = str(lpc.context).split('\n')
    drop_chord_content = [s for s in drop_chord_content if not s.startswith('\\')]

    # Get the lilypond text for the root chord content
    lpc.context = lily.lilyObjects.LyMusicList()
    lpc.appendObjectsToContextFromStream(lilychordsroot)
    root_chord_content = str(lpc.context).split('\n')
    root_chord_content = [s.replace('r ','s ') for s in root_chord_content if not s.startswith('\\')]

    # Replace tied chord endings with rests (for weird time signatures)
    for i in range(1,len(root_chord_content)):
        if '~' in root_chord_content[i-1]:
            root_chord_content[i] = re.sub('<.*>', 's', root_chord_content[i])
    for i in range(1,len(drop_chord_content)):
        if '~' in drop_chord_content[i-1]:
            drop_chord_content[i] = re.sub('<.*>', 'r', drop_chord_content[i])

    # Build the fretboard diagrams for the drop voicings
    string_offsets = []
    if drop_type == 'drop2':
        string_offsets = [0, 1, 2, 3]
    elif drop_type == 'drop3':
        string_offsets = [0, 1, 2, 4]
    elif drop_type == 'drop24':
        string_offsets = [0, 1, 3, 4]

    i = 0
    cc = copy.deepcopy(drop_chord_content)
    fretboard_templates = copy.deepcopy(drop_chord_content)

    for j, l in enumerate(cc):
        if '~' in cc[j-1]:
            fretboard_templates[j] = ''
            drop_chord_content[j] = f'\\set predefinedDiagramTable = #fret-table-{i}\n          ' + drop_chord_content[j]
            continue
        if '<' not in l or '>' not in l:
            continue
        mel_string_num = melody_string_nums[list(melody_string_nums.keys())[i]]
        note_pos = chord_note_frets[list(chord_note_frets.keys())[i]]
        interval_name = chord_interval_names[list(chord_interval_names.keys())[i]]
        fretboard_templates[j] = f'#(define fret-table-{i} (make-fretboard-table))\n\n' + \
                                 f'\\storePredefinedDiagram #fret-table-{i}\n' + \
                                 fretboard_templates[j] + '\n'
        fretboard_templates[j] += '#guitar-tuning\n'
        fretboard_templates[j] += '#\'('
        fretboard_templates[j] += f'(place-fret {mel_string_num + string_offsets[0]} {int(note_pos[0])} "{interval_name[3]}")'
        fretboard_templates[j] += f'(place-fret {mel_string_num + string_offsets[1]} {int(note_pos[1])} "{interval_name[2]}")'
        fretboard_templates[j] += f'(place-fret {mel_string_num + string_offsets[2]} {int(note_pos[2])} "{interval_name[1]}")'
        fretboard_templates[j] += f'(place-fret {mel_string_num + string_offsets[3]} {int(note_pos[3])} "{interval_name[0]}"))'
        fretboard_templates[j] += f'\n'
        drop_chord_content[j] = f'\\set predefinedDiagramTable = #fret-table-{i}\n          ' + drop_chord_content[j]
        i += 1

    # convert melody to tab with positions
    if notation == 'tablature':
        mel_i = 0
        for i, l in enumerate(list(melody_content)):
            if ('\\' not in l and
                    '{' not in l and
                    '}' not in l and
                    l.strip() != ''):
                p = melody_neck_positions[list(melody_neck_positions.keys())[mel_i]]
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
    vals['fretboard_templates'] = '\n'.join([f for f in fretboard_templates if '<' in f])
    vals['chord_symbols'] =      '\n              '.join(root_chord_content)
    vals['interval_names'] =     True if interval_names == 'intervals_on' else False
    vals['orientation'] =        '\\override FretBoard.fret-diagram-details.orientation = #\'landscape' if orientation == 'landscape' else ''
    vals['fretboard_diagrams'] = '\n          '.join(drop_chord_content)
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
