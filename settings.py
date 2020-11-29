import json
from pathlib import Path
from midi import Preset


def preset_to_json(p):
    if p is None:
        return None
    return (p.index, p.bank, p.name, p.sb)


def json_to_preset(j):
    if j is None:
        return None
    return Preset(j[0], j[1], j[2], j[3])


class Settings:
    def __init__(self):
        self.soundbank = ['*']
        self.nbinw = 18.     #22 # nb white keys in width
        self.pblstart = 52.5 # wind start in white key scale
        self.wGap = 70       # Top keyboard ribon
        self.corrH = 0.      #-6 # to center key because PORTRAIT
        self.scale = False   # flag to scale or slide keyboard
        self.blackRat = 0.5  # for blak keys
        self.decal = 0       # global half tone decalage
        self.currentPreset = None
    
    @staticmethod        
    def load():
        path = Path(__file__).parent / 'settings.json'
        settings = Settings()
        if path.exists():
            settings.__dict__.update(json.loads(path.read_text()))
            settings.currentPreset = json_to_preset(settings.currentPreset)
        return settings    

    def save(self):
        path = Path(__file__).parent / 'settings.json'
        tmp = dict(self.__dict__)
        tmp['currentPreset'] = preset_to_json(tmp['currentPreset'])
        path.write_text(json.dumps(self.__dict__, indent=2))
 
