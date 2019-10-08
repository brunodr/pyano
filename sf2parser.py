# Parser based on SoundFont 2 specification available here:
#.    http://freepats.zenvoid.org/sf2/sfspec24.pdf


from struct import unpack
from pathlib import Path
import mmap


def get_sf2_preset_list(sf2path):
    with open(sf2path, 'rb') as f:
        chk_dict = _parse_chunks(f)
        return _parse_phdr_chunk(f, *chk_dict['sfbk']['pdta']['phdr'])


def _unpack_chunk_header(f, pos):
    f.seek(pos)
    chkid, chklen = unpack('4sI', f.read(8))
    return (chkid.decode('ascii'), chklen)


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


def _parse_inst_chunk(f, pos, chklen):
    res = []
    pos += 8
    end = pos + chklen
    f.seek(pos)
    index = 0
    while pos + 22 <= end:
        name, bagindex = unpack('20sH', f.read(22))
        eos = name.find(0)
        if eos >= 0:
            name = name[:eos]
        res.append((index, name.decode('ascii', errors='replace')))
        pos += 22
        index += 1
    return res
        
'''
CHAR achPresetName[20]; WORD wPreset;
WORD wBank;
WORD wPresetBagNdx; DWORD dwLibrary; DWORD dwGenre; DWORD dwMorphology;
'''
def _parse_phdr_chunk(f, pos, chklen):
    res = []
    pos += 8
    end = pos + chklen
    f.seek(pos)
    while pos + 38 <= end:
        name, preset, bank, bagindex, lib, genre, morph = unpack('<20sHHHIII', f.read(38))
        eos = name.find(0)
        if eos >= 0:
            name = name[:eos]
        res.append((preset, bank, name.decode('ascii', errors='replace')))
        pos += 38
    return res    


class Sf2Parser:
    def __init__(fpath):
        pass


if __name__ == '__main__':
    sf2_folder = Path(__file__).parent / 'SoundBanks'
    sf2_files = [str(f) for f in sf2_folder.glob('*.*')]
    with open(sf2_files[0], "rb") as f:
        chk_dict = _parse_chunks(f)
        for inst in _parse_phdr_chunk(f, *chk_dict['sfbk']['pdta']['phdr']):
            print(inst)
