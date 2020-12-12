#!/usr/bin/python3

'''
Parser based on SoundFont 2 specification available here:
http://freepats.zenvoid.org/sf2/sfspec24.pdf
'''

import struct
import argparse
from pathlib import Path


class PresetNotFoundError(Exception):
    pass


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
18: "unused2",
19: "unused3",
20: "unused4",
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
49: "reserved2",
50: "endloopAddrsCoarseOffset",
51: "coarseTune",
52: "fineTune",
53: "sampleID",
54: "sampleModes",
55: "reserved3",
56: "scaleTuning",
57: "exclusiveClass",
58: "overridingRootKey", }


sample_type_dict = {
1: "monoSample",
2: "rightSample",
4: "leftSample",
8: "linkedSample",
0x8001: "RomMonoSample",
0x8002: "RomRightSample",
0x8004: "RomLeftSample",
0x800: "RomLinkedSample",
}


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
struct sfModList
{
    SFModulator sfModSrcOper;
    SFGenerator sfModDestOper;
    SHORT modAmount;
    SFModulator sfModAmtSrcOper;
    SFTransform sfModTransOper;
};
'''
_pmod_fmt = '<HHhHH'


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
struct sfInstBag
{
    WORD wInstGenNdx;
    WORD wInstModNdx;
};
'''
_ibag_fmt = '<HH'


'''
struct sfInstGenList {
    SFGenerator sfGenOper;
    genAmountType genAmount; };
'''
_igen_fmt = _pgen_fmt
_igen_parse = _pgen_parse


'''
struct sfModList
{
    SFModulator sfModSrcOper;
    SFGenerator sfModDestOper;
    SHORT modAmount;
    SFModulator sfModAmtSrcOper;
    SFTransform sfModTransOper;
};
'''
_imod_fmt = '<HHhHH'


'''
struct sfSample
{
    CHAR achSampleName[20];
    DWORD dwStart;
    DWORD dwEnd;
    DWORD dwStartloop;
    DWORD dwEndloop;
    DWORD dwSampleRate;
    BYTE byOriginalPitch;
    CHAR chPitchCorrection;
    WORD wSampleLink;
    SFSampleLink sfSampleType;
};
'''
_shdr_fmt = '<20sIIIIIBbHH'
def _shdr_parse(buff, pos):
    name, *others = struct.unpack_from(_shdr_fmt, buff, pos)
    return (__convstr(name), *others)


