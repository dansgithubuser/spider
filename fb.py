import argparse
parser=argparse.ArgumentParser(description='tools for working with downloaded copies of Facebook data')
parser.add_argument('path', help='path to root of facebook data download (unzipped)')
parser.add_argument('--word-frequency', '--wf', action='store_true', help='count word frequency in messages')
parser.add_argument('--word-frequency-user', '--wfu', help='user to get word frequency for, default all users')
parser.add_argument('--messages-from-user', '--mfu', help='print message from user')
parser.add_argument('--messsage-from-user-start', '--mfus', help='index of first message to print')
parser.add_argument('--messages-from-user-finish', '--mfuf', help='index of last message to print')
args=parser.parse_args()

from html.parser import HTMLParser
class MessageParser(HTMLParser):
	def __init__(self, desired_user):
		HTMLParser.__init__(self)
		self.desired_user=desired_user
		self.stack=[]
		self.user=None
		self.meta=None

	def handle_starttag(self, tag, attrs):
		self.stack.append((tag, attrs))

	def handle_endtag(self, tag):
		assert tag==self.stack[-1][0]
		self.stack=self.stack[:-1]

	def handle_data(self, data):
		if   self.stack[-1]==('span', [('class', 'user')]):
			self.user=data
		elif self.stack[-1]==('span', [('class', 'meta')]):
			self.meta=data
		elif (self.desired_user and self.user==self.desired_user) or ((not self.desired_user) and self.user):
			self.handle_message(data)

	def go(self):
		import os
		with open(os.path.join(args.path, 'html', 'messages.htm')) as file: self.feed(file.read())

if args.word_frequency:
	import re
	class WordCountParser(MessageParser):
		def __init__(self, *args, **kwargs):
			MessageParser.__init__(self, *args, **kwargs)
			from collections import defaultdict
			self.wordcount=defaultdict(int)

		def handle_message(self, message):
			for word in message.split():
				self.wordcount[re.sub(r'[^a-z\-\']', '', word.lower())]+=1

	parser=WordCountParser(args.word_frequency_user)
	parser.go()
	wordcount=list(parser.wordcount.items())
	wordcount.sort(key=lambda x: x[1])
	with open('wc.txt', 'w') as file:
		for word, count in wordcount: file.write(word+' '+str(count)+'\n')

if args.messages_from_user:
	class Parser(MessageParser):
		def handle_message(self, message):
			print(message)

	parser=Parser(args.messages_from_user)
	parser.go()

print('all requests processed; call with -h for help')
