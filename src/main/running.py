import sys, traceback
import copy
from copy import deepcopy
import pickle
import time
import json
from pprint import pprint
from feature import as_featurestruct
from json import dumps
from utils import flatten
from itertools import chain
try:
    # Python 2?
    from xmlrpclib import ServerProxy, Fault  # @UnresolvedImport @UnusedImport
except:
    # Therefore it must be Python 3.
    from xmlrpc.client import ServerProxy, Fault #@UnusedImport @UnresolvedImport @Reimport

from utils import update, Struct
from feature import StructJSONEncoder 
from os.path import basename
from solver import NullProblemSolver, MorseProblemSolver, XnetProblemSolver,\
    MockProblemSolver

class Analyzer(object):
    """A proxy for the Analyzer. 
    Note: It assumes the server is running with the right grammar
    """
    def __init__(self, url):
        self.analyzer = ServerProxy(url) 
        
    def parse(self, sentence):        
        return [as_featurestruct(r, s) for r, s in self.analyzer.parse(sentence)]
    
    def issubtype(self, typesystem, child, parent):
        return self.analyzer.issubtype(typesystem, child, parent)

analyzer = Analyzer("http://localhost:8090")




