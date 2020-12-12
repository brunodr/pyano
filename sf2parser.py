#!/usr/bin/python3

'''
Parser based on SoundFont 2 specification available here:
http://freepats.zenvoid.org/sf2/sfspec24.pdf
'''


from struct import unpack
from pathlib import Path


gen_dict = {
0: "startAddrsOffset",
1: "endAddrsOffset",
2: "startloopAddrsOffset",
3: "endloopAddrsOffset",
4: "startAddrsCoarseOffset",
5: "modLfoToPitch",
6: "vibLfoToPitch",
7: "modEnvToPitch",
8: "initialFilterFc",
9: "initialFilterQ",
10: "modLfoToFilterFc",
11: "modEnvToFilterFc",
12: "endAddrsCoarseOffset",
13: "modLfoToVolume",
14: "unused1",
15: "chorusEffectsSend",
16: "reverbEffectsSend",
17: "pan",
21: "delayModLFO",
22: "freqModLFO",
23: "delayVibLFO",
24: "freqVibLFO",
25: "delayModEnv",
26: "attackModEnv",
27: "holdModEnv",
28: "decayModEnv",
29: "sustainModEnv",
30: "releaseModEnv",
31: "keynumToModEnvHold",
32: "keynumToModEnvDecay",
33: "delayV",
34: "attackV",
35: "holdV",
36: "decayV",
37: "sustainV",
38: "releaseV",
39: "keynumToVolEnvHold",
40: "keynumToVolEnvDecay",
41: "instrument",
42: "reserved1",
43: "keyRange",
44: "velRange",
45: "startloopAddrsCoarseOffset",
46: "keynum",
47: "velocity",
48: "initialAttenuation",
50: "endloopAddrsCoarseOffset",
51: "coarseTune",
52: "fineTune",
54: "sampleModes",
56: "scaleTuning",
57: "exclusiveClass",
58: "overridingRootKey", }


def get_sf2_preset_list(sf2path):
    '''
    Return the list of presets in the sound font file in the form
    of a list of tuples [(preset_index, bank, preset_name), ...]
    '''
    with open(sf2path, 'rb') as f:
        chk_dict = _parse_chunks(f)
        presets = _parse_phdr_chunk(f, chk_dict['sfbk']['pdta']['phdr'])
        # The raw preset list contains a terminal entry which we need to remove
        return [(p[1], p[2], p[0]) for p in presets[:-1]]


def _unpack_chunk_header(f, pos):
    f.seek(pos)
    chkid, chklen = unpack('4sI', f.read(8))
    return (chkid.decode('ascii'), chklen)


def _cleanstr(s):
    eos = s.find(0)
    return s[:eos] if eos >= 0 else s


def _iterchunk(f, chunk, entry_size):
    pos = chunk[0]
    chklen = chunk[1]
    pos += 8
    end = pos + chklen
    f.seek(pos)
    while pos + entry_size <= end:
        yield f.read(entry_size)
        pos += entry_size


def _print_riff_struct(f, pos):
     chkid, chklen = _unpack_chunk_header(f, pos)
     end = pos + 8 + chklen
     if chkid in ['RIFF', 'LIST']:
         subid = unpack('4s', f.read(4))[0].decode('ascii')
         print(f'{chkid}-{subid} {pos} {chklen}')
         pos += 12
         while pos < end:
             pos += _print_riff_struct(f, pos)
     else:
         print(f'{chkid} {pos} {chklen}')
     return chklen + 8


def _parse_chunks(f):
    def parse_rec(pos, chk_dict):
         chkid, chklen = _unpack_chunk_header(f, pos)
         end = pos + 8 + chklen
         if chkid in ['RIFF', 'LIST']:
             subid = unpack('4s', f.read(4))[0].decode('ascii')
             sub_dict = {}
             chk_dict[subid] = sub_dict
             pos += 12
             while pos < end:
                 pos += parse_rec(pos, sub_dict)
         else:
             chk_dict[chkid] = (pos, chklen)
         return chklen + 8
    top_dict = {}
    parse_rec(0, top_dict)
    return top_dict


