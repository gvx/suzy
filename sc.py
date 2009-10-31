#!/usr/bin/env python
#suzy compiler
#compiles suzy code to byte-code

import sys, optparse, string
from sdef import byte_code_table

class CompileError(Exception):
	pass

usage = "usage: %prog [options] [fromfile [tofile]]"
parser = optparse.OptionParser(usage)
parser.add_option("-m", "--metadata", metavar="DATA", default='', help='Add metadata to byte-code file')
parser.add_option("-d", "--debug", action='store_true', default=False, help='Show debugging information')
options, args = parser.parse_args()

#Phase 0: opening infile and outfile + reading the infile
if len(args) > 0:
	infile = open(args[0])
else:
	infile = sys.stdin
if len(args) > 1:
	outfile = open(args[1],'w')
else:
	outfile = sys.stdout

horlen, verlen, latlen = [int(t.strip()) for t in infile.readline().split(',')]
program_text = infile.read()

if options.debug:
	print 'Horlen: %s, Verlen: %s, Latlen: %s' % (horlen, verlen, latlen)

#Phase 1: parsing the suzy source into a list of lists (easier to deal with than a big string)
parsed = [[]]
ver = 0
lat = 0
for line in program_text.split('\n'):
	if ver >= verlen:
		ver = 0
		lat += 1
		parsed.append([])
	if line == '&':
		parsed[lat].extend([[' ']*horlen]*(verlen-1))
		ver = 0
		lat += 1
		parsed.append([])
		continue
	parsed[lat].append([char for char in line+' '*(horlen-len(line))])
	ver += 1

#Phase 2: walking down the source tree
horlen, verlen, latlen = horlen+1, verlen+1, latlen+1
start_pos = (0,0,0,1,0,0)
process_stack = [start_pos]
completed = []
passed = {}
byte_code = {}
LABEL_COUNTER = 0
dircodes = {'{': (-1, 0, 0), '}': (1, 0, 0),
			'^': (0, -1, 0), '_': (0, 1, 0),
			'[': (0, 0, -1), ']': (0, 0, 1),
			}
#print parsed[0]

