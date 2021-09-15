try:
	import vim
except ImportError:
	raise "This module is only available from vim!"

import re, locale

#----EXCEPTION MSGS----

REGEX_UNICODE_EXCEPTION	= re.sub("(?m)^", " | ", 
			"You pass to compile method string, "\
			"which must be converted to Unicode. I can't do it"\
			"automaticall, cause I can't guess which codec you"\
			"need. It may be vim's 'encoding' variable (%s) or"\
			"vim's 'fileencoding' variable (%s)...")

#----GLOBAL VARS----

NEWLINES = {
	"dos"	: "\r\n",
	"unix"	: "\n",
	"mac"	: "\r"
}

#----AUXILLIARY FUNCS----

def _true_offset(u_obj, offset, encoding, prev=(0,0)):
	return len(u_obj[prev[0]:offset].encode(encoding)) + prev[1]

def _encode_if_u(obj, encoding):
	if isinstance(obj, str):
		return obj.encode(encoding)

#----MATCHOBJECT----

class MatchObject:
	"""
	If we make regexp search in unicode string by means of standart re module,
	it return sometimes Match_object, which provide access to many useful
	information. But this is informationa about unicode string in which we
	search. For work with vim buffer information about string in vim encoding
	is more useful. So, this class provides object-emulator of standart
	Match_object.
	When you expect to get a string, you get a bytes in ENCODING codec,
	not unicode.

	mo		- true match object
	encoding	- encoding for convert unicode objects
	lastindex	- integer index of the last matched capturing group, or None
	lastgroup	- the name of the last matched capturing group, or None
	re		- regex object, which match() or search() method returned
				produced this MatchObject instance
	string		- string passed to match() or search()
	pos		- value of pos which was passed to the search() or match()
				method
	endpos		- value of endpos which was passed to the search() or match()
				method
	"""
	def __init__(self, mo, encoding, old_mo=None):
		if old_mo:
			for i in ["string", "pos", "endpos"]:
				setattr(self, i, getattr(old_mo, i))
		else:
			if isinstance(mo.string, str):
				self.pos	= _true_offset(mo.string, mo.pos, encoding)
				self.endpos	= _true_offset(mo.string, mo.pos, encoding,
							(mo.pos, self.pos))
				self.string	= mo.string
			else:
				self.pos	= mo.pos
				self.endpos	= mo.endpos
				self.string	= mo.string

		self.encoding	= encoding
		self.mo		= mo
		self.lastindex	= mo.lastindex
		self.lastgroup	= mo.lastgroup
		self.re		= mo.re

	def expand(self, template):
		"""
		Return:		bytes

		Return the string, obtained by doing backslash substitution on the
		template string template, as done by the sub() method. Escapes such
		as '\\n' are converted to the appropriate characters, and numeric
		or named backreferences are replaced by contents of the corresponding
		group
		"""
		result = self.mo.expand(template)
		return _encode_if_u(result, self.encoding)

	def group(self, *gr):
		"""
		Return:		bytes / tuple of bytes

		Returns one or more subgroups of the match
		"""
		result = self.mo.group(*gr)
		if isinstance(result, tuple):
			return tuple(map(lambda x: _encode_if_u(x, self.encoding), result))
		else:
			return _encode_if_u(result, self.encoding)

	def groups(self, default=None):
		"""
		Return:		tuple

		Returns a tuple containing all the subgroups of the match
		"""
		result = self.mo.groups(default)
		return tuple(map(lambda x: _encode_if_u(x, self.encoding), result))

	def groupdict(self, default=None):
		"""
		Return:		dict

		Return a dictionary containing all the named subgroups of the match,
		keyed by the subgroup name

		All keys and values are bytes
		"""
		result = {}

		for i in self.mo.groupdict.keys():
			result[_encode_if_u(i, self.encoding)] = \
				_encode_if_u(self.mo.groupdict(default)[i], self.encoding)

	def start(self, gr=0):
		"""
		Return:		int

		Return the index of the start of the substring matched by GROUP
		"""
		if isinstance(self.mo.string, str):
			return _true_offset(self.mo.string, self.mo.start(gr), self.encoding)
		else:
			return self.mo.start(gr)

	def end(self, gr=0):
		"""
		Return:		int

		Return the index of the end of the substring matched by GROUP
		"""
		if isinstance(self.mo.string, str):
			return _true_offset(self.mo.string, self.mo.end(gr), self.encoding)
		else:
			return self.mo.end(gr)

	def span(self, gr=0):
		"""
		Return:		tuple

		Returns 2-tuple (m.start(group), m.end(group))
		"""
		if isinstance(self.mo.string, str):
			start	= self.start(gr)
			stop	= start + len(self.group(gr))
			return start, end
		else:
			self.mo.span(gr)

