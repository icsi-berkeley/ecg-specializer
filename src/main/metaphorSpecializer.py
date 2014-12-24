"""
.. This "Metaphor Specializer" is in progress, but the idea is to gather information from a SemSpec
and output it in some more readable or accessible structure. It will also contain information about individual
fillers, like "poverty" - such as the frequency with which "poverty" occurs in the "Social problems are animate agents"
metaphor vs. the "States are Locations" metaphor.

.. moduleauthor:: Sean Trott <seantrott@icsi.berkeley.edu>

Ideas: 
-Maybe build in visualization tools, using R or some type of Python graph tool. So when you query "lexeme" and then "poverty",
you could get some type of bar graph, showing the frequency of each metaphor "poverty" appears in. 
-Build in better tool for accessing individual roles that "poverty" appears in:
    -social problems / infections/harmful agents
    -property / landmark (states are locations)


"""


""" ADDED STUFF """
"""*****"""

import sys, traceback
import copy
from copy import deepcopy
import time
import json
from pprint import pprint
from feature import as_featurestruct
from json import dumps
from utils import flatten
from itertools import chain
from rpy2 import robjects

try:
    # Python 2?
    from xmlrpclib import ServerProxy, Fault  # @UnresolvedImport @UnusedImport
except:
    # Therefore it must be Python 3.
    from xmlrpc.client import ServerProxy, Fault #@UnusedImport @UnresolvedImport @Reimport

from utils import update, Struct
from feature import StructJSONEncoder 
from os.path import basename
from specializerTools import *
from solver2 import NullProblemSolver, MorseProblemSolver, XnetProblemSolver,\
    MockProblemSolver
# from pprint import pprint, pformat

def updated(d, *maps, **entries):
    """A "functional" version of update...
    """
    dd = dict(**d) if isinstance(d, dict) else Struct(d)
    return update(dd, *maps, **entries)
 

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


class Color(object):
   PURPLE = '\033[95m'
   CYAN = '\033[96m'
   DARKCYAN = '\033[36m'
   BLUE = '\033[94m'
   GREEN = '\033[92m'
   YELLOW = '\033[93m'
   RED = '\033[91m'
   BOLD = '\033[1m'
   UNDERLINE = '\033[4m'
   END = '\033[0m'

