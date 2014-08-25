"""
.. The Problem Solvers (for various kinds of simulators), i.e. the object 
    that drives the robot, given a message (ntuple) prepared by the 
    :mod:`specializer` module.
  
.. moduleauthor:: Luca Gilardi <lucag@icsi.berkeley.edu>

"""
from __future__ import print_function

from json import loads
from pprint import pprint
from socket import socket
import struct  

from builder import build
from feature import StructJSONEncoder
from utils import update, vector_mul, vector_add, Struct
debug =1

class ProblemSolver(object):
    """Base for all problem solvers.
    """
    def solve(self, ntuple):
        abstract  # @UndefinedVariable

class NullProblemSolver(ProblemSolver):
    def solve(self, ntuple):
        pprint(ntuple, width=72)
        
    def close(self):
        pass

class DispatchingProblemSolver(ProblemSolver):
    """A trivial problem solver.
    """
#     def __init__(self, simulator):
#         self.simulator = simulator

    def solve(self, json_ntuple):
        """Decode the ntuple and dispatch the call.
        """
        #print('JSON-encoded ntuple to solve:', json_ntuple, sep='\n')
        ntuple = loads(json_ntuple, object_hook=StructJSONEncoder.as_struct)
        try:
            dispatch = getattr(self, 'solve_%s' % ntuple.parameters[0].action)
            dispatch(ntuple)
        except AttributeError:
            pprint(ntuple)
            raise
        
class MockProblemSolver(DispatchingProblemSolver):
    """A mock solver, for testing without a simulator.
    """
    def __init__(self, **kw):
        update(self, world=build('mock'))

    # Versors for the four directions
    headings = dict(north=(0.0, 1.0, 0.0), south=(0.0, -1.0, 0.0), east=(1.0, 0.0, 0.0), west=(-1.0, 0.0, 0.0)) 
    
    @staticmethod
    def getpos(instance):
        p = instance.pos
        return (p.x, p.y, p.z)    

    @staticmethod
    def setpos(instance, v):
        instance.pos = pos = Struct(x=v[0], y=v[1], z=v[2])
        return pos

    def solve_move(self, ntuple):
        print('mock solver: begin move')
        world = self.world
        home_pos = world.robot1_instance.pos
        for parameters in ntuple.parameters:
            acted_upon = parameters.acted_upon
            heading = parameters.heading
            direction = parameters.direction
            goal = parameters.goal
            inst = getattr(world, acted_upon)
            if goal:
                # TODO: super/subtype relations missing!
                if goal.ontological_category.type() == 'location':
                    print('|  move(x={x}, y={y}, z=0.0)'.format(x=goal.xCoord, y=goal.yCoord))
                    self.setpos(inst, (float(goal.xCoord), float(goal.yCoord), 0.0))    
                else:
                    # We assume it's an object, like a box or a block
                    obj = getattr(world, goal.referent.type())
                    print('|  move(x={x}, y={y}, z={z})'.format(x=obj.pos.x, y=obj.pos.y, z=obj.pos.z))
                    self.setpos(inst, (obj.pos.x, obj.pos.y, obj.pos.z))    
            elif direction == 'home':
                print('|  move(x={x}, y={y}, z=0.0)'.format(x=home_pos.x, y=home_pos.y))
                self.setpos(inst, (home_pos.x, home_pos.y, home_pos.z))    
            elif heading:
                n = float(parameters.distance.value)
                pos = self.getpos(inst)
                newpos = vector_add(pos, vector_mul(n, self.headings[heading]))
                print('|  move(x={0[0]}, y={0[1]}, z={0[2]})'.format(newpos))
                self.setpos(inst, newpos)
        print('mock solver: end move')        
        
    def close(self):
        # No op.
        pass

class MorseProblemSolver(DispatchingProblemSolver):
    """Trivial problem solver for a Morse object.
    """
    def __init__(self, **kw):
        update(self, world=build('morse'))
        
    def solve_walk(self, ntuple):
        print('walk:', ntuple)
    
    headings = dict(north=(0.0, 1.0, 0.0), south=(0.0, -1.0, 0.0), 
                    east=(1.0, 0.0, 0.0), west=(-1.0, 0.0, 0.0))

    @staticmethod
    def getpos(instance):
        p = instance.pos
        return (p.x, p.y, p.z)    

    def solve_move(self, ntuple):
        world = self.world
        home_pos = world.robot1_instance.pos
        print('solver: begin move_to_destination')
        if debug: print(len(ntuple.parameters))
        for parameters in ntuple.parameters:
            if debug: print(parameters)
            acted_upon = parameters.acted_upon
            heading = parameters.heading
            goal = parameters.goal
            direction = parameters.direction
            inst = getattr(self.world, acted_upon)

            if goal:
                # TODO: super/subtype relations missing!
                if debug: print("goal is")
                if debug: print(goal)
                if goal.ontological_category.type() == 'location':
                    inst.move(x=float(goal.xCoord), y=float(goal.yCoord), z=0.0)    
                else:
                    # We assume it's an object, like a box or a block
                    if debug: print("self.world")
                    if debug: print(self.world)
                    if debug: print("goal.referent.type()")
                    if debug: print(goal.referent.type())
                    obj = getattr(self.world, goal.referent.type())
                    if debug: print("obj is")
                    if debug: print(obj)
                    if debug: print("color type is")
                    if debug: print (goal.extensions.boundedObject)

                    #if debug: print (goal.extensions.property.ontological_category.type())
                    #color = getattr(self.world, goal.extensions.property.ontological_category.type())
                    inst.move(x=obj.pos.x, y=obj.pos.y, z=obj.pos.z)
            elif direction == 'home':
##                print('|  move(x={x}, y={y}, z=0.0)'.format(x=home_pos.x, y=home_pos.y))
                inst.move(x=home_pos.x, y=home_pos.y, z=home_pos.z)
            elif heading:
                n = float(parameters.distance.value)
                pos = self.getpos(inst)
                newpos = vector_add(pos, vector_mul(n, self.headings[heading]))
                inst.move(x=newpos[0], y=newpos[1], z=newpos[2])
        print('solver: end move_to_destination')
    
    def solve_step(self, ntuple):
        print('step:', ntuple)
        
    def close(self):
        self.world.robot1_instance.close()

class XnetProblemSolver(ProblemSolver):
    """Sends problem to hard-coded xnet robot.xml 
    """
    def __init__(self):
        self.sock = socket()
        self.sock.connect(('localhost', 4040))

    def writeUTF(self, data, strng):
        utf8 = strng.encode('utf-8')
        length = len(utf8)
        data.append(struct.pack('!H', length))
        pack_format = '!' + str(length) + 's'
        data.append(struct.pack(pack_format, utf8))  

    def solve(self, ntuple):
        data = []
        self.writeUTF(data, ntuple)
        msgbytes = b"".join(data)
        self.sock.sendall(msgbytes)  
          
    def close(self):
        self.sock.close() 
