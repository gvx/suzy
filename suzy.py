#!/usr/bin/env python
#suzy interpreter

import sys, optparse, os.path, math
from subprocess import Popen
from sdef import instruction_table

usage = "usage: %prog [options] file"
parser = optparse.OptionParser(usage)
parser.add_option("-n", "--noscfile", action="store_true", default=False, help='do not create a .sc compiled Suzy file')
parser.add_option("-d", "--debug", action="store_true", default=False, help='print every action--debugging only')
options, args = parser.parse_args()

if not args:
	print "Please supply a Suzy script."
	exit()

suzyfile = open(args[0])
firstline = suzyfile.readline()
if firstline.startswith('#!'):
	firstline = suzyfile.readline()
if not firstline.startswith('SUZY'):
	suzyfile.close()
	p = os.path.dirname(sys.argv[0])
	if not p.endswith('/'): p+='/'
	command = ["python", p+"sc.py", "-mAuto-generated for Suzy interpreter 0.0", args[0]]
	if options.noscfile:
		script = Popen(command, stdout=PIPE).communicate()[0]
	else:
		Popen(command+[os.path.splitext(args[0])[0]+'.sc']).communicate()[0]
		suzyfile = open(os.path.splitext(args[0])[0]+'.sc')
		suzyfile.readline()
		script = suzyfile.read()
		suzyfile.close()
else:
	script = suzyfile.read()
	suzyfile.close()

#Interpreting Functions
def vartype(name):
	if isinstance(name, int) or name[0].islower():
		return int
	else:
		return str

def newvar(name):
	return vartype(name)()

def resolve(K):
	Type, Content = K
	if Type == 'c':
		return Content
	elif Type == 'v':
		return mem.get(Content, newvar(Content))
	elif Type == 'iv':
		Content = mem.get(Content[1:], newvar(Content[1:]))
		return mem.get(Content, newvar(Content))

def resolvevar(K):
	Type, Content = K
	if Type == 'v':
		return Content
	elif Type == 'iv':
		return mem.get(Content, newvar(Content))

def put(name, value):
	if vartype(name)==str:
		mem[name] = str(value)
	else:
		try:
			mem[name] = int(value)
		except:
			mem[name] = 0

class Filexs:
	def __init__(self):
		self.file = None
		self.curfile = ''
	def read(self):
		if self.file:
			return self.file.read()
		else:
			return sys.stdin.readline().rstrip()
	def write(self, t):
		if self.file:
			self.file.write(t)
		else:
			sys.stdout.write(t)
	def close(self):
		if self.file:
			self.file.close()
filexs = Filexs()

single_escapes = {'\\': '\\', 'n': '\n', 't': '\t', 'b': '\b'}
def unesc(escaped_text):
	unescaped_text = []
	STATE = 0
	mdat = []
	for c in escaped_text:
		if STATE == 0:
			if c == '\\':
				STATE = 1
			else:
				unescaped_text.append(c)
		elif STATE == 1:
			if c in single_escapes:
				unescaped_text.append(single_escapes[c])
				STATE = 0
			elif c == 'a':
				STATE = 2
			elif c == 'u':
				STATE = 4
		else:
			mdat.append(c)
			if len(mdat)==STATE:
				unescaped_text.append(STATE==4 and unichr or chr)(int(''.join(mdat),16))
				del mdat[:]
	return ''.join(unescaped_text)

