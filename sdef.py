byte_code_table = {	'STR_CONST': '\x43\x30',
					'NUM_CONST': '\x43\x31',
					'MATH_EXPR': '\x43\x32',
					'VAR': '\x56\x30',
					'IND_VAR': '\x56\x31',
					'COMP_EQ': '\x3d\x30',
					'COMP_GT': '\x3d\x31',
					'COMP_LT': '\x3d\x32',
					'COND_JUMP': '\x4a\x30',
					'RAND_DIR': '\x4a\x31',
					'GOTO': '\x4a\x32',
					'INPUT': '\xc2\xbf',
					'PRINT': '\xc2\xa1',
					'SET': '\x58\x30',
					'SWAP': '\x58\x31',
					'CAT': '\x58\x32',
					'SUBSTR': '\x58\x33',
					'END_PROGRAM': '\x40\x20',

					'OPEN_FILE': '\x4f\x46',
					'USE_LIB': '\x2b\x20',
				}

instruction_table = dict((v,k) for k,v in byte_code_table.items())