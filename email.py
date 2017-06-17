import collections, glob, pprint

try: input=raw_input
except: pass

import argparse
parser=argparse.ArgumentParser(
	description=(
		'Process a series of emails exported '
		'as plain text by ImportExportTools addon for Thunderbird '
		'or as mbox format by gmail takeout. '
	)
)
parser.add_argument('glob', nargs='+', help='glob of email files')
parser.add_argument('--start', help='regex of start of interesting section')
parser.add_argument('--end', help='regex of end of interesting section')
parser.add_argument('--split', help='what to split lines with', default=' ')
parser.add_argument('--output', default='out.txt')
parser.add_argument('--keygen', action='store_true', help='prompt when unkeyed item is encountered')
parser.add_argument('--key', default='key.txt', help='file associated with keygen')
parser.add_argument('--ignore', default='ignore.txt', help='file containing terms to ignore')
args=parser.parse_args()

print('globs: '+str(args.glob))
if args.start: print('start: ('+args.start+')')
if args.end: print('end: ('+args.end+')')
print('split: ('+args.split+')')

key=collections.defaultdict(list)
if args.key:
	try:
		with open(args.key) as file: key.update(eval(file.read()))
	except: pass
ignore=[]
if args.ignore:
	try:
		with open(args.ignore) as file: ignore=eval(file.read())
	except: pass

total=0
for g in args.glob: total+=len(glob.glob(g))

def write_key():
	with open(args.key, 'w') as file: file.write(pprint.pformat(dict(key)))
	with open(args.ignore, 'w') as file: file.write(pprint.pformat(ignore))

history=collections.defaultdict(dict)
i=0
for g in args.glob:
	for filename in glob.glob(g):
		i+=1
		print('{}/{} {}'.format(i, total, filename))
		with open(filename) as file: lines=file.readlines()
		class State:
			def __init__(self): self.reset()
			def reset(self):
				self.date=None
				self.interested=False
				self.bad_encoding=False
				self.items=collections.defaultdict(lambda: collections.defaultdict(list))
		state=State()
		if not args.start: state.interested=True
		import re
		for i_line, line in enumerate(lines):
			#print('line {}: {}'.format('x' if state.interested else ' ', line.strip()))
			#date
			df='{}-{:0>2}-{:0>2}'
			def month_n(abbr):
				import calendar
				return list(calendar.month_abbr).index(abbr.capitalize())
			no_date=state.date==None
			m=re.match('Date: ([0-9]+)/([0-9]+)/([0-9:]+)', line)
			if m: state.date=df.format(m.group(3), m.group(1), m.group(2))
			m=re.match('Date: .*, ([0-9]+) ([A-Za-z]+) ([0-9:]+)', line)
			if m: state.date=df.format(m.group(3), month_n(m.group(2)), m.group(1))
			m=re.match('date: ([0-9]+) ([a-z]+) ([0-9]+)', line)
			if m: state.date=df.format(m.group(1), month_n(m.group(2)), m.group(3))
			m=re.match('Subject: .* ([0-9]+) ([a-z]+) ([0-9]+)', line)
			if m: state.date=df.format(m.group(1), month_n(m.group(2)), m.group(3))
			if no_date and state.date:
				print('date: {} line: {}/{}'.format(state.date, i_line+1, len(lines)))
			#encoding
			m=re.match('Content-Type: ([^;]*);', line)
			if m: state.bad_encoding=m.group(1)!='text/plain'
			if state.bad_encoding: continue
			#interest
			if not state.interested:
				if re.search(args.start, line):
					state.interested=True
			else:
				if args.end and re.search(args.end, line):
					if state.date==None:
						print('no date!')
						pprint.pprint(state.items)
					else:
						history[state.date].update(state.items)
					state.reset()
					continue
				for item in line.split(args.split):
					item=item.lower().strip()
					if not item: continue
					keywords=[]
					#key
					for keyword, regexes in key.items():
						for regex in regexes:
							if re.search(regex, item):
								keywords.append(keyword)
								break
					#keygen
					if not keywords and args.keygen:
						should_ignore=False
						for regex in ignore:
							if re.search(regex, item):
								should_ignore=True
								break
						if not should_ignore:
							print('unkeyed item encountered: {}'.format(item.encode()))
							print('context')
							for context_line in lines[:i_line+1][-4:]: print(context_line.rstrip())
							#regex
							while True:
								print('regex? ')
								regex=input()
								if not regex: regex=re.sub(r'(\?|\.|\+|\(|\))', r'\\\1', item)
								try:
									if re.search(regex, item): break
									else: print('regex does not match')
								except Exception as e: print(e)
							#new key
							print('keyword? ')
							keyword=input()
							if keyword:
								key[keyword].append(regex)
								keywords.append(keyword)
							else:
								ignore.append(regex)
							write_key()
					#update items
					if not keywords: keywords.append(None)
					for keyword in keywords: state.items[keyword][item].append(line.strip())
write_key()
with open(args.output, 'w') as file: file.write(pprint.pformat(history))
heatFilename='heat.'+args.output
with open(heatFilename, 'w') as file:
	file.write('begin\n')
	index=[]
	for date, items in sorted(history.items(), key=lambda x: x[0]):
		for item, lines in sorted(items.items(), key=lambda x: x[0] if x[0] else ''):
			if item not in index: index.append(item)
	index=dict([(index[i], i) for i in range(len(index))])
	for item, i in index.items():
		import synesthesia
		r, g, b, a=synesthesia.color(str(item))
		file.write('ycolor {} {} {} {} 255\n'.format(i, r, g, b))
	def to_days(date):
		from datetime import datetime
		return (datetime.strptime(date, '%Y-%m-%d')-datetime.utcfromtimestamp(0)).days
	for date, items in history.items():
		for item, lines in items.items():
			file.write('hover {} {} {}\n'.format(to_days(date), index[item], '{} {}\n{}\n'.format(item, date, '\n'.join(lines))))
	file.write('end\n')
	for date, items in history.items():
		for item, lines in items.items():
			file.write('{} {}\n'.format(to_days(date), index[item]))
import os, subprocess
plotstuff=os.environ.get('PLOTSTUFF', '../plotstuff/go.py')
subprocess.call('python {} --type heat {}'.format(plotstuff, heatFilename), shell=True)
