from music21 import *
import copy

class AnacrusisException(Exception):
    pass

class NoteTooLowForChord(Exception):
    pass

string_notes = [
    40.0,
    45.0,
    50.0,
    55.0,
    59.0,
    64.0
]

def voicingOutOfFretRange(pitches, mel_string, string_offsets, min_fret):
    return (
        pitches[3] < string_notes[mel_string-string_offsets[0]] + min_fret or
        pitches[2] < string_notes[mel_string-string_offsets[1]] + min_fret or
        pitches[1] < string_notes[mel_string-string_offsets[2]] + min_fret or
        pitches[0] < string_notes[mel_string-string_offsets[3]] + min_fret
    )

def checkValidStringSet(mel_string, string_offsets):
    if mel_string-string_offsets[3] < 0:
        raise IndexError

def positionForChord(c, min_fret, max_fret, prev_chord, prev_string, drop_type):
    string_offsets = []
    if drop_type == 'drop2':
        string_offsets = [0, 1, 2, 3]
    elif drop_type == 'drop3':
        string_offsets = [0, 1, 2, 4]
    elif drop_type == 'drop24':
        string_offsets = [0, 1, 3, 4]

    pitches = [x.ps for x in c.pitches]
    pitches = list(sorted(pitches))
    mel_string = 5

    # if the highest voice stayed the same between chords
    # try to play it on the same string
    if prev_chord is not None:
        prev_mel = list(sorted([x.ps for x in prev_chord.pitches]))[3]
        if pitches[3] == prev_mel:
            mel_string = prev_string
            try:
                while (voicingOutOfFretRange(pitches, mel_string, string_offsets, min_fret)):
                    mel_string -= 1
                    checkValidStringSet(mel_string, string_offsets)
            except IndexError:
                mel_string = 5

    # normal case, start from the highest string
    try:
        while (voicingOutOfFretRange(pitches, mel_string, string_offsets, min_fret)):
            mel_string -= 1
            checkValidStringSet(mel_string, string_offsets)
    except IndexError:
        try:
            min_fret = 0
            mel_string = 5
            while (voicingOutOfFretRange(pitches, mel_string, string_offsets, min_fret)):
                mel_string -= 1
                checkValidStringSet(mel_string, string_offsets)
        except IndexError:
            raise NoteTooLowForChord

    note_positions = [
        pitches[3] - string_notes[mel_string-string_offsets[0]],
        pitches[2] - string_notes[mel_string-string_offsets[1]],
        pitches[1] - string_notes[mel_string-string_offsets[2]],
        pitches[0] - string_notes[mel_string-string_offsets[3]] ]

    # return melody_string_num, fret_position, note_positions
    return 5 - mel_string, note_positions

def increaseChordOctave(c, min_fret):
    c = copy.deepcopy(c)
    octaves = 1 + ((string_notes[-1] + min_fret) - c.pitches[-1].ps) // 12
    for n in c.notes:
        new = copy.deepcopy(n)
        new.octave += octaves
        c.remove(n)
        c.add(new)
    return c

def matchInversionToMelody(c, mel):
    c = copy.deepcopy(c)
    # print(f"before inversion: {c}")
    for n in c.notes: # find pitch of the melody note in the chord
            if n.pitch.pitchClass == mel.pitch.pitchClass:
                chord_mel = n
                break
    for n in c.notes: # shift the whole chord up so that the melody note matches
        new = copy.deepcopy(n)
        new.octave += (mel.octave - chord_mel.octave)
        c.remove(n)
        c.add(new)
    for n in c.notes:
        if n.pitch.ps > mel.pitch.ps:
            new = copy.deepcopy(n)
            while(new.pitch.ps > mel.pitch.ps):
                new.octave -= 1
            c.remove(n)
            c.add(new)
    # print(f"after inversion: {c}")
    return c

def drop_chord(c, type='drop2'):
    c = copy.deepcopy(c)
    if type == 'drop2':
        c[2].octave -= 1
    elif type == 'drop3':
        c[1].octave -= 1
    elif type == 'drop24':
        c[0].octave -= 1
        c[2].octave -= 1
    return c