def matheval(expr):
	tempres = 0
	do_sqrt = False
	fields = []
	tmpx = ''
	indirect = False
	if options.debug:
		print(expr)
	for char in expr:
		if char in '*/%+-':
			if tmpx:
				fields.append((indirect and 'iv' or 'c',tmpx))
				tmpx = ''
			indirect = False
			fields.append(('o',char))
		elif char.isalpha() and not indirect:
			if tmpx:
				fields.append((indirect and 'iv' or 'c',tmpx))
				tmpx = ''
			elif fields and fields[-1][0] == 'v':
				#implicit multiplication
				fields.append(('o','*'))
			indirect = False
			fields.append(('v', char))
		elif char == '\\':
			indirect = True
			tmpx += char
		else:
			tmpx += char
	if tmpx:
		fields.append((indirect and 'iv' or 'c',tmpx))
	if fields[0][1] == '-':
		fields.pop(0)
		fields[0] = ('c',-int(resolve(fields[0])))
	elif fields[0][1] == '+':
		fields.pop(0)
		fields[0] = ('c',abs(int(resolve(fields[0]))))
	elif fields[0][1] == '*':
		fields.pop(0)
	elif fields[0][1] == '/':
		fields.pop(0)
		do_sqrt = True
	if fields[-1][1] == '-':
		fields.pop()
		fields[-1] = ('c',int(resolve(fields[0]))-1)
	elif fields[-1][1] == '+':
		fields.pop()
		fields[-1] = ('c',int(resolve(fields[0]))+1)
	elif fields[-1][1] == '*':
		fields.pop()
		fields[-1] = ('c',int(resolve(fields[0]))**2)
	elif fields[0][1] == '/':
		fields.pop()
	#evaluate fields *here*
	i = 1
	while i < len(fields):
		#if fields[i][0] == 'o':
		if fields[i][1] in '*/%':
			two = fields.pop(i+1)
			op = fields.pop(i)
			one = fields.pop(i-1)
			if op[1] == '*':
				fields.insert(i-1, ('c', int(resolve(one))*int(resolve(two))))
			elif op[1] == '%':
				try:
					a = int(resolve(one))%int(resolve(two))
				except ZeroDivisionError:
					a = 0
				fields.insert(i-1, ('c', a))
			else:
				try:
					a = float(resolve(one))/int(resolve(two))
					if a > 0:
						a = int(a)
					else:
						a = int(math.ceil(a))
				except ZeroDivisionError:
					a = 0
				fields.insert(i-1, ('c', a))
		else:
			i += 2
	i = 1
	while i < len(fields):
		if fields[i][0] == 'o':
			if fields[i][1] in '+-':
				two = fields.pop(i+1)
				op = fields.pop(i)
				one = fields.pop(i-1)
				if op[1] == '+':
					fields.insert(i-1, ('c', int(resolve(one))+int(resolve(two))))
				else:
					fields.insert(i-1, ('c', int(resolve(one))-int(resolve(two))))
			else:
				i += 2
	tempres = resolve(fields[0])#should be one
	if do_sqrt: tempres = int(tempres**.5)
	return ('c', tempres)

mem = {}
loadedlibs = {}

if options.debug:
	mem["debug_lib_level"] = 0