def process_branch(pos):
	global LABEL_COUNTER
	if str(pos) in completed:
		if options.debug:
			print 'tried to reprocess branch', pos
		return
	x, y, z, dx, dy, dz = pos
	state = None
	byte_code[pos] = []
	expr = []
	meta_state = None
	math_depth = 0
	args_left = 0
	def flushadd(bc_str, state, args_left):
		if expr:
			byte_code[pos].append(''.join(expr))
			del expr[:]
			args_left -= 1
			if args_left:
				state = 'args'
			else:
				state = None
		if bc_str:
			byte_code[pos].append(bc_str)
		return state, args_left
	if options.debug:
		print 'new branch', pos
	while True:
		if 0 <= z < latlen and 0 <= y < verlen and 0 <= x < horlen:
			c = parsed[z][y][x]
			if options.debug:
				sys.stdout.write(c)
			if not args_left and state == 'args':
				state = None
			if state=='str':
				if c == '`':
					state=='escaped_str'
				#elif c == '\\':
				#	state=
				elif c == '"':
					byte_code[pos].append(''.join(expr))
					expr = []
					state = meta_state
					if state=='args':
						args_left -= 1
				else:
					expr += c
			elif state=='escaped_str':
				if c not in dircodes:
					raise CompileError('A temporary string escape should be followed by a constant direction.')
				else:
					dx, dy, dz = dircodes[c]
					state='str'
			elif c == '"':
				meta_state = state
				state='str'
				state, args_left = flushadd('STR_CONST', state, args_left)
			elif c in " |'" or (c == '-' and state != 'math'):
				pass
			elif c == '@':
				state, args_left = flushadd('END_PROGRAM', state, args_left)
				return
			elif c in dircodes:
				if options.debug:
					sys.stdout.write("\x17")
				dx, dy, dz = dircodes[c]
				loc = str((x,y,z,dx,dy,dz))
				if loc in passed:
					state, args_left = flushadd('GOTO', state, args_left)
					byte_code[pos].append(passed[loc])
					return
				else:
					state, args_left = flushadd('LABEL', state, args_left)
					LABEL_COUNTER += 1
					byte_code[pos].append(LABEL_COUNTER)
					passed[loc] = LABEL_COUNTER
			elif c == '#':
				x, y, z = (x+dx)%horlen, (y+dy)%verlen, (z+dz)%latlen
			elif c == '$':
				state, args_left = flushadd('COND_JUMP', state, args_left)
				pos1 = ((x+dx)%horlen, (y+dy)%verlen, (z+dz)%latlen, dx, dy, dz)
				pos2 = ((x+dx*2)%horlen, (y+dy*2)%verlen, (z+dz*2)%latlen, dx, dy, dz)
				process_stack.append(pos1)
				process_stack.append(pos2)
				LABEL_COUNTER += 1
				byte_code[pos].append(LABEL_COUNTER)
				passed[str(pos1)] = LABEL_COUNTER
				LABEL_COUNTER += 1
				byte_code[pos].append(LABEL_COUNTER)
				passed[str(pos2)] = LABEL_COUNTER
				#byte_code[str(pos)].append(str(pos1))
				#byte_code[str(pos)].append(str(pos2))
				return
			elif c == '%':
				state, args_left = flushadd('RAND_DIR', state, args_left)
				poss = [((x+ddx)%horlen, (y+ddy)%verlen, (z+ddz)%latlen, ddx, ddy, ddz)
						for ddx, ddy, ddz in dircodes.values()
						if ddx != dx or ddy != dy or ddz != dz]
				process_stack.extend(poss)
				for posx in poss:
					LABEL_COUNTER += 1
					byte_code[pos].append(LABEL_COUNTER)
					passed[str(posx)] = LABEL_COUNTER
				#byte_code[pos].append(str(poss))
				return
			elif c == ';':
				state, args_left = flushadd(None, state, args_left)
			elif c == '/':
				state, args_left = flushadd('OPEN_FILE', state, args_left)
				state='args'
				args_left = 1
			elif c == '+':
				state, args_left = flushadd('USE_LIB', state, args_left)
				state='args'
				args_left = 1
			elif c == '=':
				state, args_left = flushadd('COMP_EQ', state, args_left)
				state='args'
				args_left = 2
			elif c == '<':
				state, args_left = flushadd('COMP_LT', state, args_left)
				state='args'
				args_left = 2
			elif c == '>':
				state, args_left = flushadd('COMP_GT', state, args_left)
				state='args'
				args_left = 2
			elif c == '!':
				state, args_left = flushadd('PRINT', state, args_left)
				state='args'
				args_left = 1
			elif c == '.':
				state, args_left = flushadd('CAT', state, args_left)
				state='args'
				args_left = 2
			elif c == ',':
				state, args_left = flushadd('SUBSTR', state, args_left)
				state='args'
				args_left = 3
			elif c == '~':
				state, args_left = flushadd('SWAP', state, args_left)
				state='args'
				args_left = 2
			elif c == ':':
				state, args_left = flushadd('SET', state, args_left)
				state='args'
				args_left = 2
			elif c == '?':
				state, args_left = flushadd('INPUT', state, args_left)
				state='args'
				args_left = 2
			elif state=='math':
				if math_depth == 0 and c == ')':
					state, args_left = flushadd(None, state, args_left)
					state=meta_state
				else:
					if c == ')':
						math_depth -= 1
					if c == '(':
						math_depth += 1
					expr.append(c)
			elif c == '(':
				meta_state=state
				state, args_left = flushadd('MATH_EXPR', state, args_left)
				state='math'
				math_depth = 0
			elif c in string.letters:
				state, args_left = flushadd('VAR', state, args_left)
				byte_code[pos].append(c)
				args_left -= 1
			elif c in string.digits:
				if not byte_code[pos] or byte_code[pos][-1] != 'NUM_CONST':
					state, args_left = flushadd('NUM_CONST', state, args_left)
				expr.append(c)
			elif c == '\\':
				state, args_left = flushadd('IND_VAR', state, args_left)
			args_left += 1
		else:
			print('alert!')
		x, y, z = (x+dx)%horlen, (y+dy)%verlen, (z+dz)%latlen
		if str((x,y,z,dx,dy,dz)) in passed:
			if options.debug:
				print('!!!')
			state, args_left = flushadd('GOTO', state, args_left)
			byte_code[pos].append(passed[str((x,y,z,dx,dy,dz))])
			return

while process_stack:
	pos = process_stack.pop(0)
	process_branch(pos)
	completed.append(str(pos))

#Phase 3: iterating over the generated byte-code for finding labels
Labels = {}
Branches = {}
offset = 0
def iterate_branch1(branch):
	global offset
	lpos = 0
	while lpos < len(branch):
		if branch[lpos] == 'LABEL':
			branch.pop(lpos)
			Labels[branch[lpos]] = lpos+offset
			branch.pop(lpos)
		else:
			lpos += 1
	offset += len(branch)
Branches[str(start_pos)] = offset
iterate_branch1(byte_code[start_pos])
for pos in byte_code:
	if pos != start_pos:
		Branches[str(pos)] = offset
		iterate_branch1(byte_code[pos])

#Phase 4: flatten branches
byte_code_final = []
Lbls = dict((v, Branches.get(k, 0)) for k,v in passed.items())

def iterate_branch2(branch):
	labelsleft = 0
	for item in branch:
		if item == 'GOTO':
			labelsleft = 1
		elif item == 'COND_JUMP':
			labelsleft = 2
		elif item == 'RAND_DIR':
			labelsleft = 4
		elif labelsleft:
			if item in Labels:
				item = Labels[item]
			else:
				item = Lbls[item]
			labelsleft -= 1
		byte_code_final.append(item)
iterate_branch2(byte_code[start_pos])
for pos in byte_code:
	if pos != start_pos:
		iterate_branch2(byte_code[pos])

#Phase 5: converting byte-code strings to actual byte-code
header = 'SUZY'
if options.metadata:
	header += '%metadata:' + options.metadata
outputted_byte_code = [header]

for line in byte_code_final:
	if line in byte_code_table:
		outputted_byte_code.append(byte_code_table[line])
	else:
		outputted_byte_code.append(str(line))

outfile.write('\n'.join(outputted_byte_code))

###############
infile.close()
outfile.close()