def addMelodyToChord(c, mel):
    c = copy.deepcopy(c)
    if mel is None or mel.pitch.pitchClass in c.pitchClasses:
        return c
    # print(f"checking if {mel.pitch.name} in {c.pitchNames}")
    r = copy.deepcopy(c[0].pitch)
    i = interval.Interval(noteStart=r, noteEnd=mel)
    r.ps += i.semitones % 12
    c.add(r)
    # print(f"added melody note: {c[0]} {r}")
    return c

def expandToFourNoteChord(c, kind, maj_triad='major-seven', min_triad='minor-seven'):
    c = copy.deepcopy(c)
    if len(c.notes) == 3:
        r = copy.deepcopy(c[0].pitch)
        if 'minor' in kind:
            if min_triad == 'minor-seven':
                r.ps -= 2
                r.octave += 1
                c.add(r)
            elif min_triad == 'minor-six':
                r.ps -= 3
                r.octave += 1
                c.add(r)
            elif min_triad == 'minor-nine':
                r.ps -= 2
                r.octave += 1
                c.add(r)
                c[0].transpose(2, inPlace=True)
            elif min_triad == 'minor-six-nine':
                r.ps -= 3
                r.octave += 1
                c.add(r)
                c[0].transpose(2, inPlace=True)
        elif 'augmented' in kind:
            r.ps -= 2
            r.octave += 1
            c.add(r)
        elif 'diminished' in kind:
            r.ps -= 3
            r.octave += 1
            c.add(r)
        elif 'major' in kind:
            if maj_triad == 'major-seven':
                r.ps += 11
                c.add(r)
            elif maj_triad == 'major-six':
                r.ps += 9
                c.add(r)
            elif maj_triad == 'major-nine':
                r.ps += 11
                c.add(r)
                c[0].transpose(2, inPlace=True)
            elif maj_triad == 'major-six-nine':
                r.ps += 9
                c.add(r)
                c[0].transpose(2, inPlace=True)
        elif 'suspended' in kind:
            flatseven = copy.deepcopy(c[0].pitch)
            flatseven.ps -=2
            flatseven.octave += 1
            c.add(flatseven)
    elif len(c.notes) == 1: # assume major?
        r = copy.deepcopy(c[0].pitch)
        third = copy.deepcopy(r)
        third.ps += 4
        fifth = copy.deepcopy(r)
        fifth.ps += 7
        seventh = copy.deepcopy(r)
        seventh.ps += 11
        c.add(third)
        c.add(fifth)
        c.add(seventh)
    return c