#Main Interpreter Loop
def interpret(lines, ismain=False):
	i = 0
	ins_args_left = 0
	ins_args = []
	comp = None
	action = None

	while i < len(lines):
		ins = instruction_table[lines[i]]
		if options.debug:
			sp = '->'*mem["debug_lib_level"]
			print sp+'INSTRUCTION:',ins
			print sp+'MEMORY:',mem
		if ins == 'STR_CONST':
			i += 1
			ins_args.append(('c', unesc(lines[i])))
			if options.debug:
				print sp+'META-INSTRUCTION:',lines[i]
			ins_args_left -= 1
		elif ins == 'NUM_CONST':
			i += 1
			ins_args.append(('c', int(lines[i])))
			if options.debug:
				print sp+'META-INSTRUCTION:',lines[i]
			ins_args_left -= 1
		elif ins == 'MATH_EXPR':
			#evaluate math
			i += 1
			returnvalue = matheval(lines[i])
			if options.debug:
				print sp+'META-INSTRUCTION:',lines[i]
			ins_args.append(returnvalue)
			ins_args_left -= 1
		elif ins == 'VAR':
			i += 1
			ins_args.append(('v', lines[i]))
			if options.debug:
				print sp+'META-INSTRUCTION:',lines[i]
			ins_args_left -= 1
		elif ins == 'IND_VAR':
			ins_args.append('iv')
		elif ins in ('COMP_EQ', 'COMP_GT', 'COMP_LT', 'SET', 'SWAP', 'CAT'):
			action = ins
			ins_args_left = 2
		elif ins == 'COND_JUMP':
			i = int(lines[i + (comp and 1 or 2)])-1
		elif ins == 'RAND_DIR':
			i = int(lines[i + random.randint(1,4)])-1
		elif ins == 'GOTO':
			i = int(lines[i + 1])-1
		elif ins in ('INPUT', 'PRINT', 'OPEN_FILE', 'USE_LIB'):
			action = ins
			ins_args_left = 1
		elif ins == 'SUBSTR':
			action = ins
			ins_args_left = 4
		elif ins == 'END_PROGRAM':
			if ismain:
				print '' #flush line
			break
		if action and not ins_args_left:
			ins_args_i = len(ins_args) - 1
			while ins_args_i >= 0:
				if ins_args[ins_args_i] == 'iv':
					ins_args[ins_args_i] = ('v', resolve(ins_args.pop(ins_args_i+1)))
				ins_args_i -= 1
			if action=='COMP_EQ':
				comp = resolve(ins_args[0]) == resolve(ins_args[1])
			elif action=='COMP_GT':
				comp = resolve(ins_args[0]) > resolve(ins_args[1])
			elif action=='COMP_LT':
				comp = resolve(ins_args[0]) < resolve(ins_args[1])
			elif action=='INPUT':
				mem[resolvevar(ins_args[0])] = filexs.read()
			elif action=='PRINT':
				filexs.write(str(resolve(ins_args[0])))
			elif action=='OPEN_FILE':
				filexs.close()
				filexs.curfile = str(resolve(ins_args[0]))
				if filexs.curfile and filexs.curfile != '0':
					try:
						if not os.path.exists(filexs.curfile):
							filexs.file = open(filexs.curfile, 'w+')
						else:
							filexs.file = open(filexs.curfile, 'r+')
					except:
						print "suzy: could not open file"
						if options.debug:
							print "Tried to open file", filexs.curfile, "but it failed"
						break
				else:
					filexs.file = None
			elif action=='USE_LIB':
				try:
					fname = str(resolve(ins_args[0]))
					if fname in loadedlibs:
						libscript = loadedlibs[fname]
					else:
						libfile = open(fname+'.sc')
						libfile.readline()
						libscript = libfile.read().split('\n')
						libfile.close()
						loadedlibs[fname] = libscript
					if options.debug:
						mem["debug_lib_level"] += 1
					interpret(libscript)
					if options.debug:
						mem["debug_lib_level"] -= 1
				except IOError:
					print "suzy: could not load library", fname
					break
			elif action=='SET':
				put(resolvevar(ins_args[0]), resolve(ins_args[1]))
			elif action=='SWAP':
				tmp = resolve(ins_args[0])
				put(resolvevar(ins_args[0]), resolve(ins_args[1]))
				put(resolvevar(ins_args[1]), tmp)
			elif action=='CAT':
				if ins_args[0][0] == 'c' or not isinstance(resolve(ins_args[0]), str):
					raise TypeError("Can't concatenate to anything other than a string variable")
				if isinstance(resolve(ins_args[1]), int):
					r = unichr(r)
				else:
					r = resolve(ins_args[1])
				mem[resolvevar(ins_args[0])] += r
			elif action=='SUBSTR':
				if ins_args[0][0] == 'c' or not isinstance(resolve(ins_args[0]), str):
					raise TypeError("Can't put a substring in anything other than a string variable")
				put(resolvevar(ins_args[0]), resolve(ins_args[1])[resolve(ins_args[2]):resolve(ins_args[3])])
			action = None
			del ins_args[:]
		i += 1

try:
	interpret(script.split('\n'), True)
except Exception, e:
	print "suzy: fatal unhandled error:", e
filexs.close()