def _parse_inst_chunk(f, chunk):
    res = []
    for index, buff in enumerate(_iterchunk(f, chunk, 22)):
        name, _bagindex = unpack('20sH', buff)
        name = _cleanstr(name)
        res.append((index, name.decode('ascii', errors='replace')))
    return res


'''
struct sfPresetHeader {
    CHAR achPresetName[20];
    WORD wPreset;
    WORD wBank;
    WORD wPresetBagNdx;
    DWORD dwLibrary;
    DWORD dwGenre;
    DWORD dwMorphology;
}
'''
def _parse_phdr_chunk(f, chunk):
    res = []
    for buff in _iterchunk(f, chunk, 38):
        name, preset, bank, bagindex, _lib, _genre, _morph = unpack('<20sHHHIII', buff)
        name = _cleanstr(name).decode('ascii', errors='replace')
        res.append((name, preset, bank, bagindex))
    return res    


'''
struct sfPresetBag {
    WORD wGenNdx;
    WORD wModNdx; };
'''
def _parse_pbag_chunk(f, chunk):
    res = []
    for buff in _iterchunk(f, chunk, 4):
        genIndex, modIndex = unpack('<HH', buff)
        res.append((genIndex, modIndex))
    return res


'''
struct sfGenList {
    SFGenerator sfGenOper;
    genAmountType genAmount; };

where the types are defined:

typedef struct {
    BYTE byLo;
    BYTE byHi; } rangesType;

typedef union {
    rangesType ranges;
    SHORT shAmount;
    WORD wAmount;
} genAmountType;
'''
def _parse_pgen_chunk(f, chunk):
    res = []
    for buff in _iterchunk(f, chunk, 4):
        genType, data = unpack('<HH', buff)
        if genType == 43 or genType == 44:
            _, low, high = unpack('<HBB', buff)
            data = (low, high)
        res.append((genType, data))
    return res


'''
struct sfInst {
    CHAR achInstName[20];
    WORD wInstBagNdx; };
'''
def _parse_inst_chunk(f, chunk):
    res = []
    for buff in _iterchunk(f, chunk, 22):
        name, bagindex = unpack('<20sH', buff)
        name = _cleanstr(name).decode('ascii', errors='replace')
        res.append((name, bagindex))
    return res


'''
struct sfInstGenList {
    SFGenerator sfGenOper;
    genAmountType genAmount; };
'''
def _parse_igen_chunk(f, chunk):
    return _parse_pgen_chunk(f, chunk)


if __name__ == '__main__':
    sf2_folder = Path(__file__).parent / 'SoundBanks'
    sf2_files = [str(f) for f in sf2_folder.glob('*.*')]
    with open(sf2_files[0], "rb") as f:
        chk_dict = _parse_chunks(f)
        presets = _parse_phdr_chunk(f, chk_dict['sfbk']['pdta']['phdr'])
        pbags = _parse_pbag_chunk(f, chk_dict['sfbk']['pdta']['pbag'])
        pgens = _parse_pgen_chunk(f, chk_dict['sfbk']['pdta']['pgen'])
        igens = _parse_igen_chunk(f, chk_dict['sfbk']['pdta']['igen'])
        for i in range(len(presets) - 1):
            p = presets[i]
            zone_start = p[3]
            zone_count = presets[i+1][3] - p[3]
            if not 'Piano' in p[0]:
                continue
            print(f'{p[0]} ({zone_count})')
            for izone in range(zone_count):
                z = zone_start + izone
                print(f'  zone {izone}: {pbags[z+1][0] - pbags[z][0]} gen, {pbags[z+1][1] - pbags[z][1]} mod')
                pgen_start = pbags[z][0]
                pgen_count = pbags[z+1][0] - pbags[z][0]
                for igen in range(pgen_count):
                    print(f'    pgen {gen_dict[pgens[pgen_start + igen][0]]} {pgens[pgen_start + igen][1]}')
