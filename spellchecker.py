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
		self.yo_dat	= path + ".dat"

		self.optional	= {}
		self.necessary	= {}

		side		= r"[^\s\.\,\"\'\-\:\\\/\<\>\;\(\)\!\?\_\[\]]*"
		center		= r"[е|Е]"

		self.pattern	= side + center + side

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

	def refresh_db(self):
		"""
		Return:		None

		Reads words from .txt dictionary and replaces old
		.dat file with a new one
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

		if os.path.isfile(self.yo_dat):
			os.remove(self.yo_dat)

		db		= shelve.open(self.yo_dat)
		db["optional"]	= optional
		db["necessary"]	= necessary
		db.close()

	def read_db(self):
		"""
		Return:		None

		Reads .dat word database and puts data into
		instance.optional and instance.necessary dictionaries
		"""
		try:
			db = shelve.open(self.yo_dat)
		except FileNotFoundError:
			raise FileNotFoundError("")
		self.optional	= db["optional"]
		self.necessary	= db["necessary"]

	def necessary_correction(self):
		"""
		Return:		None

		Finds in buffer words, written with 'E' | 'e' letter
		and replaces them in buffer, if it is necessary
		"""
		pattern	= self.buffer.re.compile(self.pattern)
		matches	= self.buffer.re.findall(pattern)
	
		repl = set()
		counter = 0

		for i in range(len(matches)):
			if matches[i].lower() in self.necessary.keys():
				repl.add(matches[i])
				counter += 1

		if counter == 0:
			msg	= "No words, written without necessary YO were found!"
			action	= self.buffer.interactive(None, None, msg, "&Ok", 0)
			return

		msg	= "%d words, written without necessary YO were found!"\
				"Do you want to correct them?" % counter
		choices	= "&Yes\n&No"
		action	= self.buffer.interactive(None, None, msg, choices, 1)
		
		if action == 1:
			for i in range(counter):
				
				word		= repl.pop()
				replacement	= self.necessary[word.lower()]
				replacement	= self.__fix_case(word, replacement)
		
				self.buffer.replace(word, replacement)
		self.buffer.vim2py()

	def optional_correction(self):
		"""
		Return:		None

		Finds words, which optionally may be written with YO
		Highlights them and gives user an option to correct
		them one by one, or to correct them all at once
		"""
		pattern = self.buffer.re.compile(self.pattern)
		matches	= self.buffer.re.findall(pattern)

		repl	= []
		for i in range(len(matches)):
			if matches[i].lower() in self.optional.keys():
				repl.append(matches[i])

		counter	= len(repl)

		if counter == 0:
			msg	= "No words, written without optional YO were found!"
			action	= self.buffer.interactive(None, None, msg, "&Ok", 0)
			return

		msg	= "%d words with optional YO were found!"\
				"You can choose which words to correct,"\
				"or to correct them all at once!"
		choices	= "&Correct\n&All\n&Backwards\n&Forward\n&Exit"

		pointer	= 0

		start	= self.buffer.find(repl[pointer])
		h_end	= start + len(repl[pointer].encode(self.buffer.encoding))
		end	= start + len(repl[pointer])

		action	= self.buffer.interactive(start, h_end, msg % counter, choices, 0)
		while action != 5:
			if action == 1:
				# correct one highlighted word
				word		= repl[pointer]
				replacement	= self.optional[word.lower()]
				replacement	= self.__fix_case(word, replacement)

				self.buffer[start:end] = replacement

				del repl[pointer]

				if pointer > len(repl) - 1:
					pointer = 0

				counter -= 1

				if repl == []:
					break

				start	= self.buffer.find(repl[pointer])
				h_end	= start + len(repl[pointer].encode(self.buffer.encoding))
				end	= start + len(repl[pointer])
			elif action == 2:
				# correct all the words

				for i in range(len(repl)):
					start	= self.buffer.find(repl[i])
					end	= start + len(repl[i])

					word		= repl[i]
					replacement	= self.optional[word.lower()]
					replacement	= self.__fix_case(word, replacement)

					self.buffer[start:end] = replacement
				counter = 0
			elif action == 3:
				# go to previous word

				pointer -= 1

				if pointer < 0:
					pointer = len(repl) - 1

				start	= self.buffer.find(repl[pointer])
				h_end	= start + len(repl[pointer].encode(self.buffer.encoding))
				end	= start + len(repl[pointer])
			elif action == 4:
				# go to next word

				pointer += 1

				if pointer > len(repl) - 1:
					pointer = 0

				start	= self.buffer.find(repl[pointer])
				h_end	= start + len(repl[pointer].encode(self.buffer.encoding))
				end	= start + len(repl[pointer])
			elif action == 5:
				# cancel
				break
			if counter == 0:
				break
			action	= self.buffer.interactive(start, h_end, msg % counter, choices, 0)
		self.buffer.vim2py()

def main():
	path		= os.path.splitext(vim.eval("g:vim_yo_dict"))[0]
	buf		= buffer.Buffer()

	spellchecker	= YoSpellchecker(path, buf)
	spellchecker.read_db()
	spellchecker.necessary_correction()
	spellchecker.optional_correction()

