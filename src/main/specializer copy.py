"""
.. The Specalizer module gathers information from the SemSpec and 
    outputs an ntuple.

.. moduleauthor:: Luca Gilardi <lucag@icsi.berkeley.edu>

"""

import sys, traceback
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
# from pprint import pprint, pformat

def updated(d, *maps, **entries):
    """A "functional" version of update...
    """
    dd = dict(**d) if isinstance(d, dict) else Struct(d)
    return update(dd, *maps, **entries)

# This just defines the interface
class NullSpecializer(object):
    def specialize(self, fs): 
        """Specialize fs into task-specific structures.
        """
        abstract  # @UndefinedVariable

class TrivialSpecializer(NullSpecializer):
    def __init__(self):
        self._NTUPLE_T = dict(predicate_type=None,             
                              parameters=None, # one of (_execute, _query)                         
                              return_type='error_descriptor') 

        # Their types should be actually constrained.
        # We are supposed to have inserted the symbols; None means no default.
        self._execute = dict(kind='execute',  # XXX 
                             control_state='ongoing', 
                             action=None,
                             acted_upon=None,
                             distance=Struct(value=1, units='square'),
                             goal=None,
                             heading='north',
                             direction=None)
        
        self._query = dict(kind='query', 
                           subject=None, 
                           object=None, 
                           answer=None)

    def specialize(self, fs):
        """This method takes a SemSpec (the fs parameter) and outputs an n-tuple.
        
        This needs more than some cleaning.
        """
        def make_parameters():
            def params_for_simple(process):
                """Make parameters for a single process
                """
                if process.type() == 'MotionPath':
                    params = updated(self._execute,
                                     action=process.actionary.type(), 
                                     acted_upon=process.mover.referent.type())
                    # Is there a heading specified?
                    if process.heading.type():
                        params.update(heading=process.heading.tag.type())
                    # Is a distance specified?                
                    if hasattr(process.spg, 'distance') and hasattr(process.spg.distance, 'amount'):
                        d = process.spg.distance
                        params.update(distance=Struct(value=d.amount.value.value, units=d.units.type()))
                    # Is a goal specified?
                    if hasattr(process.spg, 'goal'):
                        params.update(goal=process.spg.goal) 
                    # Is a direction specified?
                    if hasattr(process, 'direction'):
                        params.update(direction=process.direction.type()) 
                    return params
                elif process.type() == 'StagedProcess':
                    params = updated(self._execute, 
                                     action=core.m.profiledProcess.actionary, 
                                     acted_upon=process.mover.referent.type())
                    if eventProcess.stageRole.type():
                        params.update(control_state=eventProcess.stageRole)
                    return params
        
            def params_for_compound(process):
                if process.type() == 'SerialProcess':
                    for pgen in chain(map(params_for_compound, (process.process1, process.process2))):
                        for p in pgen:
                            yield p
                else:
                    yield params_for_simple(process)

            core = fs.rootconstituent.core  # needed in params_for_simple(process)
            eventProcess = core.m.eventProcess
            allowed_types = dict(compound=['SerialProcess'],
                                 simple=['MotionPath', 'CauseMotionPathAction', 'StagedProcess'])
            t = eventProcess.type()
            assert t in flatten(allowed_types.values()), 'problem: process type is: %s' % t
            
            if t in allowed_types['simple']:
                return [params_for_simple(eventProcess)]
            else:
                return list(params_for_compound(eventProcess))
                        
            # TODO: Perhaps move this logic inside the relevant methods
            if t == 'MotionPath':
#                 print('eventProcess:', eventProcess)
                params = updated(self._execute,
                                 action=eventProcess.actionary.type(), 
                                 acted_upon=eventProcess.mover.referent.type())
                if eventProcess.heading.type():
                    params.update(heading=eventProcess.heading.tag.type())
                # Is a distance (with an amount) specified?                
                if hasattr(eventProcess.spg, 'distance') and hasattr(eventProcess.spg.distance, 'amount'): 
                    d = eventProcess.spg.distance
                    params.update(distance=Struct(value=d.amount.value.value, units=d.units.type()))
                # Is a goal is specified?
                if hasattr(eventProcess.spg, 'goal'):
                    params.update(goal=eventProcess.spg.goal) 
                return params
            elif t == 'StagedProcess':
                process = core.m.profiledProcess
                params = updated(self._execute, action=process.actionary, 
                                 acted_upon=process.mover.referent.type())
                if eventProcess.stageRole.type():
                    params.update(control_state=eventProcess.stageRole)
                return params

        mood = fs.m.mood.replace('-', '_')
        assert mood in ('YN_Question', 'WH_Question', 'Declarative', 'Imperative')

        # Dispatch call to some other spacialize_* methods.
        # Note: now paramters is a sequence.
        
        params = make_parameters()
        ntuple = updated(self._NTUPLE_T,
                         getattr(self, 'specialize_%s' % mood)(fs),
                         parameters=[Struct(param) for param in params])
        
        return Struct(ntuple)

    def specialize_YN_Question(self, fs):
        return dict(predicate_type='query', return_type='boolean')

    def specialize_WH_Question(self, fs):
        specific = fs.m.contents.profiledParticipant.specific
        f = 'collection_of' if fs.m.contents.profiledParticipant.number == '>1' else 'singleton'
        return dict(predicate_type='query',
                    return_type='%s(class_reference)' % f if specific == 'what' else '%s(instance_reference)' % f)

    def specialize_Declarative(self, fs):
        return dict(predicate_type='assertion', return_type='error_descriptor')

    def specialize_Imperative(self, fs):
        return dict(predicate_type='command', return_type='error_descriptor')

def main_loop(analyzer, solver=NullProblemSolver(), specializer=NullSpecializer(), filter_predicate=None):
    """REPL-like thing. Should be reusable.
    """
    def prompt():
        while True:
            ans = input('Command or q/Q to quit> ') # Python 3
#           ans = raw_input('Command or q/Q to quit> ') # Python 2
            if ans.lower() == 'q':
                solver.close()
                return
            elif ans:
                try:
                    yield analyzer.parse(ans)#this is a generator
                except Fault as err:
                    print('Fault', err)
                    if err.faultString == 'compling.parser.ParserException':
                        print("No parses found for '%s'" % ans)

    for analyses in prompt():
        for fs in filter(filter_predicate, analyses):
            try:
                ntuple = specializer.specialize(fs)
                json_ntuple = dumps(ntuple, cls=StructJSONEncoder, indent=2)
                # print(json_ntuple)
                solver.solve(json_ntuple)
            except:
                print('Problem solving %s' % analyses)
                traceback.print_exc()
            break
        
class Analyzer(object):
    """A proxy for the Analyzer. 
    Note: It assumes the server is running with the right grammar
    """
    def __init__(self, url):
        self.analyzer = ServerProxy(url) 
        
    def parse(self, sentence):        
        return [as_featurestruct(a) for a in self.analyzer.parse(sentence)]
    
def usage(args):
    print('Usage: %s [-s <problem solver>] [-a <analyzer server URL>]' % basename(args[0]))
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
