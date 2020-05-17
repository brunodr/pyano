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
mi.loadInstrument(0, 0)# 46 harp, 11 vibra, 14 tubular bels
# 68 oboi, 71 clarinette, 60 cor, 19 orgue, 52 voix

nbinw = 18#22 # nb white keys in width
fracKey = 0.5 # fraction of first white key in width
pblstart = 52.5 # wind start in white key scale
wGap = 70 # Top keyboard ribon
corrH = 0#-6 # to center key because PORTRAIT
scale = 0 # flag to scale or slide keyboard
blackRat = 0.5 # for blak keys 

def get_keys(startf, nb_whites):
  '''Return list of piano keys in the form (k, c) where k is the midi code and c is the color 'b' for black and 'w' for white'''
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
        wGap = self.size.h - (self.size.w/2.67)
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
        #mi.loadInstrumentd(512*0+instrum)
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


class PresetsDataSourceDelegate:

    def __init__(self, presets):
        self.presets = presets
    
    def tableview_number_of_sections(self, tableview):
        # Return the number of sections (defaults to 1)
        return 1

    def tableview_number_of_rows(self, tableview, section):
        # Return the number of rows in the section
        return len(self.presets)

    def tableview_cell_for_row(self, tableview, section, row):
        # Create and return a cell for the given section/row
        cell = ui.TableViewCell()
        cell.text_label.text = self.presets[row][2]
        return cell

    def tableview_title_for_header(self, tableview, section):
        # Return a title for the given section.
        # If this is not implemented, no section headers will be shown.
        return None

    def tableview_can_delete(self, tableview, section, row):
        # Return True if the user should be able to delete the given row.
        return False

    def tableview_can_move(self, tableview, section, row):
        # Return True if a reordering control should be shown for the given row (in editing mode).
        return False

    def tableview_delete(self, tableview, section, row):
        # Called when the user confirms deletion of the given row.
        pass

    def tableview_move_row(self, tableview, from_section, from_row, to_section, to_row):
        # Called when the user moves a row with the reordering control (in editing mode).
        pass

    def tableview_did_select(self, tableview, section, row):
        # Called when a row was de-selected (in multiple selection mode).
        p = self.presets[row]
        mi.loadInstrument(*p[:2])
        
        
if __name__ == '__main__':
    side_panel_width = 200 
    side_panel_y = 30
    view = SceneView()
    view.scene = Piano()
    presets = list(mi.getPresets())
    
    presets.sort(key = lambda x:(x[1], x[0]))
    table = ui.TableView()
    table.data_source = PresetsDataSourceDelegate(presets)
    table.delegate = table.data_source
    table.width = side_panel_width
    table.x = -side_panel_width
    table.y = side_panel_y
    table.height = view.height - side_panel_y
    table.flex = 'H'
    view.add_subview(table)
    b = ui.Button(title='____Presets')
    b.background_color=(1,1,0)
    view.add_subview(b)
    def open_close_panel(sender):
        closing = table.x == 0
        def animation(closing=closing):
            table.x = -side_panel_width if closing else 0
            view.scene.x = 0 if closing else side_panel_width
        ui.animate(animation, duration=0.5)
    b.action = open_close_panel
    view.present(orientations=LANDSCAPE)