#----_RegExp----

class _RegExp:
	"""
	Class container
	"""
	def __init__(self, master):
		self.master = master

	def compile(self, pattern, flags=0):
		"""
		Return:		RegExp_object

		Compile a regex pattern into a regex object.
		The expression's behaviour can be modified by specified
		a FLAGS value
		"""
		if isinstance(pattern, (str, bytes)):
			if not isinstance(pattern, str):
				raise UnicodeDecodeError(REGEX_UNICODE_EXCEPTION % (
					self.master.encoding, 
					vim.eval("&fileencoding")))
			return re.compile(pattern)
		elif pattern.flags == (pattern.flags | re.U):
			return pattern
		else:
			return re.compile(pattern.pattern, flags | re.U)

	def search(self, pattern, flags=0, *pos):
		"""
		Return:		MatchObject

		Scan through buffer, looking for a location, where the regex
		pattern produces a match, and return a corresponding MatchObject
		instance
		"""
		pattern	= self.compile(pattern, flags)
		mo	= MatchObject(pattern.search(self.master.decode(), *pos), self.master.encoding)
		return mo

	def match(self, pattern, flags=0, *pos):
		"""
		Return:		MatchObject

		If zero or more characters at the beginning of buffer match this
		regex, return a corresponding MatchObject instance
		"""
		pattern	= self.compile(pattern, flags)
		mo	= MatchObject(pattern.match(self.master.decode(), *pos), self.master.encoding)
		return mo

	def split(self, pattern, maxsplit=0):
		"""
		Return:		list

		Split buffer contents bt the occurences of pattern. If capturing
		parentheses are used in patternm the the text of all groups in
		the pattern are also returned as part of the resulting list
		"""
		pattern	= self.compile(pattern)
		result	= re.split(pattern, self.master.decode(), maxsplit)
		return result

	def findall(self, pattern):
		"""
		Return:		list

		Return a list of all non-overlapping matches of pattern in buffer
		"""
		pattern	= self.compile(pattern)
		result	= re.findall(pattern, self.master.decode())
		return result

	def finditer(self, pattern):
		"""
		Return:		iterator_object

		Return an iterator over all non-overlapping matches for the RE
		pattern in string
		"""
		pattern	= self.compile(pattern)
		old_mo	= None
		for i in re.finditer(pattern, self.master.decode()):
			mo	= MatchObject(i, self.master.encoding, old_mo)
			old_mo	= mo
			yield mo

	def count(self, pattern):
		"""
		Return:		int

		Return number of occurences
		"""
		pattern	= self.compile(pattern)
		return len(map(None, pattern.finditer(self.master.decode())))

	def sub(self, pattern, repl, *count):
		"""
		Return:		None

		Change buffer by replacing the leftmost non-overlapping occurences
		of PATTERN in buffer by the replacement REPL
		"""
		pattern	= self.compile(pattern)

		try:
			result	= re.sub(pattern, repl, self.master.decode(), *count)
		except UnicodeDecodeError:
			raise UnicodeDecodeError(REGEX_UNICODE_EXCEPTION % (
					self.master.encoding,
					vim.eval("&fileencoding")))

		self.master.text = result.encode(self.master.encoding)
		self.master.py2vim()

	def subn(self, pattern, repl, *count):
		"""
		Return:		int

		Perform the same operation as sub(), but also return
		a number of substitutions made
		"""
		pattern = self.compile(pattern)
	
		try:
			result, n = re.subn(pattern, repl, self.master.decode(), *count)
		except UnicodeDecodeError:
			raise UnicodeDecodeError(REGEX_UNICODE_EXCEPTION % (
					self.master.encoding,
					vim.eval("&fileencoding")))

		self.master.text = result
		self.master.py2vim()

		return n