class MetaphorSpecializer(UtilitySpecializer):
    def __init__(self):
        """ Inherits from UtilitySpecializer. """

        # This puts the Analyzer and _Stacked list into the Task-Specializer --> is there a cleaner way to do this?
        UtilitySpecializer.__init__(self)

        # Data structure, representing all of the metaphors parsed from input sentences
        self.metaphors = {}

        self.database = {}

        self.sentence = None

        self.parse_num = None

        """ Ideally will be some sort of repository of lexemes and their corresponding roles. """
        self.lexemes = {}

    def get_related_roles(self, obj):
        roles = []
        for slot in obj.__features__.values():
            for role, filler in slot.__items__():
                if filler.index() == obj.index():  
                    roles.append(role)
        return roles

    def get_related_roles2(self, schema, obj):
        """ * Make this recursive. Continually search within contained schemas. """
        roles = []
        for role, filler in schema.__items__():
            if hasattr(filler, "__items__"):
                for r,f in filler.__items__():
                    if f.index() == obj.index():
                        roles.append(r)
            if filler.index() == obj.index():
                roles.append(role)
        return roles


    def extract_metaphors(self, fs):
        for slot in fs.__features__.values():
            for role, filler in slot.__items__():
                if filler.typesystem() == 'SCHEMA':
                    f = filler.type()
                    #f = f.replace("_", "-")
                    if self.analyzer.issubtype('SCHEMA', f, 'Metaphor_pairTest'):
                        #self.add_metaphors(filler.type())
                        self.list_mappings(filler)


    def add_metaphors(self, metaphor):
        if self._sentence in self.metaphors:
            if not metaphor in self.metaphors[self._sentence]:
                self.metaphors[self._sentence].append(metaphor)
        else:
            self.metaphors[self._sentence] = [metaphor]

    def view_metaphors(self):
        for sentence, metaphors in self.metaphors.items():
            print("")
            print(sentence)
            for metaphor in metaphors:
                print(metaphor)
        print("")


    def view_id(self, sentence):
        """ prints out mappings of SENTENCE nicely. """
        #for key, value in self.database.items():
        #    print(key)
        for metaphor in self.database[sentence]:
                print("")
                print(Color.BOLD + metaphor['name'] + Color.END)
                for mapping in metaphor['mappings']:
                    print("")
                    if mapping[2]:
                        print(Color.UNDERLINE + "Filler:" + Color.END + " " + mapping[2])
                    print(Color.UNDERLINE + "Mapping:" + Color.END)
                    target = [x for x in mapping[0] if not x in mapping[1] and x != 'protagonist' and x != 'target']
                    source = [x for x in mapping[1] if not x in mapping[0] and x != 'protagonist' and x != 'source']
                    shared = list(set(mapping[0]).intersection(mapping[1]))
                    print(str(target) + " <---- " + str(source))
                    print("")
                    print("Shared structure:")
                    print(shared)
                    print("")

    def elaborate_mappings(self, metaphor):
        """ Adds to database of metaphors, with elaborate mappings between them. Also adds lexemes involved in metaphor
        to lexeme base."""
        if self._sentence in self.database:
            if not str(metaphor.name) in [x['name'] for x in self.database[self._sentence]]:
                self.database[self._sentence].append({"parse:": self.parse_num, "name": str(metaphor.name), 'mappings': []})
                for role, filler in metaphor.__items__():
                    if filler.type() == 'Mapping':
                        fill = None
                        targets = set(self.get_related_roles2(metaphor.target, filler.target))
                        source = set(self.get_related_roles2(metaphor.source, filler.source))                         
                        if hasattr(filler.target, "ontological_category"):
                            fill = filler.target.ontological_category.type()
                            self.add_item(filler.target.ontological_category.type(), source, targets, str(metaphor.name))
                        if hasattr(filler.target, "referent") and filler.target.referent.type():
                            self.add_item(filler.target.referent.type(), source, targets, str(metaphor.name))
 
                        self.database[self._sentence][-1]['mappings'].append([targets, source, fill])  
        else:
            self.database[self._sentence] = [{"parse:": self.parse_num, "name": str(metaphor.name), 'mappings': []}]
            for role, filler in metaphor.__items__():
                if filler.type() == 'Mapping':
                    fill = None
                    targets = set(self.get_related_roles2(metaphor.target, filler.target))
                    source = set(self.get_related_roles2(metaphor.source, filler.source))
                    if hasattr(filler.target, "ontological_category"):
                        fill = filler.target.ontological_category.type()
                        self.add_item(filler.target.ontological_category.type(), source, targets, str(metaphor.name))
                    if hasattr(filler.target, "referent") and filler.target.referent.type():
                        self.add_item(filler.target.referent.type(), source, targets, str(metaphor.name))   
                    self.database[self._sentence][-1]['mappings'].append([targets, source, fill])  


    def list_mappings(self, metaphor):
        """ Lists mappings of metaphor, also adds string representation of metaphor to repository. 
        Then, prints out mappings in metaphor (source, target, etc.), and if the roles have ont-categories
        or actionaries, adds these to lexeme base.
        This basically just calls two functions based on the metaphor input - it adds the metaphor to the list of metaphors,
        then also called "elaborate_mappings", which iterates through the mappings in the metaphor and adds them to the "database". elaborate_mappings
        also adds the lexemes to the lexeme-base if applicable. """
        #print("Metaphor name: %s" %metaphor.name)
        self.add_metaphors(str(metaphor.name))
        self.elaborate_mappings(metaphor)
        """
        for role, filler in metaphor.__items__():
            if filler.type() == "Mapping":

                targets = set(self.get_related_roles2(metaphor.target, filler.target))
                source = set(self.get_related_roles2(metaphor.source, filler.source))

                if hasattr(filler.target, "ontological_category"):
                    #print(filler.target.ontological_category.type())
                    self.add_item(filler.target.ontological_category.type(), source, targets, str(metaphor.name))

                if hasattr(filler.target, "referent") and filler.target.referent.type():
                    self.add_item(filler.target.referent.type(), source, targets, str(metaphor.name))
        """


    def add_item(self, item, sources, targets, name):
        """ Adds lexemes to list of lexemes and their roles + metaphors.
        might add "count" - number of times lexeme appears in certain role.
        """
        if item in self.lexemes:
            if name in self.lexemes[item].keys():
                self.lexemes[item][name]['frequency'] += 1
                if not self._sentence in self.lexemes[item][name]['sentences']:
                    self.lexemes[item][name]['sentences'].append(self._sentence)
            #if self._sentence in self.lexemes[item].keys():
                #if not name in self.lexemes[item][self._sentence]:            
            #    if not name in [x[1] for x in self.lexemes[item][self._sentence]]:
            #        self.lexemes[item][self._sentence].append([self.parse_num, name, {'source_roles':sources, 'target_roles':targets}])
            else:
                self.lexemes[item][name] = {'roles': {'source': sources, 'target': targets},
                                            'frequency': 1,
                                            'parse': self.parse_num,
                                            'sentences': [self._sentence]}
        else:
            self.lexemes[item] = {name: {'roles': {'source': sources, 'target': targets},
                                         'frequency': 1,
                                         'parse': self.parse_num,
                                         'sentences': [self._sentence]}}
            #self.lexemes[item] = {self._sentence: [[self.parse_num, name, {'source_roles':sources, 'target_roles':targets}]]}


    def obtain_lexeme(self, lexeme):
        return self.lexemes[lexeme]

    def print_lexemes(self):
        for i in self.lexemes:
            print(i)

    def plot_lexeme(self, lexeme):
        data = self.lexemes[lexeme]




    def specialize(self, fs, count):
        """This method takes a SemSpec (the fs parameter) and modifies a data structure with the primary metaphors,
        from which you can access all of the roles / fillers of certain lexemes. * IN progress (exact functionality uncertain)
        
        """
        self.parse_num = "parse " + str(count)
        b = self.extract_metaphors(fs)
        #a = self.get_related_roles(fs.m.profiledParticipant)
        #if len(self.metaphors[self._sentence]) <= 0:
        #    del self.metaphors[self._sentence]
        #self.view_id(self._sentence)
        return None


