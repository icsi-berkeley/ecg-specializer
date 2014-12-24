""" 

@author: Sean Trott

These are unit tests for the Analyzer and grammars. In this first run, the only intention
is to see whether or not a sentence parses. It's possible that later we can add a more
qualitative way of testing, but for now it will be the command line equivalent of the
"Sentence Test Runner" in the Workbench. 

Note: Sentences should be tagged in some way so it knows whether to test that they do or don't parse. Maybe 
assume they should be parsed, unless tagged with an asertisk or some other clue. 

Note: Should also be able to specify which grammar you want to pull sentences from and test. E.g., don't
run "primero" sentences for "first", and so on.

* This code is very much in progress - will have to put things in functions, etc., but the main thing is that
you don't have to run the Analyzer in a separate window now. Ultimately it should just iterate through the grammars
and test them all.

"""



import os
from subprocess import * #call, check_output
os.environ['JYTHONPATH'] = 'lib/compling.core.jar:src/main'
import unittest
from specializer import *
import time
from signal import *

try:
    # Python 2?
    from xmlrpclib import ServerProxy, Fault  # @UnresolvedImport @UnusedImport
except:
    # Therefore it must be Python 3.
    from xmlrpc.client import ServerProxy, Fault 

class Analyzer(object):
    """A proxy for the Analyzer. 
    Note: It assumes the server is running with the right grammar
    """
    def __init__(self, url):
        self.analyzer = ServerProxy(url, encoding='utf-8') 
        
    def parse(self, sentence):        
        return [as_featurestruct(r, s) for r, s in self.analyzer.parse(sentence)]
    
    def issubtype(self, typesystem, child, parent):
        return self.analyzer.issubtype(typesystem, child, parent)

    def reload(self, prefs):
    	self.analyzer.reload(prefs)

    def close(self):
    	self.analyzer.close()











def read_examples(filename):
	""" Reads examples from file. outputs to list"""
	f = open(filename, 'r')
	examples = []
	mark = False
	for line in f:
		if ";" in line:
			mark = False
		elif mark and len(str(line).strip()) > 0:
			examples.append(str(line).strip().replace("\n", ""))
		elif 'EXAMPLE_SENTENCES ::==' in line:
			mark = True
	return examples


""" These paths should be modified, once there's a good location for the grammars (not machine-dependent.) """
suites = {'first': 'first.prefs',
		  'robots': 'robots.prefs',
		  'primero': 'primero.prefs',
		  'spanish-metaphor': 'spanish-metaphor.prefs',
		  'spanish-robots': 'spanish-robots.prefs'}

""" If "while" loop is commented out, jython analyzer must be running in separate Terminal tab. Any grammar will do,
since it reloads the grammar in the 'for' loop. If not, there should be no other processes running on the local server.

"""
prefix = '/Users/seantrott/Dropbox/ECG/'
if __name__ == "__main__":

	total_errors = 0
	analyzer = Analyzer("http://localhost:8090")
	#server = Popen(['jython', '-m', 'analyzer', suites['first']])
	"""
	while True:
		try:
			analyzer = Analyzer("http://localhost:8090")
			analyzer.parse("the red block")
			print("successfully connected")
			break
		except Exception:
			pass
	"""
	to_test = suites.keys()

	if len(sys.argv) > 1:   # Fix this conditional block later to allow for more flexibility in input statements. Right now, you can't input "robots" without also inputting file-path.
		prefix = sys.argv[1]
		if len(sys.argv) > 2:
			to_test = sys.argv[2:]
	
	gen = (key for key in suites.keys() if key in to_test)
	#for name, grammar in suites.items():
	for name in gen:
		print("")
		print("TESTING: " + name)
		grammar = prefix + suites[name]
		examples = read_examples(grammar)

		analyzer.reload(grammar)
		#os.popen(arg)
		#server = Popen(['jython', '-m', 'analyzer', grammar], shell=False)

		#analyzer = Analyzer("http://localhost:8090")
		#os.popen('jython -m analyzer2 /Users/seantrott/Dropbox/ECG/robots.prefs')


		errors = []
		for sentence in examples:
			try:
				analyzer.parse(sentence)
				print("success: " + sentence)
			except Fault as err:
				print(err.faultString)
				print("failure: " + sentence)
				errors.append(sentence)
		print("Total errors in " + str(name) + ": " + str(len(errors)))
		total_errors += len(errors)
		if len(errors) > 0:
			print("Sentences causing errors: ")
			for s in errors:
				print(s)

		#server.terminate()
		#time.sleep(60)

		#server.communicate()


	#server.terminate()

	print("")
	print("Total errors in all grammars: " + str(total_errors))
	i = 0
	#analyzer.close()
	#while i < 100:
	#	print(i)