#----BUFFER----

class Buffer:
	"""
	This class provides simple access to vim buffer from python
	Constructor takes one optional argument - vim's buffer
	(current buffer by default)

	Buffer contents are stored in instance.text attribute

	--------------------------------------------------------------
	Synchronyzation methods:
	
		General: vim2py(), py2vim()

		Offset converting: offset2LC(), LC2offset()

	--------------------------------------------------------------
	String emulation:

	Instance of this class has most of string methods. Some
	of them work similarly as in the string, but others, which
	return changed string, really return None and modify the
	vim buffer

	count(), index(), find(), rindex(), rfind(), endswith(),
	startswith(), isalnum(), isalpha(), isdigit(), islower()
	isspace(), istitle(), isupper(), center(), rjust(),
	ljust(), zfill(), rstrip(), lstrip(), strip(), capitalize(),
	lower(), swapcase(), title(), upper(), replace(), expandtabs(),
	decode(), encode(), split(), splitlines()

	---------------------------------------------------------------
	Sequence emulation:

	Instance of this class class a lot of sequence's methods and can
	properly work with a slice

	__setitem__(), __delitem__(), __getitem__(), __len__(),
	__contains__(), __iadd__(), append(), extend(), __imul__(),
	insert(), remove(), reverse()

	---------------------------------------------------------------
	File emulation:

	Instance of this class has some file-object like methods and may
	be used for file simulation

	isatty(), close(), flush(), tell(), seek(), truncate(), read(),
	readline(), readlines(), write(), writelines()

	---------------------------------------------------------------
	Attributes

	instance.text		unicode object, containing buffer contents
	instance.newlines	EOL string ('\\r' or '\\r\\n' or '\\n')
	instance.encoding	buffer encoding (vim's &encoding)
	instance.buffer		vim.buffer object

	instance.closed		False
	instance.mode		'rb+'
	"""
	def __init__(self, buffer=vim.current.buffer):
		self.vim2py(buffer)

		self.re		= _RegExp(self)

		# file-compatitive vars
		self.closed	= False
		self.mode	= "rb+"

	#----synchronization methods----

	def vim2py(self, buffer=vim.current.buffer):
		"""
		Return:		None

		Read info from vim's buffer and update some object
		data: self.text, self.buffer, self.newlines and
		self.encoding
		"""
		self.newlines	= NEWLINES[vim.eval("&fileformat")]
		self.encoding	= re.sub(r"^(?:8bit|2byte)-", "", vim.eval("&encoding"))

		try:
			"".encode(self.encoding)
		except LookupError:
			try:
				self.encoding = {
					"ucs-2"		: "utf-8",
					"ucs-21e"	: "unicode-internal"
				}[self.encoding]
			except KeyError:
				raise LookupError("This module is not provided with %s"\
						"codec" % self.encoding)
		self.text	= self.newlines.join(buffer)
		self.buffer	= buffer

	def py2vim(self):
		"""
		Return:		None

		Write self.text into vim.buffer
		"""
		self.buffer[:] = self.text.split(self.newlines)

	def offset2LC(self, offset):
		"""
		Return:		tuple

		Get offset in python notation (zero-leader) and return
		pair (line, column) in vim notation (1-leader)
		"""
		line	= int(vim.eval("byte2line(%d)" % (offset + 1)))
		column	= offset - int(vim.eval("line2byte(%d)" % line)) + 2
		return line, column

	def LC2offset(self, line, column):
		"""
		Return:		int

		Get pair (line, column) in vim notation (1-leader) and return
		offset in python notation (zero-leader)
		"""
		result	= int(vim.eval("line2byte('%s')" % line))
		result	= result + column - 2
		return result

	#----string-like and sequence-like methods----

	def __setitem__(self, key, value):
		if not isinstance(value, (str, bytes)):
			raise TypeError("__setitem__ method takes only str | bytes!")
		if isinstance(key, int):
			if key < 0:
				key += len(self)
			if key >= len(self) or key < 0:
				raise IndexError
			key = slice(key, key + 1)

		try:
			start	= key.start or 0
			stop	= key.stop or {0:0, None:len(self)}[key.stop]
		except KeyError:
			raise TypeError
		if start < 0:
			start += len(self)
		if stop < 0:
			stop += len(self)

		start	= max(start, 0)
		stop	= max(stop, 0)

		if key.step:
			value	= value.replace("\r\n", "\n")
			value	= list(value)[::key.step]
			value	= "".join(value)

		if isinstance(value, str):
			value		= value.encode(self.encoding)

		self.text	= self.text.encode(self.encoding)[:start] + value +\
					self.text.encode(self.encoding)[stop:]
		self.text	= self.text.decode(self.encoding)
		self.py2vim()

	def __delitem__(self, key):
		"""
		"""
		self.text	= self.text[:key] + self.text[key + 1:]
		self.buffer[:]	= self.text.split(self.newlines)

	def __getitem__(self, key):
		return self.text[key]

	def __len__(self):
		return len(self.text)

	def __contains__(self, item):
		return item in self.text

	def __iadd__(self, other):
		len_s = len(self)
		self[len_s:len_s] = other

	def __imul__(self, other):
		"""
		Buffer object *= 0	-> None # delete buffer contains
		Buffer object *= 1	-> None # nothing to do
		Buffer object *= Int	-> None # duplicate buffer contains
							Int times
		"""
		if other == 0:
			self.text = ""
			self.py2vim()
		else:
			save = self.text
			for i in range(other - 1):
				self.append(save)

	def __str__(self):
		return self.text

	#----sequence-like methods----

	def append(self, other):
		"""
		Return:		None

		Appends string to the end of buffer
		"""
		self += other

	def extend(self, other):
		"""
		Return:		None

		Appends list to the end of buffer
		"""
		self += other

	def insert(self, index, other):
		"""
		Return:		None

		Insert OTHER in INDEX position
		"""
		self[index:index] = other

	def remove(self, item):
		"""
		Return:		None
		"""
		del self[self.index(item)]

	def reverse(self, how="strings"):
		"""
		Return:		None

		Reverse buffer contains

		if HOW == 'strings', reverses strings order
		if HOW == 'letters', reverses letters order
		"""
		if how == "strings":
			l = list(self.buffer)
			l.reverse()
			self[:] = self.newlines.join(l)
		elif how == "letters":
			l = list(re.sub(r"\r\n?", r"\n", self.text))
			l.reverse()
			self[:] = "".join(l).replace("\n", self.newlines)
		else:
			raise TypeError("Bad argument '%s' in reverse method" % how)

	#----info methods----

	def count(self, item, *pos):
		"""
		Return:		int

		Returns the number of occurences of substring SUB in
		buffer[start:end]
		"""
		if isinstance(item, str):
			return self.text.count(item, *pos)
		elif isinstance(item, bytes):
			return self.text.encode(self.encoding).count(item, *pos)

	def index(self, item, *pos):
		"""
		Return:		int

		Like find(), but raise ValueError, if the substring is
		not found
		"""
		if isinstance(item, str):
			return self.text.index(item, *pos)
		elif isinstance(item, bytes):
			return self.text.encode(self.encoding).index(item, *pos)

	def find(self, item, *pos):
		"""
		Return:		int

		Returns the lowest index in the buffer, where substring
		SUB is found, such that SUB is contained in the range
		(START, END)
		"""
		if isinstance(item, str):
			return self.text.find(item, *pos)
		elif isinstance(item, bytes):
			return self.text.encode(self.encoding).find(item, *pos)

	def rindex(self, item, *pos):
		"""
		Return:		int

		Like rfind() but raises ValueError when the substring
		is not found
		"""
		if isinstance(item, str):
			return self.text.rindex(item, *pos)
		elif isinstance(item, bytes):
			return self.text.encode(self.encoding).rindex(item, *pos)

	def rfind(self, item, *pos):
		"""
		Return:		int

		Returns the highest index in buffer where substring SUB is
		found, such that SUB is contained within range (START, END)
		"""
		if isinstance(item, str):
			return self.text.rfind(item, *pos)
		elif isinstance(item, bytes):
			return self.text.encode(self.encoding).rfind(item, *pos)

	def endswith(self, suffix, *pos):
		"""
		Return:		bool

		Returns True if the buffer ends with a specified SUFFIX
		Returns False if not
		"""
		if isinstance(suffix, str):
			return self.text.endswith(suffix, *pos)
		elif isinstance(suffix, bytes):
			return self.text.encode(self.encoding).endswith(suffix, *pos)

	def startswith(self, prefix, *pos):
		"""
		Return:		bool

		Returns True if the buffer starts with a specified PREFIX
		Return False if not
		"""
		if isinstance(prefix, str):
			return self.text.startswith(prefix, *pos)
		elif isinstance(prefix, bytes):
			return self.text.encode(self.encoding).startswith(prefix, *pos)

	def isalnum(self):
		"""
		Return:		bool

		"""
		return self.text.isalnum()

	def isalpha(self):
		"""
		Return:		bool
		"""
		return self.text.isalpha()

	def isdigit(self):
		"""
		Return:		bool
		"""
		return self.text.isdigit()

	def islower(self):
		"""
		Return:		bool
		"""
		return self.text.islower()

	def isspace(self):
		"""
		Return:		bool
		"""
		return self.text.isspace()

	def istitle(self):
		"""
		Return:		bool
		"""
		return self.text.istitle()

	def isupper(self):
		"""
		Return:		bool
		"""
		return self.text.isupper()

	#----line-changing methos----

	def map(self, func, *pos):
		"""
		Return:		None

		Applies FUNC to every (default) lines in buffer
		"""
		if len(pos) == 1:
			R = range(pos[0])
		elif len(pos) == 2:
			R = range(pos[0], pos[1])
		elif len(pos) == 3:
			R = range(pos[0], pos[1], pos[2])
		else:
			R = range(len(self))
		for i in R:
			try:
				self.buffer[i] = func(self.buffer[i])
			except IndexError:
				break
		self.vim2py()

	def center(self, width, *pos):
		"""
		Return:		None

		Center every (default) lines in buffer
		"""
		self.map(lambda x: x.center(width), *pos)

	def rjust(self, width, *pos):
		"""
		Return:		None

		Rjust every (default) lines in buffer
		"""
		self.map(lambda x: x.rjust(width), *pos)

	def ljust(self, width, *pos):
		"""
		Return:		None

		Ljust every (default) lines in buffer
		"""
		self.map(lambda x: x.ljust(width), *pos)

	def zfill(self, width, *pos):
		"""
		Return:		None

		Zfill every (default) lines in buffer
		"""
		self.map(lambda x: x.zfill(width), *pos)

	def rstrip(self, chars=None, *pos):
		"""
		Return:		None

		Rstrip every (default) lines in buffer
		"""
		self.map(lambda x: x.rstrip(chars), *pos)

	def lstrip(self, chars=None, *pos):
		"""
		Return:		None

		Lstrip every (default) lines in buffer
		"""
		self.map(lambda x: x.lstrip(chars), *pos)

	def strip(self, chars=None, *pos):
		"""
		Return:		None

		Strip every (default) lines in buffer
		"""
		self.map(lambda x: x.strip(chars), *pos)

	def capitalize(self, *pos):
		"""
		Return:		None

		Capitalize case in every (default) lines in
		buffer
		"""
		self.map(lambda x: x.capitalize(), *pos)

	def lower(self, *pos):
		"""
		Return:		None

		Lower case in every (default) lines in buffer
		"""
		self.map(lambda x: x.lower(), *pos)

	def swapcase(self, *pos):
		"""
		Return:		Nonee

		Swapcase in every (default) lines in buffer
		"""
		self.map(lambda x: x.swapcase(), *pos)

	def title(self, *pos):
		"""
		Return:		None

		Case like title in every (default) lines in
		buffer
		"""
		self.map(lambda x: x.title(), *pos)

	def upper(self, *pos):
		"""
		Return:		None

		Upper in every (default) lines in buffer
		"""
		self.map(lambda x: x.upper(), *pos)

	def replace(self, old, new, maxsplit=None, *pos):
		"""
		Return:		None

		Replace substring OLD to NEW in every (default)
		lines in buffer
		"""
		if isinstance(maxsplit, int):
			self.map(lambda x: x.replace(old, new, maxsplit), *pos)
		else:
			self.map(lambda x: x.replace(old, new), *pos)

	def expandtabs(self, tabsize=0, *pos):
		"""
		Return:		None

		Expand tabs in every (default) lines in buffer
		"""
		self.map(lambda x: x.expandtabs(tabsize), *pos)

	def decode(self):
		"""
		Return:		str

		Decodes the string using the codec, registered
		for self.encoding
		"""
		return self.text

	def encode(self, codec):
		"""
		Return:		bytes

		Return an encoded version of as string (in CODEC)
		"""
		return self.text.encode(codec)

	def split(self, *args):
		"""
		Return:		list

		Return a list of the words in the buffer
		"""
		return self.text.split(*args)

	def splitlines(self, *args):
		"""
		Return:		list

		Return a list of lines in the buffer
		"""
		return self.text.splitlines(*args)

	#----file-like methods----

	def isatty(self):
		"""
		!!! ALWAYS FALSE !!!
		"""
		return False

	def close(self):
		"""
		NOTHING TO DO
		"""
		return None

	def flush(self):
		"""
		NOTHING TO DO
		"""
		return None

	def tell(self):
		"""
		Return:		int

		Returns position in file
		(byte-offset, zero-leader)
		"""
		line	= int(vim.eval("line('.')"))
		column	= int(vim.eval("col('.')"))
		return self.LC2offset(line, column)

	def seek(self, offset, whence=0):
		"""
		Return:		None

		Move to a new file position
		whence == 0	-> movement relative to the start of file
		whence == 1	-> movement relative to current position
		whence == 2	-> movemetn relative to the end of file
		"""
		if whence == 0:
			vim.eval("cursor(%d, %d)" % self.offset2LC(offset))
		elif whence == 1:
			line		= int(vim.eval("line('.')"))
			column		= int(vim.eval("col('.')"))
			current_offset	= self.LC2offset(line, column)
			vim.eval("cursor(%d,%d)" % self.offset2LC(current_offset + offset))
		elif whence == 2:
			line		= int(vim.eval("line('$')"))
			column		= int(vim.eval("col('$')"))
			vim.eval("cursor(%d,%d)" % self.offset2LC(len(self) - offset))
		else:
			raise TypeError("Second argument seek() method must be 0, 1 or 2")

	def truncate(self, size=None):
		"""
		Return:		None

		Truncate the buffer to at most size bytes
		"""
		if size == None:
			size = self.tell()
		del(self[size:])

	def read(self, size=-1):
		"""
		Return:		string

		Read at most size bytes from the file
		If SIZE is negative, then reads all till
		the end of a file
		"""
		pos = self.tell()
		
		if size >= 0:
			self.seek(size, 1)
			return str(self.encode(self.encoding)[pos:pos + size])
		else:
			self.seek(0,2)
			return str(self.encode(self.encoding)[pos:])

	def readline(self, size=-1):
		"""
		Return:		string

		Read one entire string from the file
		Newline char is kept in string
		"""
		pos		= self.tell()
		text		= self.encode(self.encoding)
		newlines	= self.newlines.encode(self.encoding)
		try:
			result	= text[pos: text.index(newlines, pos)] + newlines
		except ValueError:
			result	= text[pos:]
		if size >= 0:
			self.seek(pos + size, 0)
			return result[:size].decode(self.encoding)
		else:
			self.seek(pos + len(result))
			return result.decode(self.encoding)

	def readlines(self, sizehint=0):
		"""
		Return:		list

		Read untill the end of buffer, using readline()
		"""
		total	= 0
		lines	= []
		line	= self.readline()

		while line:
			lines.append(line)

			if int(vim.eval("line('.')")) == int(vim.eval("line('$')")):
				lines.append(self.readline())
				break
			total += len(line)
			if 0 < sizehint <= total:
				break
			line = self.readline()
		return lines

	def write(self, string):
		"""
		Return:		None

		Write a string to the buffer under cursor
		"""
		if not isinstance(string, str):
			string = string.decode(self.encoding)
		
		string = re.sub(r"\r\n?|\n", self.newlines, string)
		pos		= self.tell()
		self[pos:pos]	= string
		self.seek(pos + len(string))

	def writelines(self, array):
		"""
		Return:		None

		Write a sequence of string to the file
		"""
		self.write(self.newlines.join(array))

	#----interactive methods----

	def dialog_enabled(self):
		"""
		Return:		bool

		Checks if dialog option is enabled in vim
		"""
		result	= bool(int(vim.eval("has('dialog_con')")) or\
				int(vim.eval("has('dialog_gui')")))
		return result

	def interactive(self, start=None, end=None, *confirm, **options):
		"""
		interactive([start [, end [, msg [, choices [, default [, type]]]]]]
				[, highlight=group] [, vpos = "bot" (or "top")]
				[, gap = "gap"])

		Return:		int

		Go to START position, highlight from START to END by
		GROUP (default == 'IncSearch'), and run vim's confirmation
		dialog

		MSG, CHOICES, DEFAULT, TYPE pass into vim's confirm() func

		See ':help confirm()' for extra details
		"""
		if not self.dialog_enabled():
			raise Exception("")

		if start == None:
			start	= self.tell()
		if end == None:
			end	= self.tell()

		if not confirm:
			confirm = ("request", )
		if not "highlight" in options.keys():
			options["highlight"]	= "IncSearch"
		if not "vpos" in options.keys():
			options["vpos"]		= "bot"
		if not "gap" in options.keys():
			options["gap"]		= 3

		# compute position
		start_l, start_c	= self.offset2LC(start)
		end_l, end_c		= self.offset2LC(end)

		# redraw
		if options["vpos"]	== "top":
			vim.command("normal! %izt" % (max(start_l - options["gap"], 1)))
		elif options["vpos"]	== "bot":
			vim.command("normal! %izb" % (min(end_l + options["gap"],
				int(vim.eval("line('$')")))))
		vim.command("match %s /\\%%%il\\%%%ic\\_.*\\%%%il\\%%%ic/" % (
				options["highlight"], start_l, start_c, end_l, end_c))
		vim.command("redraw")

		# confirmation
		def advanced_str(obj):
			if isinstance(obj, str):
				if "c" in vim.eval("&guioptions"):
					dialog_encoding = self.encoding
				else:
					dialog_encoding = locale.getdefaultlocale()[1]
				return obj
			else:
				return str(obj)
		confirm	= map(advanced_str, confirm)
		result	= vim.eval("confirm(%s)" % ("'"+"', '".join(confirm)+"'"))
		vim.command("match None /\\%%%il\\%%%ic\\_.*\\%%%il\\%%%ic/" %
				(start_l, start_c, end_l, end_c))
		return int(result)
