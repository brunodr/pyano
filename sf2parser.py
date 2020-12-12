#!/usr/bin/python3

'''
Parser based on SoundFont 2 specification available here:
http://freepats.zenvoid.org/sf2/sfspec24.pdf
'''

import struct
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
_phdr_fmt = '<20sHHHIII'
def _phdr_parse(buff, pos):
    name, preset, bank, bagindex = struct.unpack_from('<20sHHH', buff, pos)
    return (__convstr(name), preset, bank, bagindex)
  
'''
struct sfPresetBag {
    WORD wGenNdx;
    WORD wModNdx; };
'''
_pbag_fmt = '<HH'


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
_pgen_fmt = '<HH'
def _pgen_parse(buff, pos):
    genType, data = struct.unpack_from('<HH', buff, pos)
    if genType == 43 or genType == 44:
        _, low, high = struct.unpack_from('<HBB', buff, pos)
        data = (low, high)
    return (genType, data)


'''
struct sfInst {
    CHAR achInstName[20];
    WORD wInstBagNdx; };
'''
_inst_fmt = '<20sH'
def _inst_parse(buff, pos):
    name, bagindex = struct.unpack_from('<20sH', buff, pos)
    return (__convstr(name), bagindex)


'''
struct sfInstGenList {
    SFGenerator sfGenOper;
    genAmountType genAmount; };
'''
_igen_fmt = _pgen_fmt
_igen_parse = _pgen_parse


_chunk_desc_dict = {
    'phdr': (_phdr_fmt, _phdr_parse),
    'inst': (_inst_fmt, _inst_parse),
    'pbag': (_pbag_fmt, None),
    'pgen': (_pgen_fmt, _pgen_parse),
    'igen': (_igen_fmt, _igen_parse),
}


def get_sf2_preset_list(sf2path):
    '''
    Return the list of presets in the sound font file in the form
    of a list of tuples [(preset_index, bank, preset_name), ...]
    '''
    with open(sf2path, 'rb') as f:
        chk_dict = _parse_chunks(f)
        presets = chk_dict['sfbk']['pdta']['phdr'][:]
        # The raw preset list contains a terminal entry which we need to remove
        return [(p[1], p[2], p[0]) for p in presets[:-1]]


class Chunk:
    '''
    Utility class for reading SF2 file chunks.
    '''
    def __init__(self, name, f, pos, size, fmt, parse_func=None):
        self.f = f
        self.pos = pos
        self.chunk_size = size
        self.elem_size = struct.calcsize(fmt)
        self.format = fmt
        self.elem_count = self.chunk_size // self.elem_size
        self.parse_func = parse_func

    def __len__(self):
        return self.elem_count

    def __getitem__(self, key):
        if isinstance(key, slice):
            if key.start is None:
                start = 0
            else:
                start = key.start
                self.__checkindex(start)
            if key.stop is None:
                stop = self.elem_count
            else:
                stop = key.stop
                self.__checkindex(stop)
            count = stop - start
            if count <= 0:
                return []
            self.f.seek(self.pos + 8 + start * self.elem_size)
            buff = self.f.read(self.elem_size * count)
            if self.parse_func:
                return [self.parse_func(buff, i * self.elem_size) for i in range(count)]
            else:
                return [struct.unpack_from(self.format, buff, i * self.elem_size) for i in range(count)]
        else:
            self.__checkindex(key)
            self.f.seek(self.pos + 8 + key * self.elem_size)
            buff = self.f.read(self.elem_size)
            if self.parse_func:
                return self.parse_func(buff, 0)
            else:
                return struct.unpack(self.format, buff)

    def __checkindex(self, index):
        if not isinstance(index, int):
            raise TypeError('Invalid index type')
        if index < 0 or index >= self.elem_count:
            raise IndexError(f'Index {index} is out of range')


def _unpack_chunk_header(f, pos):
    f.seek(pos)
    chkid, chklen = struct.unpack('4sI', f.read(8))
    return (chkid.decode('ascii'), chklen)


def _cleanstr(s):
    eos = s.find(0)
    return s[:eos] if eos >= 0 else s


def __convstr(s):
    return _cleanstr(s).decode('ascii', errors='replace')


def _print_riff_struct(f, pos):
     chkid, chklen = _unpack_chunk_header(f, pos)
     end = pos + 8 + chklen
     if chkid in ['RIFF', 'LIST']:
         subid = struct.unpack('4s', f.read(4))[0].decode('ascii')
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
             subid = struct.unpack('4s', f.read(4))[0].decode('ascii')
             sub_dict = {}
             chk_dict[subid] = sub_dict
             pos += 12
             while pos < end:
                 pos += parse_rec(pos, sub_dict)
         else:
            chkdef = _chunk_desc_dict.get(chkid)
            if chkdef:
                chk_dict[chkid] = Chunk(chkid, f, pos, chklen, chkdef[0], chkdef[1])
            else:
                chk_dict[chkid] = None
         return chklen + 8
    top_dict = {}
    parse_rec(0, top_dict)
    return top_dict



if __name__ == '__main__':
    sf2_folder = Path(__file__).parent / 'SoundBanks'
    sf2_files = [str(f) for f in sf2_folder.glob('*.*')]
    with open(sf2_files[0], "rb") as f:
        chk_dict = _parse_chunks(f)
        pdta = chk_dict['sfbk']['pdta']
        presets = pdta['phdr'][:]
        pbags = pdta['pbag'][:]
        pgens = pdta['pgen'][:]
        igens = pdta['igen'][:]
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
