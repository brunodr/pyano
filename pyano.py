# Piano
# 
# A simple multi-touch piano.

from scene import *
import sound
from itertools import chain

white_key_names = [
	'C3',
	'D3', 
	'E3',
	'F3',
	'G3',
	'A3', 
	'B3',
	'C4',
	'D4',
	'E4',
	'F4',
	'G4']
white_key_names = [f'Piano_{n}' for n in white_key_names] 

class Key (object):
	def __init__(self, frame, hitFrame=None):
		self.frame = frame
		self.hitFrame = hitFrame if hitFrame else frame
		self.name = None
		self.touch = None
		self.color = Color(1, 1, 1, 1)
		self.highlight_color = Color(0.9, 0.9, 0.9, 1)

	def hit_test(self, touch):
		return touch.location in self.hitFrame

class Piano (Scene):
	def setup(self):
		self.white_keys = []
		self.black_keys = []
		black_key_names = [
			'Piano_C3#', 
			'Piano_D3#', 
			'Piano_F3#', 
		  'Piano_G3#', 
		  'Piano_A3#',
		  'Piano_C4#', 
			'Piano_D4#', 
			'Piano_F4#', 
		  'Piano_G4#']
		for key_name in chain(white_key_names, black_key_names):
			sound.load_effect(key_name)
		white_positions = range(14)
		black_positions = [0.5, 1.5, 3.5, 4.5, 5.5, 7.5, 8.5, 10.5,11.5, 12.5]
		key_w = self.size.w
		key_h = self.size.h / 12
		for i in range(len(white_key_names)):
			pos = white_positions[i]
			key = Key(Rect(0, pos * key_h, key_w, key_h))
			key.name = white_key_names[i]
			self.white_keys.append(key)
		for i in range(len(black_key_names)):
			pos = black_positions[i]
			frame = Rect(0, pos * key_h + 10, key_w * 0.6, key_h - 20)
			hitFrame = Rect(0, pos * key_h, key_w * 0.6, key_h)
			key = Key(frame, hitFrame)
			key.name = black_key_names[i]
			key.color = Color(0, 0, 0, 1)
			key.highlight_color = Color(0.2, 0.2, 0.2, 1)
			self.black_keys.append(key)

	def draw(self):
		stroke_weight(1)
		stroke(0.5, 0.5, 0.5)
		for key in chain(self.white_keys, self.black_keys):
			if key.touch is not None:
				fill(*key.highlight_color.as_tuple())
			else:
				fill(*key.color.as_tuple())
			rect(*key.frame.as_tuple())

	def touch_began(self, touch):
		for key in chain(self.black_keys, self.white_keys):
			if key.hit_test(touch):
				key.touch = touch
				sound.play_effect(key.name)
				return

	def touch_moved(self, touch):
		hit_key = None
		for key in chain(self.black_keys, self.white_keys):
			hit = key.hit_test(touch)
			if hit and hit_key is None:
				hit_key = key
				if key.touch is None:
					key.touch = touch
					sound.play_effect(key.name)
			if key.touch == touch and key is not hit_key:
				key.touch = None

	def touch_ended(self, touch):
		for key in chain(self.black_keys, self.white_keys):
			if key.touch == touch:
				key.touch = None

run(Piano(), PORTRAIT)