def main_loop(analyzer, specializer=MetaphorSpecializer()):
    """REPL-like thing. Should be reusable.
    """


    def prompt():
        while True:
            ans = input('> ') # Python 3
            specialize = True
            if ans.lower() == 'q':
                return
            elif ans.lower() == 'view':
                specialize = False
                specializer.view_metaphors()
            elif ans.lower() == 'plot':
                l = input("which lexeme? >")
                try:
                    specializer.plot(l)
                except Exception:
                    print("Could not find lexeme. Here are the stored lexemes:")
                    specializer.print_lexemes()
            elif ans.lower() == 'viewid':
                specialize = False
                #pprint(specializer.database)
                sent = input("enter sentence> ")
                try:
                    specializer.view_id(sent)
                except Exception:
                    print("Could not find sentence. Here are the sentences you've already analyzed:")
                    [print(i) for i in specializer.database]
            elif ans.lower() == 'lexeme':
                specialize = False
                lexeme = input("enter specific lexeme> ")
                try:
                    pprint(specializer.obtain_lexeme(lexeme))
                except Exception:
                    print("Could not find lexeme. Here are the stored lexemes:")
                    specializer.print_lexemes()
            elif ans and specialize:
                specializer._sentence = ans
                try:
                    yield analyzer.parse(ans)#this is a generator
                except Fault as err:
                    print('Fault', err)
                    if err.faultString == 'compling.parser.ParserException':
                        print("No parses found for '%s'" % ans)


    """ This was altered somewhat to only take the lowest-cost parse. 
    May add in other logic (#for fs in analyses) to iterate through each of the parses as well.
    This may be desired for multiple interpretations. In that case we may also want to have parse_cost information?
    """

    for analyses in prompt():
        parse_num = 1
        for fs in analyses:
            try:     
                #print("New Analysis: ")
                specializer.specialize(fs, parse_num)  
                parse_num += 1 
            except:
                print('Problem solving %s' % analyses)
                traceback.print_exc()
        
        

    
    
if __name__ == '__main__':
    # These contain default values for the options
    main_loop(Analyzer('http://localhost:8090'), specializer=MetaphorSpecializer())
    sys.exit(0)