def reduceToFourNoteChord(c, csymb, mel):
    # print(f"reducing chord {c}")
    # print(f"with melody {mel}")
    c = copy.deepcopy(c)
    if len(c.notes) > 4:
        for n in c.notes:
            if n.pitch.pitchClass == mel.pitch.pitchClass:
                mel = n
                break
        c.remove(mel)
        mel_semitones = interval.Interval(noteStart=csymb[0].pitch, noteEnd=mel).semitones % 12
        if 'minor' in csymb.chordKind:
            if mel_semitones == 0: # root
                c.remove(c[0])
            elif mel_semitones == 1: # b9
                c.remove(c[0])
            elif mel_semitones == 2: # 9
                c.remove(c[0])
            elif mel_semitones == 4: # 3
                c.remove(c[1])
            elif mel_semitones == 5: # 4
                c.remove(c[1])
            elif mel_semitones == 6: # b5
                c.remove(c[2])
            elif mel_semitones == 7: # 5
                c.remove(c[2])
            elif mel_semitones == 8: # #5
                c.remove(c[2])
            elif mel_semitones == 9: # 6
                c.remove(c[3])
            elif mel_semitones == 10: # b7
                c.remove(c[3])
            elif mel_semitones == 11: # 7
                c.remove(c[3])
        elif 'augmented' in csymb.chordKind:
            if mel_semitones == 1: # b9
                c.remove(c[0])
            elif mel_semitones == 2: # 9
                c.remove(c[0])
            elif mel_semitones == 3: # b3
                c.remove(c[1])
            elif mel_semitones == 5: # 4
                c.remove(c[1])
            elif mel_semitones == 6: # b5
                c.remove(c[2])
            elif mel_semitones == 7: # 5
                c.remove(c[2])
            elif mel_semitones == 9: # 13
                c.remove(c[2])
            elif mel_semitones == 11: # 7
                c.remove(c[3])
        elif 'half-diminished' in csymb.chordKind:
            if mel_semitones == 1: # b9
                c.remove(c[0])
            elif mel_semitones == 2: # 9
                c.remove(c[0])
            elif mel_semitones == 4: # 3
                c.remove(c[1])
            elif mel_semitones == 5: # 4
                c.remove(c[1])
            elif mel_semitones == 7: # 5
                c.remove(c[2])
            elif mel_semitones == 8: # #5
                c.remove(c[2])
            elif mel_semitones == 9: # 6
                c.remove(c[3])
            elif mel_semitones == 11: # 7
                c.remove(c[3])
        elif 'diminished' in csymb.chordKind:
            if mel_semitones == 1: # b9
                c.remove(c[0])
            elif mel_semitones == 2: # 9
                c.remove(c[0])
            elif mel_semitones == 4: # 3
                c.remove(c[1])
            elif mel_semitones == 5: # 4
                c.remove(c[2])
            elif mel_semitones == 7: # 5
                c.remove(c[2])
            elif mel_semitones == 8: # #5
                c.remove(c[3])
            elif mel_semitones == 10: # b7
                c.remove(c[3])
            elif mel_semitones == 11: # 7
                c.remove(c[0])
        elif 'dominant' in csymb.chordKind:
            if mel_semitones == 1: # b9
                c.remove(c[0])
            elif mel_semitones == 2: # 9
                c.remove(c[0])
            elif mel_semitones == 3: # #9
                c.remove(c[1])
            elif mel_semitones == 5: # 4
                c.remove(c[1])
            elif mel_semitones == 6: # b5
                c.remove(c[2])
            elif mel_semitones == 8: # #5
                c.remove(c[2])
            elif mel_semitones == 9: # 13
                c.remove(c[2])
                c[0].transpose(2, inPlace=True)
            elif mel_semitones == 11: # 7
                c.remove(c[3])
        elif 'major' in csymb.chordKind:
            if mel_semitones == 0: # root
                c.remove(c[0])
            elif mel_semitones == 1: # b9
                c.remove(c[0])
            elif mel_semitones == 2: # 9
                c.remove(c[0])
            elif mel_semitones == 3: # b3
                c.remove(c[1])
            elif mel_semitones == 5: # 4
                c.remove(c[1])
            elif mel_semitones == 6: # #11
                c.remove(c[2])
            elif mel_semitones == 8: # #5
                c.remove(c[2])
            elif mel_semitones == 9: # 6
                c.remove(c[3])
            elif mel_semitones == 10: # b7
                c.remove(c[3])
            elif mel_semitones == 11: # 7
                c.remove(c[3])
        elif 'suspended' in csymb.chordKind:
            if mel_semitones == 1: # b9
                c.remove(c[0])
            elif mel_semitones == 2: # 9
                c.remove(c[0])
            elif mel_semitones == 3: # b3
                c.remove(c[1])
            elif mel_semitones == 5: # 3
                c.remove(c[1])
            elif mel_semitones == 6: # b5
                c.remove(c[2])
            elif mel_semitones == 8: # #5
                c.remove(c[2])
            elif mel_semitones == 9: # 13
                c.remove(c[2])
            elif mel_semitones == 11: # 7
                c.remove(c[3])
        c.add(mel)
    return c

