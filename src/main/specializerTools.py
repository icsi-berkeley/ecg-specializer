"""
.. The Specalizer module gathers information from the SemSpec and 
    outputs an ntuple.

.. moduleauthor:: Luca Gilardi <lucag@icsi.berkeley.edu>, Sean Trott

"""


""" ADDED STUFF """
"""*****"""

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

# This just defines the interface
class NullSpecializer(object):
    def specialize(self, fs): 
        """Specialize fs into task-specific structures.
        """
        abstract  # @UndefinedVariable

class DebuggingSpecializer(NullSpecializer):
    def __init__(self):
        self.debug_mode = False

        # Original input sentence
        self._sentence = None

    """ Sets debug_mode to ON/OFF """
    def set_debug(self):
        self.debug_mode = not self.debug_mode 



class UtilitySpecializer(DebuggingSpecializer):
    def __init__(self):
        self._stacked = []
        DebuggingSpecializer.__init__(self)
        self.analyzer = Analyzer('http://localhost:8090')

    """ Input PROCESS, searches SemSpec for Adverb Modifiers. Currently just returns speed,
    but could easily be modified to return general manner information. """
    def get_actionDescriptor(self, process):
        for i in process.__features__.values():
            for role, filler in i.__items__():
                if filler.typesystem() == 'SCHEMA' and self.analyzer.issubtype('SCHEMA', filler.type(), 'AdverbModification'):
                    if process.index() == filler.modifiedThing.index():
                        return filler.value
        return None

    """ This returns a string of the specified relation of the landmark to the other RD, based on the values
    and mappings encoded in the SemSpec.
    """
    def get_locationDescriptor(self, goal):
        #location = {}
        location = ''
        for i in goal.__features__.values():
            for role, filler in i.__items__():
                if filler.type() == 'Sidedness':
                    if filler.back.index() == goal.index():
                        return 'behind' #location = 'behind'
                elif filler.type() == 'BoundedObject':
                    if filler.interior.index() == goal.index():
                        return 'into'
                elif filler.type() == "NEAR_Locative":
                    if filler.p.proximalArea.index() == goal.index(): #i.m.profiledArea.index(): 
                        location = 'near'    
                        #location['relation'] = 'near' 
                elif filler.type() == "AT_Locative":
                    if filler.p.proximalArea.index() == goal.index():
                        location = 'at' 
                        #location['relation'] = 'at'
                """
                elif filler.type() == 'INTO_Path':
                    if filler.bo.interior.index() == goal.index():
                        location = 'into'  
                """      
        return location 

    """Depth-first search of sentence to collect values matching object (GOAL). 
    Now just iterates through feature struct values (due to change in FS structure). Returns a dictionary
    of object type, properties, and trajector landmarks.
    """
    def get_objectDescriptor(self, goal):
        if 'referent' in goal.__dir__() and goal.referent.type():
            returned = {'referent': goal.referent.type(), 'type': goal.ontological_category.type()}
        elif goal.ontological_category.type() == 'location':
            returned = {'location': (int(goal.xCoord), int(goal.yCoord))}
        else:
            returned = {'type': goal.ontological_category.type()}
            if 'givenness' in goal.__dir__():
                returned['givenness'] = goal.givenness.type()
        for i in goal.__features__.values():
            for roles, filler in i.__items__():
                if filler.typesystem() == 'SCHEMA':
                    if self.analyzer.issubtype('SCHEMA', filler.type(), 'PropertyModifier'):
                        if filler.modifiedThing.index() == goal.index():
                            returned[str(filler.property.type())] = filler.value.type()
                    """
                    if filler.type() == 'PropertyModifier':
                        if filler.modifiedThing.index() == goal.index():
                            returned[str(filler.property.type())] = filler.value.type()
                    """
                    if filler.type() == "TrajectorLandmark":
                        if filler.trajector.index() == goal.index():
                            l = self.get_objectDescriptor(filler.landmark)
                            relation = self.get_locationDescriptor(filler.profiledArea)
                            locationDescriptor = {'objectDescriptor': l, 'relation': relation}
                            returned['locationDescriptor'] = locationDescriptor                                            
        return returned   

    """ Meant to match 'one-anaphora' with the antecedent. As in, "move to the big red box, then move to another one". Or,
    'He likes the painting by Picasso, and I like the one by Dali.' Not yet entirely clear what information to encode 
    besides object type. """
    def resolve_anaphoricOne(self, item):
        popper = list(self._stacked)
        while len(popper) > 0:
            ref = popper.pop()
            if 'location' in ref or 'locationDescriptor' in ref:
                ref = popper.pop()
            else:
                # Inspect object descriptor: if it contains color and size, maybe add these too?
                if item.givenness.type() == 'distinct':
                    return {'objectDescriptor': {'type': ref['objectDescriptor']['type'], 'givenness': 'distinct'}} 
                else:
                    test = self.get_objectDescriptor(item)
                    ### Here, it should evaluate the list of descriptors (color, size, etc.) and see which ones conflict with previous OD. have new function, "eval_properties".
                    merged = self.merge_descriptors(ref['objectDescriptor'], test)
                    #test['type'] = ref['objectDescriptor']['type']
                    return {'objectDescriptor': merged}
        raise Exception

    def merge_descriptors(self, old, new):
        """ Merges object descriptors from OLD and NEW. Objective: move all descriptions / properties from OLD
        into NEW unless NEW conflicts. If a property conflicts, then use the property in NEW. """
        for key, value in old.items():
            if not key in new or key == 'type':
                new[key] = old[key]
        return new
        
    """ Simple reference resolution gadget, meant to unify object pronouns with potential
    antecedents. """
    def resolve_referents(self, actionary=None, pred=None):
        popper = list(self._stacked)
        while len(popper) > 0:
            ref = popper.pop()
            if self.resolves(ref, actionary, pred):
                if 'partDescriptor' in ref:
                    return ref['partDescriptor']
                return ref
        raise Exception

    """ Returns a boolean on whether or not the "popped" value works in the context provided. """
    def resolves(self, popped, actionary=None, pred=None):
        if actionary == 'be2' or actionary == 'be':
            if 'location' in popped or 'locationDescriptor' in popped:
                return 'relation' in pred
            else:
                if 'referent' in popped:
                    test = popped['referent'].replace('_', '-')
                    return self.analyzer.issubtype('ONTOLOGY', test, 'physicalEntity')
                else:
                    return self.analyzer.issubtype('ONTOLOGY', popped['objectDescriptor']['type'], 'physicalEntity')
        if actionary == 'forceapplication' or actionary == 'move':
            if 'location' in popped or 'locationDescriptor' in popped:
                return False
            #if 'referent' in popped: #hasattr(popped, 'referent'):
            #    test = popped['referent'].replace('_', '-')
            #    return self.analyzer.issubtype('ONTOLOGY', test, 'moveable')
            if 'partDescriptor' in popped:
                pd = popped['partDescriptor']['objectDescriptor']
                if 'referent' in pd:
                    return self.analyzer.issubtype('ONTOLOGY', pd['referent'].replace('_', '-'), 'moveable')
                else:
                    return self.analyzer.issubtype('ONTOLOGY', pd['type'], 'moveable')
            else:
                return self.analyzer.issubtype('ONTOLOGY', popped['objectDescriptor']['type'], 'moveable')
        return False      

class TemplateSpecializer(NullSpecializer):
    def __init__(self):

        self._NTUPLE_T = dict(predicate_type=None,             
                              parameters=None, # one of (_execute, _query)                         
                              return_type='error_descriptor') 
        # Basic executable dictionary
        self._execute = dict(kind='execute',
                             control_state='ongoing', 
                             action=None,
                             protagonist=None,
                             distance=Struct(value=8, units='square'),
                             goal=None,
                             speed = .5,
                             heading=None, #'north',
                             direction=None)


        # TESTING: Causal dictionary: "Robot1, move the box to location 1 1!"
        self._cause = dict(kind = 'cause',
                           causer = None,
                           action = None)

        # Assertion: "the box is red"
        self._assertion = dict(kind='assertion',  # might need to change parameters
                             action=None,
                             protagonist=None,
                             predication=None)    

        self._WH = dict(kind = 'query',
                        protagonist = None,
                        action = None,
                        predication = None,
                        specificWh = None)
 

        #Y/N dictionary: is the box red?
        self._YN = dict(kind = 'query',
                        protagonist=None,
                        action=None,
                        predication=None)

        self._conditional = dict(kind='conditional',
                                 condition=None,  # Maybe should be template for Y/N question?
                                 command = self._execute)


