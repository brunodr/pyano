# Piano
# 
# A simple multi-touch piano.

from scene import *
import sound
import ui
from itertools import chain
import midi
import math
from time import sleep

mi = midi.MIDIInstrument()
instrum =  46
mi.loadInstrument(512*0+instrum)# 46 harp, 11 vibra, 14 tubular bels
# 68 oboi, 71 clarinette, 60 cor, 19 orgue, 52 voix

nbinw = 18#22 # nb white keys in width
fracKey = 0.5 # fraction of first white key in width
pblstart = 52.5 # wind start in white key scale
wGap = 70 # Top keyboard ribon
corrH = 0#-6 # to center key because PORTRAIT
scale = 0 # flag to scale or slide keyboard
blackRat = 0.5 # for blak keys 

def get_keys(startf, nb_whites):
  '''Return list of piano keys in the form (k, c) where k is the midi code and c is the color 'b' for black and 'w' for white' '''
  start = math.floor(startf)
  res = []
  n_w = 0
  for k in range(start, start+2*nb_whites):
      is_black = k % 12 in (1, 3, 6, 8, 10)
      res.append((k, 'b' if is_black else 'w'))
      if not is_black:
          n_w += 1
          if n_w == nb_whites:
              break
  return res


class Key(ShapeNode):
    def __init__(self, frame, hitFrame=None):
        path = ui.Path.rounded_rect(0, 0, frame.w, frame.h, frame.w/6)
        super().__init__(path)
        self.hitFrame = hitFrame if hitFrame else frame
        self.position = Point(frame.x + (frame.w)/ 2, frame.y + frame.h / 2)
        self.name = None
        self.touch = None
        self.stroke_color = (0, 0, 0, 1)
        self.base_color = (1, 1, 1, 1)
        self.highlight_color = (0.9, 0.9, 0.9, 1)
        self.fill_color = self.base_color

    def hit_test(self, touch):
        touch.location.y += corrH/ nbinw
        return touch.location in self.hitFrame

class Piano (Scene):
    touchx  = None # for keyboard dragging
    def __init__(self):
        super().__init__()
        self.white_keys = []
        self.black_keys = []
    
    def setup(self):
        self.init()
        btn = ui.Button('A')
        btn.x = 0
        btn.y = self.size.h - wGap
        btn.width = 50
        btn.height = wGap
        self.view.add_subview(btn)    
        
    def button_tapped(sender):
        print('button tapped')
        
    def init(self):
        for key in chain(self.black_keys, self.white_keys):
            key.remove_from_parent()
        self.white_keys.clear()
        self.black_keys.clear()
        key_h = self.size.h - wGap
        key_w = self.size.w / nbinw
        pos = math.floor(pblstart)-pblstart-1
        for key_name, color in get_keys(pblstart, int(nbinw)+3):
            if color == 'w':
                key = Key(Rect(pos * key_w-0.5, 0, key_w+0.5, key_h))
                pos += 1
            else:
                frame = Rect((pos - 0.5) * key_w + key_w *0.2, key_h * (1-blackRat), key_w - key_w * 0.4, key_h * blackRat)
                hitFrame = Rect((pos - 0.45) * key_w-0.5,key_h * (1-blackRat), key_w+1,key_h * blackRat)
                key = Key(frame, hitFrame)
                key.z_position = 10.0
            key.name = key_name
            if color == 'w':
                self.white_keys.append(key)
            else:
                key.base_color = (0, 0, 0, 1)
                key.highlight_color = (0.3, 0.3, 0.3, 0.9)
                self.black_keys.append(key)
            key.fill_color = key.base_color
            self.add_child(key)
        #v = ui.load_view('pyanoview')
        #v.frame = (0, 0, 360, 400)
        #v.present('sheet')

    def touch_began(self, touch):
        global pblstart
        global scale
        for key in chain(self.black_keys, self.white_keys):
            if key.hit_test(touch):
                self.pressKey(key, touch)
                return
        if touch.location.y < self.size.h - wGap:
            return # Only on ribon
        self.touchx=touch
        if touch.location.x > (self.size.w - 60):
            scale= not scale
            return
        global instrum
        if touch.location.x < 60:  
            instrum += 1
        elif touch.location.x < 120 and instrum != 0:
            instrum -= 1
        else:
            return
        global mi
        mi = midi.MIDIInstrument()
        mi.loadInstrument(512*0+instrum)
        #print(instrum)
        #Node.e
        #LabelNode('155')
        return
         
    def touch_moved(self, touch):
        hit_key = None
        global nbinw
        if self.touchx is not None:
            delt= -(touch.location.x- self.touchx.location.x)/(self.size.w / nbinw)
            if not scale:
                if abs(delt)> 0.02:
                    global pblstart
                    pblstart+=delt
                    blk = ((math.floor(pblstart)% 12) in (1, 3, 6, 8, 10))
                    if delt < 0:
                        blk *=-1
                    pblstart += blk
                    self.touchx = touch
                    self.init()
                    return
            else:
                nbinw+=delt
                self.touchx = touch
                self.init()
            return
        for key in chain(self.black_keys, self.white_keys):
            hit = key.hit_test(touch)
            if hit and hit_key is None:
                hit_key = key
                self.pressKey(key, touch)
            if key.touch == touch and key is not hit_key:
                self.releaseKey(key)
                    

    def touch_ended(self, touch):
        self.touchx = None
        for key in chain(self.black_keys, self.white_keys):
            if key.touch == touch:
                self.releaseKey(key)
    
    def pressKey(self, key, touch):
        if key.touch is None:
            key.touch = touch
            key.fill_color = key.highlight_color
            mi.playNote(key.name)

    def releaseKey(self, key):
        key.fill_color = key.base_color
        key.touch = None
        mi.stopNote(key.name)
        

run(Piano(),LANDSCAPE)