def intervalNamesForChord(c, cs):
    pitches = [x.ps for x in c.pitches]
    pitches = list(sorted(pitches))
    root_ps = cs.notes[0].pitch.ps
    interval_names = []

    for p in pitches:
        interval_semitones = (p - root_ps) % 12
        if 'minor' in cs.chordKind:
            if interval_semitones == 0:
                interval_names += ["1"]
            elif interval_semitones == 1:
                interval_names += ["b9"]
            elif interval_semitones == 2:
                interval_names += ["9"]
            elif interval_semitones == 3:
                interval_names += ["b3"]
            elif interval_semitones == 4:
                interval_names += ["3"]
            elif interval_semitones == 5:
                interval_names += ["4"]
            elif interval_semitones == 6:
                interval_names += ["b5"]
            elif interval_semitones == 7:
                interval_names += ["5"]
            elif interval_semitones == 8:
                interval_names += ["#5"]
            elif interval_semitones == 9:
                interval_names += ["6"]
            elif interval_semitones == 10:
                interval_names += ["b7"]
            elif interval_semitones == 11:
                interval_names += ["7"]
        elif 'augmented' in cs.chordKind:
            if interval_semitones == 0:
                interval_names += ["1"]
            elif interval_semitones == 1:
                interval_names += ["b9"]
            elif interval_semitones == 2:
                interval_names += ["9"]
            elif interval_semitones == 3:
                interval_names += ["#9"]
            elif interval_semitones == 4:
                interval_names += ["3"]
            elif interval_semitones == 5:
                interval_names += ["4"]
            elif interval_semitones == 6:
                interval_names += ["b5"]
            elif interval_semitones == 7:
                interval_names += ["5"]
            elif interval_semitones == 8:
                interval_names += ["#5"]
            elif interval_semitones == 9:
                interval_names += ["13"]
            elif interval_semitones == 10:
                interval_names += ["b7"]
            elif interval_semitones == 11:
                interval_names += ["7"]
        elif 'half-diminished' in cs.chordKind:
            if interval_semitones == 0:
                interval_names += ["1"]
            elif interval_semitones == 1:
                interval_names += ["b9"]
            elif interval_semitones == 2:
                interval_names += ["9"]
            elif interval_semitones == 3:
                interval_names += ["b3"]
            elif interval_semitones == 4:
                interval_names += ["3"]
            elif interval_semitones == 5:
                interval_names += ["4"]
            elif interval_semitones == 6:
                interval_names += ["b5"]
            elif interval_semitones == 7:
                interval_names += ["5"]
            elif interval_semitones == 8:
                interval_names += ["#5"]
            elif interval_semitones == 9:
                interval_names += ["6"]
            elif interval_semitones == 10:
                interval_names += ["b7"]
            elif interval_semitones == 11:
                interval_names += ["7"]
        elif 'diminished' in cs.chordKind:
            if interval_semitones == 0:
                interval_names += ["1"]
            elif interval_semitones == 1:
                interval_names += ["b9"]
            elif interval_semitones == 2:
                interval_names += ["9"]
            elif interval_semitones == 3:
                interval_names += ["b3"]
            elif interval_semitones == 4:
                interval_names += ["3"]
            elif interval_semitones == 5:
                interval_names += ["4"]
            elif interval_semitones == 6:
                interval_names += ["b5"]
            elif interval_semitones == 7:
                interval_names += ["5"]
            elif interval_semitones == 8:
                interval_names += ["#5"]
            elif interval_semitones == 9:
                interval_names += ["6"]
            elif interval_semitones == 10:
                interval_names += ["b7"]
            elif interval_semitones == 11:
                interval_names += ["7"]
        elif 'dominant' in cs.chordKind:
            if interval_semitones == 0:
                interval_names += ["1"]
            elif interval_semitones == 1:
                interval_names += ["b9"]
            elif interval_semitones == 2:
                interval_names += ["9"]
            elif interval_semitones == 3:
                interval_names += ["#9"]
            elif interval_semitones == 4:
                interval_names += ["3"]
            elif interval_semitones == 5:
                interval_names += ["4"]
            elif interval_semitones == 6:
                interval_names += ["b5"]
            elif interval_semitones == 7:
                interval_names += ["5"]
            elif interval_semitones == 8:
                interval_names += ["#5"]
            elif interval_semitones == 9:
                interval_names += ["13"]
            elif interval_semitones == 10:
                interval_names += ["b7"]
            elif interval_semitones == 11:
                interval_names += ["7"]
        elif 'major' in cs.chordKind:
            if interval_semitones == 0:
                interval_names += ["1"]
            elif interval_semitones == 1:
                interval_names += ["b9"]
            elif interval_semitones == 2:
                interval_names += ["9"]
            elif interval_semitones == 3:
                interval_names += ["b3"]
            elif interval_semitones == 4:
                interval_names += ["3"]
            elif interval_semitones == 5:
                interval_names += ["4"]
            elif interval_semitones == 6:
                interval_names += ["#11"]
            elif interval_semitones == 7:
                interval_names += ["5"]
            elif interval_semitones == 8:
                interval_names += ["#5"]
            elif interval_semitones == 9:
                interval_names += ["6"]
            elif interval_semitones == 10:
                interval_names += ["b7"]
            elif interval_semitones == 11:
                interval_names += ["7"]
        elif 'suspended' in cs.chordKind:
            if interval_semitones == 0:
                interval_names += ["1"]
            elif interval_semitones == 1:
                interval_names += ["b9"]
            elif interval_semitones == 2:
                interval_names += ["9"]
            elif interval_semitones == 3:
                interval_names += ["b3"]
            elif interval_semitones == 4:
                interval_names += ["3"]
            elif interval_semitones == 5:
                interval_names += ["4"]
            elif interval_semitones == 6:
                interval_names += ["b5"]
            elif interval_semitones == 7:
                interval_names += ["5"]
            elif interval_semitones == 8:
                interval_names += ["#5"]
            elif interval_semitones == 9:
                interval_names += ["13"]
            elif interval_semitones == 10:
                interval_names += ["b7"]
            elif interval_semitones == 11:
                interval_names += ["7"]
    return interval_names

