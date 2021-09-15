try:
	import vim
except ImportError:
	raise ImportError("This module is only available from vim!")

try:
	import buffer
except ImportError:
	raise ImportError("This module is only available with buffer module!")

import os, shelve

class YoSpellchecker:
	def __init__(self, path, buffer):
		self.buffer	= buffer

		self.yo_path	= path
		self.yo_txt	= path + ".txt"

		self.optional	= {}
		self.necessary	= {}

		side		= r"[^\s\.\,\"\'\-\:\\\/\<\>\;\(\)\!\?\_\[\]]*"
		center		= r"[е|Е]"

		self.pattern	= self.buffer.re.compile(side + center + side)

	#----auxilliary methods----

	def __fix_case(self, left, right):
		"""
		Return:		str | None

		Checks left argument case, and returns right argument
		int the same case
		If case wasn't recognized, returns None
		"""
		if left.islower():
			return right.lower()
		elif left.isupper():
			return right.upper()
		elif left.istitle():
			return right.title()

	def read_txt(self):
		"""
		Return:		None

		Reads words from .txt
		"""
		optional	= {}
		necessary	= {}

		print("Refreshing database...")

		with open(self.yo_txt, "r") as file:
			for i in file.readlines():
				if i.startswith("*"):
					optional[i[2:].replace("ё", "е").strip()] = i[2:].strip()
				else:
					necessary[i.replace("ё", "е").strip()] = i.strip()
		self.optional	= optional
		self.necessary	= necessary

	def necessary_correction(self):
		"""
		Return:		None

		Finds in buffer words, written with 'E' | 'e' letter
		and replaces them in buffer, if it is necessary
		"""
		pattern	= self.buffer.re.compile(self.pattern)
		matches	= [i for i in self.buffer.re.finditer(pattern) \
				if i.group().decode(self.buffer.encoding).lower() in self.necessary]
		counter = len(matches)


		if not counter:
			msg	= "No words, written without necessary YO were found!"
			action	= self.buffer.interactive(None, None, msg, "&Ok", 0)
			return

		msg	= "%d words, written without necessary YO were found!"\
				"Do you want to correct them?" % counter
		choices	= "&Yes\n&No"
		action	= self.buffer.interactive(None, None, msg, choices, 1)
	
		if action == 1:
			for i in range(counter):
				word		= matches[i].group().decode()
				replacement	= self.necessary[word.lower()]
				replacement	= self.__fix_case(word, replacement)
				self.buffer[matches[i].start():matches[i].end()] = replacement.encode()
		self.buffer.vim2py()

	def optional_correction(self):
		"""
		Return:		None

		Finds words, which optionally may be written with YO
		Highlights them and gives user an option to correct
		them one by one, or to correct them all at once
		"""
		pattern = self.buffer.re.compile(self.pattern)
		matches	= [i for i in self.buffer.re.finditer(pattern) \
				if i.group().decode(self.buffer.encoding).lower() in self.optional]
		counter	= len(matches)

		if not counter:
			msg	= "No words, written without optional YO were found!"
			action	= self.buffer.interactive(None, None, msg, "&Ok", 0)
			return

		msg	= "%d words with optional YO were found!"\
				"You can choose which words to correct,"\
				"or to correct them all at once!"
		choices	= "&Correct\n&All\n&Backwards\n&Forward\n&Exit"
		pointer	= 0

		start	= matches[0].start()
		end	= matches[0].end()

		action	= self.buffer.interactive(start, end, msg % counter, choices, 0)
		while action != 5:
			if action == 1:
				# correct one highlighted word
				word		= matches[pointer].group().decode(self.buffer.encoding)
				replacement	= self.optional[word.lower()]
				replacement	= self.__fix_case(word, replacement)

				self.buffer[start:end] = replacement

				del matches[pointer]

				if pointer > len(matches) - 1:
					pointer = 0

				counter -= 1

				if matches == []:
					break

				start		= matches[pointer].start()
				end		= matches[pointer].end()
			elif action == 2:
				# correct all the words

				for i in range(len(matches)):
					start	= matches[i].start()
					end	= matches[i].end()
					word	= matches[i].group().decode(self.buffer.encoding)

					replacement	= self.optional[word.lower()]
					replacement	= self.__fix_case(word, replacement)

					self.buffer[start:end] = replacement
				counter = 0
			elif action == 3:
				# go to previous word

				pointer -= 1

				if pointer < 0:
					pointer = len(matches) - 1

				start	= matches[pointer].start()
				end	= matches[pointer].end()
			elif action == 4:
				# go to next word

				pointer += 1

				if pointer > len(matches) - 1:
					pointer = 0

				start	= matches[pointer].start() 
				end	= matches[pointer].end()
			elif action == 5:
				# cancel
				break
			if counter == 0:
				break
			action	= self.buffer.interactive(start, end, msg % counter, choices, 0)
		self.buffer.vim2py()

def main():
	import re

	path		= os.path.splitext(vim.eval("g:vim_yo_dict"))[0]
	buf		= buffer.Buffer()
	spellchecker	= YoSpellchecker(path, buf)

	spellchecker.read_txt()

	spellchecker.necessary_correction()
	spellchecker.optional_correction()
