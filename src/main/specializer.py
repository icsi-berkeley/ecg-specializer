"""
.. The Specalizer module gathers information from the SemSpec and 
    outputs an ntuple.

.. moduleauthor:: Luca Gilardi <lucag@icsi.berkeley.edu>

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


class TrivialSpecializer(NullSpecializer):
    def __init__(self):

        # Stack of past object-descriptors and location-descriptors, used for reference and event resolution.
        # Maybe store pairs, like: ("LD", {relation: near, objectDescriptor: {type: box, color: red}})
        # vs. ("OD", objectDescriptor: {type: box, color: red})
        self._stacked = []

        self.analyzer = Analyzer('http://localhost:8090')

        # Setting for printing N-tuples or not
        self.debug_mode = False

        # File that parameters are sent to (default is NONE)
        self._output = None

        """ This is a dictionary meant to represent the maps between input words and their definitions.
        For example, "visit" could be a key, which triggers "Move to QL2 then return", etc.
        """
        self._definitions = dict()

        # Original input sentence
        self._sentence = None

        # Does it need to be solved? e.g., is it just a definition type? Defaults as True
        self.needs_solve = True

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
                             heading=None,
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


    """ Sets debug_mode to ON/OFF """
    def set_debug(self):
        self.debug_mode = not self.debug_mode  


    """ Meant to match 'one-anaphora' with the antecedent. As in, "move to the big red box, then move to another one". Or,
    'He likes the painting by Picasso, and I like the one by Dali.' Not yet entirely clear what information to encode 
    besides object type. """
    def resolve_anaphoricOne(self):
        popper = list(self._stacked)
        while len(popper) > 0:
            ref = popper.pop()
            if 'location' in ref or 'locationDescriptor' in ref:
                ref = popper.pop()
            else:
                # Inspect object descriptor: if it contains color and size, maybe add these too?
                return {'objectDescriptor': {'type': ref['objectDescriptor']['type'], 'givenness': 'distinct'}}  # Maybe make givenness "distinct", then have solver take care of it
        raise Exception

    """ Simple reference resolution gadget, meant to unify object pronouns with potential
    antecedents. * Some change may need to be made to Analyzer so that lattice of ontology 
    can be accessed, not simply type """
    def resolve_referents(self, actionary=None, pred=None):
        popper = list(self._stacked)
        while len(popper) > 0:
            ref = popper.pop()
            if self.resolves(ref, actionary, pred):
                return ref
        raise Exception

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

    def specialize(self, fs):
        """This method takes a SemSpec (the fs parameter) and outputs an n-tuple.
        
        This needs more than some cleaning.
        """
        def make_parameters():

            # Used just to return the referent of a particular RD, since this code is used frequently in different fucnctions
            def get_referent(process, params):
                if process.protagonist.referent.type() == "antecedent":
                    try:
                        subject = self.resolve_referents(actionary = params['action'], pred = params['predication'])
                    except(Exception):
                        print("Antecedent not found.")
                        return None
                else:
                    if process.protagonist.referent.type():
                        subject = {'objectDescriptor': {'referent': process.protagonist.referent.type(), 'type': process.protagonist.ontological_category.type()}}
                    else:
                        subject = {'objectDescriptor': get_objectDescriptor(process.protagonist)}
                    self._stacked.append(subject)
                return subject

            # Returns parameters for Stasis type of process ("the box is red")
            def params_for_stasis(process, d):
                prop = process.state
                params = updated(d, action = process.actionary.type()) #process.protagonist.ontological_category.type())
                if prop.type() == 'PropertyModifier':
                    a = {str(prop.property.type()): prop.value.type()}#, 'type': 'property'}
                    params.update(predication = a)
                elif prop.type() == 'TrajectorLandmark':
                    if prop.landmark.referent.type() == 'antecedent':
                        landmark = get_referent(process, params)
                    else:
                        landmark = get_objectDescriptor(prop.landmark)
                    pred = {'relation': get_locationDescriptor(prop.profiledArea), 'objectDescriptor': landmark}
                    #print(prop.profiledArea.ontological_category.type())
                    params.update(predication=pred)
                if hasattr(process.protagonist, 'referent'):
                    subject = get_referent(process, params)
                params.update(protagonist=subject)
                if d != self._WH:
                    params = crosscheck_params(params)
                return params                

            # Returns parameters for motion path process ("move to the box")
            
            def params_for_motionPath(process, d):
                if 'referent' in process.mover.__dir__():
                    if process.mover.referent.type() == 'antecedent':
                        try:
                            mover = self.resolve_referents('move')
                        except(Exception):
                            print("No Antecedent found")
                            return None
                    elif process.mover.referent.type():
                        mover = process.mover.referent.type()
                    else:
                        mover = get_objectDescriptor(process.spg.trajector)
                else:
                    mover = get_objectDescriptor(process.spg.trajector)
                params = updated(d, protagonist=mover)
                if hasattr(process, 'actionary'):
                    params.update(action = process.actionary.type())
                if hasattr(process, 'speed') and str(process.speed) != "None":# and process.speed.type():
                    params.update(speed = float(process.speed))
                else:  # Might change this - "dash quickly" (what should be done here?)
                    s = get_actionDescriptor(process)
                    if s is not None:
                        params.update(speed = float(s))
                # Is there a heading specified?
                if hasattr(process, 'heading'):
                    if process.heading.type():
                        params.update(heading=process.heading.tag.type())
                # Is a distance specified?                
                if hasattr(process.spg, 'distance') and hasattr(process.spg.distance, 'amount'):
                    d = process.spg.distance
                    params.update(distance=Struct(value=int(d.amount.value.value), units=d.units.type()))
                # Is a goal specified?
                if hasattr(process.spg, 'goal'):
                    g = process.spg.goal
                    goal = dict()
                    if g.type() == 'home':
                        goal['location'] = g.type()
                    elif g.ontological_category.type() == 'heading':
                        goal = None
                        params.update(heading=g.tag.type())
                    elif g.ontological_category.type() == 'region':
                        goal['locationDescriptor'] = {'objectDescriptor': get_objectDescriptor(process.spg.landmark), 'relation': get_locationDescriptor(g)}
                    elif self.analyzer.issubtype('ONTOLOGY', g.ontological_category.type(), 'part'): # checks if it's a "part" in a part whole relation
                        goal['partDescriptor'] = {'objectDescriptor': get_objectDescriptor(g.extensions.whole), 'relation': get_objectDescriptor(g)}
                    elif g.referent.type():
                        if g.referent.type() == "antecedent":
                            try:
                                if g.givenness.type() == 'distinct':
                                    goal = self.resolve_anaphoricOne()
                                else:
                                    goal = self.resolve_referents(params['action'])
                            except(Exception):
                                print("No Antecedent found")
                                return None
                            # Resolve_referents()
                        else:
                            goal['objectDescriptor'] = {'referent': g.referent.type(), 'type': g.ontological_category.type()}    ## Possibly add "object descriptor" as key here        
                    elif g.ontological_category.type() == 'location':
                        # if complex location, get "location descriptor"
                        goal['location'] = (int(g.xCoord), int(g.yCoord))
                    else:
                        goal['objectDescriptor'] = get_objectDescriptor(g) #properties
                        #goal.objectDescriptor['type'] = goal.type
                    self._stacked.append(goal)      
                    params.update(goal=goal)
                # Is a direction specified?
                                            # Here, sets "heading" param to goal's heading, and resets goal to None 
                        #Alternatively, it could add a 'heading' param to goal, but this seems more complicated than necessary.
                if hasattr(process, 'direction'):
                    params.update(direction=process.direction.type())                 
                return params   

            # gets params for force-application, like "push the box"
            def params_for_forceapplication(process, d):
                # Protagonist vs. "acted_upon"
                params = updated(d,  action = process.actionary.type())          
                if hasattr(process.actor, 'referent'):
                    params.update(protagonist=process.actor.referent.type())
                if hasattr(process.actedUpon, 'referent'):
                    if process.actedUpon.referent.type() == "antecedent":
                        try:
                            if process.actedUpon.givenness.type() == "distinct":
                                affected = self.resolve_anaphoricOne()
                            else:
                                affected = self.resolve_referents(actionary = params['action'])
                        except(Exception):
                            print("Antecedent not found.")
                            return None
                    else:
                        if process.actedUpon.referent.type():
                            affected = {'objectDescriptor': {'referent': process.actedUpon.referent.type(), 'type': process.actedUpon.ontological_category.type()}}
                        else:
                            affected = {'objectDescriptor': get_objectDescriptor(process.actedUpon)}
                    self._stacked.append(affected)
                else:
                    affected = None
                #if hasattr(process.actedUpon, 'referent'):
                    #affected = get_referent(process, params)   # else None?
                params.update(acted_upon = affected)
                # Stuff to add potentially: "force transfer", "effector / instrument", routine
                return params  

            def params_for_stagedprocess(process, d):
                params = updated(self._execute, 
                                 action=core.m.profiledProcess.actionary, 
                                 protagonist=process.mover.referent.type())
                if eventProcess.stageRole.type():
                    params.update(control_state=eventProcess.stageRole)
                return params              


            # Dispatches "process" to a function to fill in template, depending on process type. Returns parameters.
            def params_for_simple(process, message=None):
                """Make parameters for a single process
                """
                if message == "dec":
                    d = self._assertion
                elif message == 'w':
                    d = self._WH
                    d['specificWh'] = process.protagonist.specificWh.type()
                    if d['specificWh'] == 'where':
                        return params_for_where(process, d)
                elif message == "q" or message =="cond":
                    d = self._YN
                else:
                    d = self._execute
                processes = {'MotionPath': params_for_motionPath,#(process, d),
                             'Stasis': params_for_stasis,#(process, d),
                             'ForceApplication': params_for_forceapplication,#(process ,d),
                             'StagedProcess': params_for_stagedprocess}#(process, d)}
                assert process.type() in processes, 'problem: process type not in allowed types'
                return processes[process.type()](process, d)

            # This function just returns params for "where", like "where is Box1". Different process format than "which box is red?"
            def params_for_where(process, d):
                params = updated(d, action=process.actionary.type())
                h = process.state.second
                if hasattr(h, 'referent'):
                    if h.referent.type() == 'antecedent':
                        try:
                            p = self.resolve_referents(process.actionary.type())
                        except(Exception):
                            print("No antecedent found")
                            return None
                    else:
                        if h.referent.type():
                            p = {'referent': h.referent.type(), 'type': h.ontological_category.type()}
                        else:
                            p = {'objectDescriptor': get_objectDescriptor(h)}
                        self._stacked.append(p)
                    params.update(protagonist=p)
                #p = process.protagonist
                return params
                    
            
            """ This is a temporary function to address a larger issue, which is:
            In sentences like "is the big box red?", the predication "red" points back to "box".
            Thus, in the get_objectDescriptor function, "red" becomes one of the modifier properties in
            the description for "box". This is more of a grammar issue, and will have to be addressed,
            but for now, this function removes items from the object description that share a domain
            with things in the predication.
            """
            # Update: this has since been addressed in the grammar (predication no longer points back to subject)
            def crosscheck_params(p):
                predication = p['predication']
                od = p['protagonist'] 
                if 'objectDescriptor' in od:
                    od = od['objectDescriptor']
                for key in predication.keys():
                    if key in od.keys():
                        if od[key] == predication[key]:
                            del od[key]
                return p

            """ Input PROCESS, searches SemSpec for Adverb Modifiers. Currently just returns speed,
            but could easily be modified to return general manner information. """
            def get_actionDescriptor(process):
                for i in process.__features__.values():
                    for role, filler in i.__items__():
                        if filler.typesystem() == 'SCHEMA' and self.analyzer.issubtype('SCHEMA', filler.type(), 'AdverbModification'):
                            if process.index() == filler.modifiedThing.index():
                                return filler.value
                return None

            """ This should return a dictionary with a description of the location of the specified "goal". 
            Should be able to work for both: "move behind the box" (LD = {'relation': 'behind', OD: {type:box}})
            and "move to the box behind the table: OD = {type: box, LD = {'relation': 'near', OD: {type: box}}}
            """
            def get_locationDescriptor(goal):
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

            #Depth-first search of sentence to collect values matching object (GOAL). 
            # Now just iterates through feature struct values (due to change in FS structure)
            def get_objectDescriptor(goal):
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
                                    l = get_objectDescriptor(filler.landmark)
                                    relation = get_locationDescriptor(filler.profiledArea)
                                    locationDescriptor = {'objectDescriptor': l, 'relation': relation}
                                    returned['locationDescriptor'] = locationDescriptor                                            
                return returned

            """ Testing with "attempting mapping", to use defined processes in complex processes."""
            def params_for_compound(process):
                try:
                    yield attempt_mapping(core)
                except Exception as e:
                    None
                if process.type() == 'SerialProcess':
                    for pgen in chain(map(params_for_compound, (process.process1, process.process2))):
                        for p in pgen:
                            if p is None:
                                None
                            else:
                                yield p
                elif process.type() == 'CauseEffect':
                    try:
                        par = attempt_mapping(process.ed)
                        for p in par:
                            if par is None:
                                return None
                            yield p
                    except Exception as e:
                        yield causalProcess(process)
                else:
                    yield params_for_simple(process)


            def causalProcess(process):
                params = updated(self._cause, action = process.actionary.type())
                if hasattr(process.causalAgent, 'referent') and process.causalAgent.referent.type():
                    params.update(causer = process.causalAgent.referent.type())
                else:
                    params.update(causer = get_objectDescriptor(process.causalAgent))
                #cp = params_for_compound(process.process1)
                cp = params_for_simple(process.process1)
                ap = params_for_simple(process.process2)
                if cp is None or ap is None:
                    return None
                params.update(causalProcess = Struct(cp))
                params.update(affectedProcess = Struct(ap))
                return params

            """ Maps words (signs) to their definitions (signified). 
            E.g., "Robot1, visit the red box" will map "the red box" to "goal"
            in "move to QL2 then return".
            """
            def map_definitions(actionary, process):
                definition = self._definitions[actionary]

                copy = deepcopy(definition)
                goals = []
                if hasattr(core.m.profiledProcess, 'mover') and core.m.profiledProcess.mover.type() == 'ConjRD':
                    goal = eval_complexRD(core.m.profiledProcess.mover)
                    for k in goal:
                        goals.append(get_objectDescriptor(k))
                j = 0
                for i in copy:
                    if 'action' in i and i['action'] == 'push_move':
                        i = map_complex_struct(i, goals, goals[j])   # Need to JUST pass in push_move ("i")
                    else:
                        for key, v in i.items():
                            if key == "protagonist":
                                i[key] = core.m.profiledParticipant.referent.type()
                            if key == "goal":
                                if 'objectDescriptor' in v and 'referent' in v['objectDescriptor'] and v['objectDescriptor']['referent'] == 'variable':
                                    if process.mover.type() == 'ConjRD': #core.m.profiledProcess.mover.type() == 'ConjRD':
                                        i[key] = {'objectDescriptor': goals[j]}
                                    else:
                                        i[key] = {'objectDescriptor': get_objectDescriptor(process.mover)}#core.m.profiledProcess.mover)}
                    j += 1
                return copy

            """ Takes in a dictionary, and maps the values accordingly. Easier to call function than
            write code multiple times. """
            def map_values(dictionary):
                return None

            def map_complex_struct(params, goals, obj):
                for key,value in params.items():
                    #for key, value in i.items():
                    if key == 'causer':
                        params[key] = core.m.profiledParticipant.referent.type()
                    if type(value) == Struct:
                        mini_dict = value.__dict__
                        for k, v in mini_dict.items():
                            if k == 'protagonist':
                                mini_dict[k] = core.m.profiledParticipant.referent.type()
                            if k == 'acted_upon':
                                if 'referent' in v['objectDescriptor'] and v['objectDescriptor']['referent'] == 'variable':
                                    if core.m.profiledProcess.mover.type() == 'ConjRD':
                                        mini_dict[k] = {'objectDescriptor': obj} #goals[j]}  # Commented out: only going to pass in single object
                                    else:
                                        mini_dict[k] = {'objectDescriptor': get_objectDescriptor(core.m.profiledProcess.mover)}  # FIX THIS
                            if k == 'goal' and mini_dict[k] != None:
                                if 'referent' in v and v['referent'] == 'variable':
                                    if core.m.profiledProcess.mover.type() == 'ConjRD':
                                        mini_dict[k] = {'objectDescriptor': goals[j]}
                                    else:
                                        mini_dict[k] = {'objectDescriptor': get_objectDescriptor(core.m.profiledProcess.mover)}  # FIX THIS

                return [params]

            """ Takes in a complex RD, such as "the blue box and the red box", and returns a list of each
            separate RD: [the blue box, the red box...], which is easier to work with. Analagous to transferring
            items from binary tree to a non-nested list. """
            def eval_complexRD(rd):
                if rd.rd1.type() == 'ConjRD' and rd.rd2.type() == 'ConjRD':
                    return eval_complexRD(rd.rd1) + eval_complexRD(rd.rd2)
                elif rd.rd1.type() == 'ConjRD':
                    return eval_complexRD(rd.rd1) + [rd.rd2]
                elif rd.rd2.type() == "ConjRD":
                    return [rd.rd1] + eval_complexRD(rd.rd2)
                else:
                    return [rd.rd1, rd.rd2]

            self.needs_solve = True

            core = fs.rootconstituent.core  # needed in params_for_simple(process)

            """ Get actionary, use in "map definitions" 
            NOTE: This code should be used in construct_conditional, etc. --> need to be more
            loops attempting to map these definitions rather than just simple imperatives.
            Ex: "visit Box1 then visit Box2" 
            
            try:
                actionary = core.m.profiledProcess.actionary.type()
                if actionary in self._definitions:
                    p = map_definitions(actionary)
                    return p
            except Exception as e:
                #print(e)
                None
            """

            # Fix this?
            def attempt_mapping(c):
                actionary = c.profiledProcess.actionary.type()
                if actionary in self._definitions:
                    p = map_definitions(actionary, c.profiledProcess)
                    return p

            f = None
            try:
                f = attempt_mapping(core.m)
            except Exception as e:
                #print(e)
                None
            
            if f:
                return f

            
            def construct_YN():
                params = [params_for_simple(core.m.eventProcess, 'q')]
                return params 

            def construct_WH():
                params = [params_for_simple(core.m.eventProcess, 'w')]
                return params

            def construct_Declarative():
                params = [params_for_simple(core.m.eventProcess, 'dec')]
                return params

            def construct_Imperative():
                allowed_types = dict(compound=['SerialProcess', 'CauseEffect'],
                                     simple=['MotionPath', 'CauseMotionPathAction', 'StagedProcess', 'Stasis'])
                t = eventProcess.type()
                assert t in flatten(allowed_types.values()), 'problem: process type is: %s' % t
                if t in allowed_types['simple']:
                    return [params_for_simple(eventProcess)]
                else:
                    return list(params_for_compound(eventProcess))

            """ This logic all needs to be fixed up in a better evaluating loop. Should constantly
            run "compound process" to check if serial or causal process. Can't assume it's a simple prcoess. """
            def construct_condImp():
                cond = Struct(params_for_simple(core.m.ed1.eventProcess, "cond"))
                a = core.m.ed2.eventProcess
                action = list(params_for_compound(core.m.ed2.eventProcess)) #params_for_compound(core.m.ed1.eventProcess)
                action2 = []
                if cond is None or None in action:
                    return None
                for i in action:
                    action2.append(Struct(i)) 
                #if a.type() == 'CauseEffect':
                #    action = Struct(causalProcess(core.m.ed2.eventProcess))
                #else:
                #    action = Struct(params_for_simple(a))
                params = [updated(self._conditional, command=action2, condition=cond)]
                #if not 'referent' in action['goal']:
                #    params = resolve_referents(params[0])
                return params 
                    
            def construct_Definition():
                self.needs_solve = False
                a = core.m.sign.actionary.type()
                b = core.m.signified
                new = list(params_for_compound(b.eventProcess))
                self._definitions[a] = new
                return new  

            moods = {'YN_Question': construct_YN,
                     'WH_Question': construct_WH,
                     'Declarative': construct_Declarative,
                     'Imperative': construct_Imperative,
                     'Conditional_Imperative': construct_condImp,
                     'Definition': construct_Definition}

            eventProcess = core.m.eventProcess
            return moods[mood]()  

        # Add mood for conditionals, etc.        
        mood = fs.m.mood.replace('-', '_')
        assert mood in ('YN_Question', 'WH_Question', 'Declarative', 'Imperative', 'Conditional_Imperative', 'Definition')


        # Dispatch call to some other specialize_* methods.
        # Note: now parameters is a sequence.
        params = make_parameters()


        if params is None or params[0] is None:
            self.needs_solve == False
            return None

        ntuple = updated(self._NTUPLE_T,
                         getattr(self, 'specialize_%s' % mood)(fs),
                         parameters=[Struct(param) for param in params])

        if self.debug_mode:
            print(Struct(ntuple))
            dumpfile = open('src/main/pickled.p', 'ab')
            pickle.dump(Struct(ntuple), dumpfile)
            dumpfile.close()
            self._output.write("\n\n{0} \n{1} \n{2}".format(mood, self._sentence, str(Struct(ntuple))))
        return Struct(ntuple)

    # Is this right?
    def specialize_Conditional_Imperative(self, fs):
        return dict(predicate_type='conditional', return_type = 'error_descriptor')    

    def specialize_YN_Question(self, fs):
        return dict(predicate_type='query', return_type='boolean')

    def specialize_WH_Question(self, fs):
        specific = fs.m.content.profiledParticipant.specificWh.type()
        f = 'collection_of' if fs.m.content.profiledParticipant.number.type() == 'plural' else 'singleton'
        return dict(predicate_type='query',
                    return_type='%s(class_reference)' % f if specific == 'what' else '%s(instance_reference)' % f)

    def specialize_Declarative(self, fs):
        return dict(predicate_type='assertion', return_type='error_descriptor')

    def specialize_Imperative(self, fs):
        return dict(predicate_type='command', return_type='error_descriptor')

    def specialize_Definition(self, fs):
        return dict(predicate_type='definition', return_type = 'error_descriptor')


def main_loop(analyzer, solver=NullProblemSolver(), specializer=TrivialSpecializer(), 
              filter_predicate=None):
    """REPL-like thing. Should be reusable.
    """

    def handle_debug():
        debugging = open('src/main/specializer_debug_output.txt', 'a')
        #debugging.truncate()
        specializer.set_debug()
        print("Debug mode is", specializer.debug_mode)
        return debugging

    def prompt():
        while True:
            ans = input('Command or q/Q to quit, d/D for Debug mode> ') # Python 3
            specialize = True
            if ans.lower() == 'd':
                specializer._output = handle_debug()
                specialize = False
            elif ans.lower() == 'names':
                solver.names()
                specialize = False
            if ans.lower() == 'q':
                return
                solver.close()
            elif ans.lower()== 'h':
                #backdoor test
                solver.test()
            #elif ans.split(" ")[0] == 'define':
            #    consolidate(ans.split(" ")[1], ans.replace(".", "").split(" ")[1:])
                #specializer._definitions[ans.split(" ")[1]] = ans  # consolidate, so: {'visit QL1': 'move to QL1 then return'}
            #    specialize = False
            elif ans and specialize: #ans != "d":
                specializer._sentence = ans
                try:
                    yield analyzer.parse(ans)#this is a generator
                except Fault as err:
                    """
                    try:
                        new = preProcess(ans)
                        if new:
                            yield analyzer.parse(preProcess(ans))
                        else:
                            raise Fault(-1, "No parses found for: '{0}'".format(ans))
                    except Fault as err:
                    """
                    print('Fault', err)
                    if err.faultString == 'compling.parser.ParserException':
                        print("No parses found for '%s'" % ans)


    """ Adds string definition to dictionary of definitions. """
    def consolidate(w, command):
        i = 0
        s = command
        while i < len(s):
            if s[i] == 'as':
                break
            i += 1
        n = ' '.join(s[:i])
        h = ' '.join(s[i + 1:])
        specializer._definitions[w] = [n, h]
        print(specializer._definitions)


    """ Processes string input (COMMAND), such as "Robot1, visit Box1", and replaces it with
    appropriate "parseable" string, such as "Robot1, move to Box1 and return". """
    def preProcess(command):
        punc = command[-1]
        words = command.replace("!", "").replace("?", "").replace(".", "").split(" ")
        s = copy.deepcopy(words)
        i = 0
        while i < len(words):
            if words[i] in specializer._definitions:
                words[i] = replaceCommand(words[i], words)
                # Replace with suitable object
                # Assemble new string
            i += 1
        print(words)
        #print(assembleString(words, punc))
        return "Robot1, move to the big red box!"
        #return assembleString(words, punc)

    """ Takes in an input command and replaces with proper string. Used in pre-Processing string."""
    def replaceCommand(word, words):
        d = ['QL1', 'QL2', 'QL3', 'QL4', 'QO1', 'QO2', 'QO3', 'QO4']
        key = specializer._definitions[word]
        if len(key[0].split(" ")) <= 1:
            return specializer._definitions[word][1]
        else:
            value = specializer._definitions[word][1]
            s = value.split(" ")
            print(s)
            print(words)
            for i in s:
                if i in d:
                    print(i)
        #return None

    """ Takes in a list of words and joins them into a string, with punctuation at the end. """
    def assembleString(words, punc):
        print(" ".join(words) + punc)
        return " ".join(words) + punc


    for analyses in prompt():
        for fs in filter(filter_predicate, analyses):
            try:
                #resolve = specializer.reference_resolution(fs)          
                ntuple = specializer.specialize(fs)
                json_ntuple = dumps(ntuple, cls=StructJSONEncoder, indent=2)
                if specializer.debug_mode:
                    sentence = specializer._sentence.replace(" ", "_").replace(",", "").replace("!", "").replace("?", "")
                    t = str(time.time())
                    generated = "src/main/json_tuples/" + sentence
                    f = open(generated, "w")
                    f.write(json_ntuple)
                #if specializer.needs_solve and ntuple != None:
                #    solver.solve(json_ntuple)
                
            except:
                print('Problem solving %s' % analyses)
                traceback.print_exc()
            break
        
def usage(args):
    print('Usage: %s [-s <problem solver>] [-a <all server URL>]' % basename(args[0]))
    sys.exit(-1)
    
    
if __name__ == '__main__':
    # These contain default values for the options
    options = {'-s': 'null', 
               '-a': 'http://localhost:8090'}
    options.update(dict(a.split() for a in sys.argv[1:] if a.startswith('-')))
               
    if not all(o[1] in 'sa' for (o, _) in options.items()):
        usage(sys.argv)
    
    solver = dict(null=MockProblemSolver, morse=MorseProblemSolver, xnet=XnetProblemSolver)
    main_loop(Analyzer(options['-a']), specializer=TrivialSpecializer(), solver=solver[options['-s']]())
    sys.exit(0)