_chunk_desc_dict = {
    'phdr': (_phdr_fmt, _phdr_parse),
    'pbag': (_pbag_fmt, None),
    'pgen': (_pgen_fmt, _pgen_parse),
    'pmod': (_pmod_fmt, None),
    'inst': (_inst_fmt, _inst_parse),
    'ibag': (_igen_fmt, None),
    'igen': (_igen_fmt, _igen_parse),
    'imod': (_imod_fmt, None),
    'shdr': (_shdr_fmt, _shdr_parse),
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


def main(args):
    with open(args.path, "rb") as f:
        riff = _parse_chunks(f)
        if args.subcommand == 'preset':
            _cli_preset(args, riff)
        elif args.subcommand == 'instrument':
            _cli_instrument(args, riff)
        elif args.subcommand == 'sample':
            _cli_sample(args, riff)


def _get_preset_index(presets, number, bank):
    for i, p in enumerate(presets):
        if p[1] == number and p[2] == bank:
            return i
    raise PresetNotFoundError(f'Could not find preset {number} in bank {bank}')


def _print_preset_info(riff, presets, pbags, index):
    p = presets[index]
    n = presets[index + 1]
    zones = pbags[p[3]:n[3]+1]
    zone_count = len(zones) - 1
    print(f'Preset "{p[0]}" {p[1], p[2]} {zone_count} zone(s)')
    pgens = riff['sfbk']['pdta']['pgen']
    pmods = riff['sfbk']['pdta']['pmod']
    for izone in range(zone_count):
        gens = pgens[zones[izone][0]:zones[izone+1][0]]
        mods = pmods[zones[izone][1]:zones[izone+1][1]]
        print(f'  - zone {izone}: {len(gens)} gen, {len(mods)} mod')
        for gen in gens:
            print(f'    - gen {gen_dict[gen[0]]} {gen[1]}')
        for mod in mods:
            print(f'    - mod {mod}')


def _print_instrument_info(riff, instruments, ibags, index):
    p = instruments[index]
    n = instruments[index + 1]
    zones = ibags[p[1]:n[1]+1]
    zone_count = len(zones) - 1
    print(f'Instrument "{p[0]}" #{index} {zone_count} zone(s)')
    igens = riff['sfbk']['pdta']['igen']
    imods = riff['sfbk']['pdta']['imod']
    for izone in range(zone_count):
        gens = igens[zones[izone][0]:zones[izone+1][0]]
        mods = imods[zones[izone][1]:zones[izone+1][1]]
        print(f'  - zone {izone}: {len(gens)} gen, {len(mods)} mod')
        for gen in gens:
            print(f'    - gen {gen_dict[gen[0]]} {gen[1]}')
        for mod in mods:
            print(f'    - mod {mod}')


def _get_sample_info(s):
    return f'"{s[0]}", size {s[2] - s[1]}, rate {s[5]}, type {sample_type_dict[s[9]]}, opitch {s[9]}'


def _cli_preset(args, riff):
    presets = riff['sfbk']['pdta']['phdr'][:]
    if args.list:
        for p in presets[:-1]:
            print(f'- "{p[0]}", preset {p[1]}, bank {p[2]}')
        print(f'Found {len(presets) - 1} presets')
    else:
        if args.number is None:
            pbags = riff['sfbk']['pdta']['pbag'][:]
            for index in range(len(presets) - 1):
                _print_preset_info(riff, presets, pbags, index)
        else:
            index = _get_preset_index(presets, args.number, args.bank)
            _print_preset_info(riff, presets, riff['sfbk']['pdta']['pbag'], index)


def _cli_instrument(args, riff):
    instruments = riff['sfbk']['pdta']['inst'][:]
    if args.list:
        for index, inst in enumerate(instruments[:-1]):
            print(f'- #{index} "{inst[0]}"')
        print(f'Found {len(instruments) - 1} instruments')
    else:
        if args.number is None:
            ibags = riff['sfbk']['pdta']['ibag'][:]
            for index in range(len(instruments) - 1):
                _print_instrument_info(riff, instruments, ibags, index)
        else:
            _print_instrument_info(riff, instruments, riff['sfbk']['pdta']['ibag'], args.number)


def _cli_sample(args, riff):
    if args.list:
        samples = riff['sfbk']['pdta']['shdr'][:]
        for index, s in enumerate(samples[:-1]):
            print(f'- #{index} {_get_sample_info(s)}')
        print(f'Found {len(samples) - 1} samples')
    elif args.number is not None:
        s = riff['sfbk']['pdta']['shdr'][args.number]
        print(f'Sample #{args.number} {_get_sample_info(s)}')



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='subcommand', required=True)
    # preset subcommand
    preset_parser = subparsers.add_parser('preset', help='operation on presets')
    group = preset_parser.add_mutually_exclusive_group()
    group.add_argument('-n', '--number', type=int, help='preset number (all presets if absent)')
    group.add_argument('-l', '--list', action='store_true', help='list of the presets without any detail')
    preset_parser.add_argument('-b', '--bank', type=int, default=0, help='bank number')
    # instrument subcommand
    inst_parser = subparsers.add_parser('instrument', help='operation on instruments')
    group = inst_parser.add_mutually_exclusive_group()
    group.add_argument('-n', '--number', type=int, help='instrument number (all instruments if absent)')
    group.add_argument('-l', '--list', action='store_true', help='list of the instruments without any detail')
    # sample subcommand
    sample_parser = subparsers.add_parser('sample', help='operation on samples')
    group = sample_parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-n', '--number', type=int, help='sample number')
    group.add_argument('-l', '--list', action='store_true', help='list of the samples')
    # end of main command
    parser.add_argument('path', help='SoundFont file path')
    args = parser.parse_args()
    main(args)
