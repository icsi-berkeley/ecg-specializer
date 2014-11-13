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
from specializerTools import *
from solver2 import NullProblemSolver, MorseProblemSolver, XnetProblemSolver, MockProblemSolver, ClarificationError
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


class RobotSpecializer(UtilitySpecializer, TemplateSpecializer):
    def __init__(self):
        """ Inherits from UtilitySpecializer and TemplateSpecializer. """

        # This puts the Analyzer and _Stacked list into the Task-Specializer --> is there a cleaner way to do this?
        UtilitySpecializer.__init__(self)
        TemplateSpecializer.__init__(self)

        # Setting for printing N-tuples or not
        #self.debug_mode = False


        """ This is a dictionary meant to represent the maps between input words and their definitions.
        For example, "visit" could be a key, which triggers "Move to QL2 then return", etc.
        """
        self._definitions = dict()

        # Does it need to be solved? e.g., is it just a definition type? Defaults as True
        self.needs_solve = True

        # Past parameters
        self.parameters = None

    def specialize_np(self, fs, tagged, cue=None):
        """ This method takes an NP SemSpec specifically and puts it into an N-Tuple (the last N-Tuple). """
        replace = None
        if fs.m.type() == "HeadingSchema":
            new_od = fs.m.tag.type()
            replace = 'heading'  # Hack
        elif fs.m.type() == 'SPG':
            new_od = {'objectDescriptor': self.get_objectDescriptor(fs.m.landmark)}
            replace = 'goal'
            self._stacked.append(new_od)
        elif cue:
            new_od = {'objectDescriptor': self.get_objectDescriptor(fs.m)}
            self._stacked.append(new_od)
        else:
            new_od = self.resolve_anaphoricOne(fs.m)
            self._stacked.append(new_od)


        i = -1
        for param in tagged.parameters:
            i += 1
            p = param.__dict__
            copy = deepcopy(p)
            for key, value in p.items():
                if type(value) ==Struct:
                    p2 = value.__dict__
                    for k, v in p2.items():
                        if "*" in str(k):
                            temp = str(k).replace("*", "")
                            if (temp == 'heading' or temp == 'goal'): 
                                if temp == replace:
                                    p2[temp] = new_od
                                    #p2.pop(k)
                                    #copy[key] = Struct(p2)
                                else:
                                    p2[temp] = None
                            else:
                                p2[temp] = new_od
                                #p2.pop(k)
                                #copy[key] = Struct(p2)
                            p2.pop(k)
                            copy[key] = Struct(p2)
                elif "*" in str(key):
                    temp = str(key).replace("*", "")
                    p[temp] = p.pop(key)
                    copy[temp] = new_od
                    copy.pop(key)
                    #p[temp] = new_od

        tagged.parameters[i] = Struct(copy)
 


        """
        meaning = fs.m
        if meaning.ontological_category.type() == "antecedent":
            test = self.resolve_anaphoricOne(meaning)
            print(test)
        else:
            objectDescriptor = self.get_objectDescriptor(fs.m)
            print(objectDescriptor)

        """



        return tagged


    def specialize(self, fs):
        """This method takes a SemSpec (the fs parameter) and outputs an n-tuple.
        
        This needs more than some cleaning.
        """
        def make_parameters():

            # Returns parameters for Stasis type of process ("the box is red")
            def params_for_stasis(process, params):
                prop = process.state
                #params = updated(d, action = process.actionary.type()) #process.protagonist.ontological_category.type())
                if prop.type() == 'PropertyModifier':
                    a = {str(prop.property.type()): prop.value.type()}#, 'type': 'property'}
                    params.update(predication = a)
                elif prop.type() == 'TrajectorLandmark':
                    if prop.landmark.referent.type() == 'antecedent':
                        landmark = get_referent(process, params)
                    else:
                        landmark = self.get_objectDescriptor(prop.landmark)
                    pred = {'relation': self.get_locationDescriptor(prop.profiledArea), 'objectDescriptor': landmark}
                    #print(prop.profiledArea.ontological_category.type())
                    params.update(predication=pred)
                if not 'specificWh' in params:  # Check if it's a WH question, in which case we don't want to do "X-check"
                    params = crosscheck_params(params)
                return params                

 
            
            def params_for_motionPath(process, params):
                """ returns parameters for motion path process ("move to the box"). """
                if hasattr(process, 'actionary'):
                    params.update(action = process.actionary.type())
                if hasattr(process, 'speed') and str(process.speed) != "None":# and process.speed.type():
                    params.update(speed = float(process.speed))
                else:  # Might change this - "dash quickly" (what should be done here?)
                    s = self.get_actionDescriptor(process)
                    if s is not None:
                        params.update(speed = float(s))
                # Is there a heading specified?
                if hasattr(process, 'heading'):
                    if process.heading.type():
                        params.update(heading=process.heading.tag.type())
                # Is a distance specified?                
                if hasattr(process.spg, 'distance') and hasattr(process.spg.distance, 'amount'):
                    d = process.spg.distance
                    params.update(distance=Struct(value=int(d.amount.value), units=d.units.type()))
                # Is a goal specified?
                if hasattr(process.spg, 'goal'):
                    params.update(goal = get_goal(process.spg, params))
                if hasattr(process, 'direction'):
                    params.update(direction=process.direction.type())                 
                return params   

            # gets params for force-application, like "push the box"
            def params_for_forceapplication(process, params):
                """ Gets params for Force Application process. """
                if hasattr(process.actedUpon, 'referent'):
                    if process.actedUpon.ontological_category.type() == 'antecedent':
                        try:
                            affected = self.resolve_anaphoricOne(process.actedUpon)
                        except Exception:
                            print("No suitable 'one' found.")
                    elif process.actedUpon.referent.type() == "antecedent":
                        try:
                            affected = self.resolve_referents(actionary = params['action'])
                        except Exception:
                            print("Antecedent not found.")
                            return None
                    else:
                        if process.actedUpon.referent.type():
                            affected = {'objectDescriptor': {'referent': process.actedUpon.referent.type(), 'type': process.actedUpon.ontological_category.type()}}
                        else:
                            affected = {'objectDescriptor': self.get_objectDescriptor(process.actedUpon)}
                    self._stacked.append(affected)
                else:
                    affected = None
                params.update(acted_upon = affected)
                return params  

            def params_for_stagedprocess(process, d):
                params = updated(self._execute, 
                                 action=core.m.profiledProcess.actionary, 
                                 protagonist=process.mover.referent.type())
                if eventProcess.stageRole.type():
                    params.update(control_state=eventProcess.stageRole)
                return params              


            # Dispatches "process" to a function to fill in template, depending on process type. Returns parameters.
            def params_for_simple(process, template):
                if template == self._WH:
                    template['specificWh'] = process.protagonist.specificWh.type()
                    if template['specificWh'] == "where":
                        return params_for_where(process, template)
                processes = {'MotionPath': params_for_motionPath,
                             'Stasis': params_for_stasis,
                             'ForceApplication': params_for_forceapplication,
                             'StagedProcess': params_for_stagedprocess}
                params = updated(template, protagonist = get_protagonist(process),
                                 action = get_actionary(process))
                assert process.type() in processes, 'problem: process type not in allowed types'
                return processes[process.type()](process, params)

            def get_goal(process, params):
                """ Returns an object descriptor of the goal; used for SPG schemas, like in MotionPath."""
                g = process.goal
                goal = dict()
                if g.type() == 'home':
                    goal['location'] = g.type()
                elif g.ontological_category.type() == 'heading':
                    goal = None
                    params.update(heading=g.tag.type())
                elif g.ontological_category.type() == 'region':
                    goal['locationDescriptor'] = {'objectDescriptor': self.get_objectDescriptor(process.spg.landmark), 'relation': self.get_locationDescriptor(g)}
                elif self.analyzer.issubtype('ONTOLOGY', g.ontological_category.type(), 'part'): # checks if it's a "part" in a part whole relation
                    goal['partDescriptor'] = {'objectDescriptor': self.get_objectDescriptor(g.extensions.whole), 'relation': self.get_objectDescriptor(g)}
                elif g.ontological_category.type() == 'antecedent':
                    try:
                        goal = self.resolve_anaphoricOne(g)
                    except(Exception):
                        print("No suitable 'one' found.")
                elif g.referent.type():
                    if g.referent.type() == "antecedent":
                        try:
                            if g.givenness.type() == 'distinct':
                                goal = self.resolve_anaphoricOne(g)
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
                    goal['objectDescriptor'] = self.get_objectDescriptor(g) #properties
                    #goal.objectDescriptor['type'] = goal.type
                self._stacked.append(goal)
                return goal   

            def get_protagonist(process):
                """ Returns the protagonist of PROCESS. Checks to see what kind of referent / object it is. """
                if hasattr(process, "protagonist"):
                    if process.protagonist.ontological_category.type() == 'antecedent':
                        try:
                            subject = self.resolve_anaphoricOne(process.protagonist)
                        except Exception:
                            print("No suitable 'one' found.")
                    elif hasattr(process.protagonist, 'referent') and process.protagonist.referent.type() == "antecedent":
                        try:
                            subject = self.resolve_referents(get_actionary(process))
                        except(Exception):
                            print("Antecedent not found.")
                            return None
                    else:
                        subject = {'objectDescriptor': self.get_objectDescriptor(process.protagonist)}
                        if subject['objectDescriptor']['type'] != 'robot':
                            self._stacked.append(subject)
                    return subject
                return None

            def get_actionary(process):
                """ Returns the actionary of PROCESS. Checks to make sure actionary is contained in process. """
                if hasattr(process, "actionary"):
                    return process.actionary.type()
                elif process.type() == 'MotionPath':
                   return 'move'
                return None

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
                            p = {'objectDescriptor': {'referent': h.referent.type(), 'type': h.ontological_category.type()}}
                        else:
                            p = {'objectDescriptor': self.get_objectDescriptor(h)}
                        self._stacked.append(p)
                    params.update(protagonist=p)
                #p = process.protagonist
                return params
                    
            
            """ This is a temporary function to address a larger issue, which is:
            In sentences like "is the big box red?", the predication "red" points back to "box".
            Thus, in the self.get_objectDescriptor function, "red" becomes one of the modifier properties in
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
                    yield params_for_simple(process, self._execute)  # EXECUTE is default 


            def causalProcess(process):
                params = updated(self._cause, action = process.actionary.type())
                if hasattr(process.causalAgent, 'referent') and process.causalAgent.referent.type():
                    params.update(causer = {'objectDescriptor': self.get_objectDescriptor(process.causalAgent)}) # process.causalAgent.referent.type())
                else:
                    params.update(causer = self.get_objectDescriptor(process.causalAgent))
                #cp = params_for_compound(process.process1)
                cp = params_for_simple(process.process1, self._execute)
                ap = params_for_simple(process.process2, self._execute)
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
                if hasattr(process, 'mover') and process.mover.type() == 'ConjRD':
                    goal = eval_complexRD(process.mover)
                    for k in goal:
                        goals.append(self.get_objectDescriptor(k))
                j = 0
                for i in copy:
                    if 'action' in i and i['action'] == 'push_move':
                        i = map_complex_struct(i, goals, goals[j])   # Need to JUST pass in push_move ("i")
                    else:
                        for key, v in i.items():
                            if key == "protagonist":
                                i[key] = {'objectDescriptor': {'referent': core.m.profiledParticipant.referent.type(), 'type': core.m.profiledParticipant.ontological_category.type()}}
                                #i[key] = process.profiledParticipant.referent.type()
                            if key == "goal":
                                if 'objectDescriptor' in v and 'referent' in v['objectDescriptor'] and v['objectDescriptor']['referent'] == 'variable':
                                    if process.mover.type() == 'ConjRD': #core.m.profiledProcess.mover.type() == 'ConjRD':
                                        i[key] = {'objectDescriptor': goals[j]}
                                    else:
                                        i[key] = {'objectDescriptor': self.get_objectDescriptor(process.mover)}#core.m.profiledProcess.mover)}
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
                        params[key] = {'objectDescriptor': self.get_objectDescriptor(core.m.profiledParticipant)}
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
                                        mini_dict[k] = {'objectDescriptor': self.get_objectDescriptor(core.m.profiledProcess.mover)}  # FIX THIS
                            if k == 'goal' and mini_dict[k] != None:
                                if 'referent' in v and v['referent'] == 'variable':
                                    if core.m.profiledProcess.mover.type() == 'ConjRD':
                                        mini_dict[k] = {'objectDescriptor': goals[j]}
                                    else:
                                        mini_dict[k] = {'objectDescriptor': self.get_objectDescriptor(core.m.profiledProcess.mover)}  # FIX THIS

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



            # Fix this?
            def attempt_mapping(c):
                actionary = c.profiledProcess.actionary.type()
                if actionary in self._definitions:
                    p = map_definitions(actionary, c.profiledProcess)
                    return p

            self.needs_solve = True
            core = fs.rootconstituent.core 
            f = None

            try:
                f = attempt_mapping(core.m)
            except Exception as e:
                None
            
            if f:
                return f

            
            def construct_YN():
                params = [params_for_simple(core.m.eventProcess, self._YN)]
                return params 

            def construct_WH():
                params = [params_for_simple(core.m.eventProcess, self._WH)]
                return params

            def construct_Declarative():
                params = [params_for_simple(core.m.eventProcess, self._assertion)]
                return params

            def construct_Imperative():
                allowed_types = dict(compound=['SerialProcess', 'CauseEffect'],
                                     simple=['MotionPath', 'CauseMotionPathAction', 'StagedProcess', 'Stasis'])
                t = eventProcess.type()
                assert t in flatten(allowed_types.values()), 'problem: process type is: %s' % t
                if t in allowed_types['simple']:
                    return [params_for_simple(eventProcess, self._execute)]
                else:
                    return list(params_for_compound(eventProcess))

            """ This logic all needs to be fixed up in a better evaluating loop. Should constantly
            run "compound process" to check if serial or causal process. Can't assume it's a simple prcoess. """
            def construct_condImp():
                cond = list(params_for_compound(core.m.ed1.eventProcess)) # Changed so that condition can be compound / cause ("If you pushed the box North, then...")
                params = updated(self._YN)
                action = list(params_for_compound(core.m.ed2.eventProcess)) #params_for_compound(core.m.ed1.eventProcess)
                action2 = []
                cond2 = []
                if cond is None or None in action:
                    return None
                for i in action:
                    action2.append(Struct(i))
                for i in cond:
                    cond2.append(Struct(i)) 
                params = [updated(self._conditional, command=action2, condition=cond2)]
                return params 
                    
            def construct_Definition():
                self.needs_solve = False
                a = core.m.sign.actionary.type()
                b = core.m.signified
                key = b.eventProcess.actionary.type()
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

        self.parameters = params

        if self.debug_mode:
            print(Struct(ntuple))
            dumpfile = open('src/main/pickled.p', 'ab')
            pickle.dump(Struct(ntuple), dumpfile)
            dumpfile.close()
            #dumpfile2 = open('src/main/move')
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


def main_loop(analyzer, solver=NullProblemSolver(), specializer=RobotSpecializer(), 
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
                solver.test()
            elif ans and specialize:
                specializer._sentence = ans
                try:
                    yield analyzer.parse(ans)#this is a generator
                except Fault as err:
                    print('Fault', err)
                    if err.faultString == 'compling.parser.ParserException':
                        print("No parses found for '%s'" % ans)

    def write_file():
        sentence = specializer._sentence.replace(" ", "_").replace(",", "").replace("!", "").replace("?", "")
        t = str(time.time())
        generated = "src/main/json_tuples/" + sentence
        f = open(generated, "w")
        f.write(json_ntuple)

    for analyses in prompt():
        for fs in filter(filter_predicate, analyses):
            try:
                #resolve = specializer.reference_resolution(fs)          
                ntuple = specializer.specialize(fs)
                json_ntuple = dumps(ntuple, cls=StructJSONEncoder, indent=2)
                if specializer.debug_mode:
                    write_file()
                if specializer.needs_solve and ntuple != None:
                    while True:
                        try:
                            solver.solve(json_ntuple)
                            break
                        except ClarificationError as ce:
                            new_input = input(ce.message + " > ")
                            specialized = specializer.specialize_np(analyzer.parse(new_input)[0], ce.ntuple, ce.cue) 
                            json_ntuple = dumps(specialized, cls=StructJSONEncoder, indent=2)
                            #solver.solve(json_ntuple)
                
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
    main_loop(Analyzer(options['-a']), specializer=RobotSpecializer(), solver=solver[options['-s']]())
    sys.exit(0)