def addExtensions(c, csymb, ext, mel):
    c = copy.deepcopy(c)
    for e in ext:
        if e.pitch.pitchClass not in c.pitchClasses:
            ext_semitones = interval.Interval(noteStart=csymb[0].pitch, noteEnd=e).semitones % 12
            for v in c.notes:
                if mel is None or v.pitch.pitchClass != mel.pitch.pitchClass:
                    # don't change any voice that's the melody voice
                    v_semitones = interval.Interval(noteStart=csymb[0].pitch, noteEnd=v).semitones % 12
                    if (v_semitones == 0) and (ext_semitones == 1 or ext_semitones == 2):
                        # voice is root, and ext is b9 or 9
                        v.transpose(ext_semitones - v_semitones, inPlace=True)
                    # elif (v_semitones == 3 or v_semitones == 4) and (ext_semitones == 5):
                    #     # voice is 3 or b3, and ext is 11
                    #     v.transpose(ext_semitones - v_semitones, inPlace=True)
                    elif (v_semitones == 7) and (ext_semitones == 6 or ext_semitones == 8):
                        # voice is 5, and ext is b5 or #5
                        v.transpose(ext_semitones - v_semitones, inPlace=True)
                    elif (v_semitones == 11) and (ext_semitones == 9):
                        # voice is 7, and ext is 6
                        v.transpose(ext_semitones - v_semitones, inPlace=True)
                    elif (v_semitones == 7) and (ext_semitones == 9) and ('dominant' in csymb.chordKind):
                        # voice is a 5, and ext is 13 (on dominant)
                        v.transpose(ext_semitones - v_semitones, inPlace=True)
    return c


def realizeChordDurations(v):
    v = copy.deepcopy(v)
    for m in v:
        chords = m.getElementsByClass('Chord')
        rests = m.getElementsByClass('Rest')
        i = 0
        if len(chords) == 0 and len(rests) == 0:
            r = note.Rest()
            r.duration = m.barDuration
            m.insert(0.0, r)
            continue
        elif m[0].offset != 0.0:
            r = note.Rest()
            r.duration = duration.Duration(m[0].offset)
            m.insert(0.0, r)
        for n in m:
            if len(m) == i + 1: # last item in measure
                n.duration = duration.Duration(m.barDuration.quarterLength - n.offset)
            else:
                n.duration = duration.Duration(m[i+1].offset - n.offset)
            i += 1
    return v
