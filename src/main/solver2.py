"""
.. The Problem Solvers (for various kinds of simulators), i.e. the object 
    that drives the robot, given a message (ntuple) prepared by the 
    :mod:`specializer` module.
  
.. moduleauthor:: Luca Gilardi <lucag@icsi.berkeley.edu>

"""
from __future__ import print_function
import pickle
import json
from json import loads
from pprint import pprint
from socket import socket
from pprint import pprint
import random
  

from builder import build
from feature import StructJSONEncoder
from utils import update, vector_mul, vector_add, Struct
from math import sqrt
import sys
debug =0

"""A function to unpack the N-tuples from a file (for the purposes of testing the Solver).
Returns a list of all the Structs after decoding them. Assumes you're passing in a file
with pickled structs.  7/16/14 (ST)
"""
#f = open("src/main/pickled.p", "rb") # file "f" contains all the pickled structs
def unpack_pickles(f):
    returned = []
    while 1:
        try:
            item = pickle.load(f)
            #ntuple = loads(item, object_hook=StructJSONEncoder.as_struct)
            #kind = item.parameters.kind
            #returned[kind] = item
            returned.append(item)
        except EOFError:
            print("Reached end of file - list complete.")
            break
    return returned

""" Takes in a file with a JSON object, returns a Struct to pass into Solver. """
def json_to_struct(f):
    #fileStuff = open(f)
    data = json.load(f)
    temp = json.dumps(data)
    n = loads(json.dumps(data), object_hook=StructJSONEncoder.as_struct)
    return n


class ClarificationError(Exception):
    def __init__(self, message, ntuple, cue=None):
        self.message = message
        self.ntuple = ntuple
        self.cue=cue

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

    _return_type = None

    ntuple = None

    _wh = None

    def solve(self, json_ntuple):
        """Decode the ntuple and dispatch the call.
        """
        #print('JSON-encoded ntuple to solve:', json_ntuple, sep='\n')
        ntuple = loads(json_ntuple, object_hook=StructJSONEncoder.as_struct)
        self.ntuple = ntuple
        self._return_type = ntuple.return_type
        try:
            self.home_pos = self.world.robot1_instance.pos
            if (hasattr(ntuple, "predicate_type") and ntuple.predicate_type =="conditional"):
                 dispatch = getattr(self, 'solve_%s' % "conditional")
                 dispatch(ntuple)
            else:  
                for p in ntuple.parameters:
                    dispatch = getattr(self, 'solve_%s' % p.action)
                    dispatch(p)
            #dispatch(ntuple)
        except AttributeError:
            pprint(ntuple)
            raise

    #dispatch based on ntuple, should be inner fn for solve...
    def solve_ntuple (self,ntuple):
            try:
                if (hasattr(ntuple, "predicate_type") and ntuple.predicate_type =="conditional"):
                     dispatch = getattr(self, 'solve_%s' % "conditional")
                else:
                    for p in ntuple.parameters:    
                        dispatch = getattr(self, 'solve_%s' % p.action)
                        dispatch(p)
            except AttributeError:
                pprint(ntuple)
                raise


class RobotProblemSolver(DispatchingProblemSolver):
    """Trivial problem solver for a Morse object.
    """
    #def __init__(self, **kw):
    #    update(self, world=build('morse'))
        
    def solve_walk(self, ntuple):
        print('walk:', ntuple)
    
    headings = dict(north=(0.0, 1.0, 0.0), south=(0.0, -1.0, 0.0), 
                    east=(1.0, 0.0, 0.0), west=(-1.0, 0.0, 0.0))


    _recent = None

    # Lists names and attributes of all the objects in the world (besides Robot1)
    def names(self):
        for i in self.world:
            obj = getattr(self.world, i)
            if i != "robot1_instance":
                n = obj.name.split("_")[0]
                a = n[0].upper() + n[1:]
                print("{0} is of type {1}, with a color of {2} and a size of {3}.".format(a, obj.type, obj.color, obj.size))
    

    def test(self):
        obj =  getattr(self.world, 'box1_instance')
        ref =  getattr(self.world, 'robot1_instance')
        loc = self.behind( obj, ref)
        self.move(ref, loc[0], loc[1])

        pass
     #takes in a list of objects, and returns the biggest
    def getbiggest(self, instances):
        size = float('-inf')
        big = None
        for i in instances:
            if float(i.size) > size:
                big = i
                size = i.size
        return big

    #takes in a list of objects, and returns the smallest
    def getsmallest(self, instances):
        size = float('inf')
        small = None
        for i in instances:
            if float(i.size) < size:
                size = i.size
                small = i
        return small

    def solve_dash(self, ntuple):
        self.solve_move(ntuple)

    def solve_crawl(self, ntuple):
        self.solve_move(ntuple)


    def solve_move(self, parameters):
        color = None
        size = None
        world = self.world
        print('solver: begin move_to_destination')
        #for parameters in ntuple.parameters:
        protagonist = self.get_described_obj(parameters.protagonist['objectDescriptor'])
        speed = parameters.speed * 6
        heading = parameters.heading
        goal = parameters.goal
        direction = parameters.direction
        inst =protagonist 
        #getattr(self.world, protagonist)
        if goal:
            # TODO: super/subtype relations missing!
#             print(goal)
            if 'location' in goal:
                #inst.move(x=float(goal['location'][0]), y=float(goal['location'][1]), z=0.0)
                if goal['location'] == 'home':
                    self.move(inst, self.home_pos.x, self.home_pos.y, self.home_pos.z, tolerance= 2, speed=speed) 
                else:
                    self.move(inst,float(goal['location'][0]), float(goal['location'][1]), 0.0, speed=speed) 

            elif goal == 'home':
                self.move(inst, home_pos.x, home_pos.y, home_pos.z, speed=speed)    
            elif 'referent' in goal:
                obj = getattr(self.world, goal['referent']) 
                #inst.move(x=obj.pos.x, y=obj.pos.y, z=obj.pos.z)
                self.move(inst, obj.pos.x, obj.pos.y, obj.pos.z, speed=speed)
            elif ('partDescriptor' in goal):
                if goal['partDescriptor']['relation']['type'] == 'side':
                    loc = self.get_described_part_pos(goal['partDescriptor'],inst)
                    if (loc):
                        self.move(inst, loc[0], loc[1], tolerance= 2, speed=speed)
            else:
                if ('objectDescriptor') in goal: 
                    properties = goal['objectDescriptor']
                    obj = self.get_described_obj(properties, multiple=True)
                    if (obj):
                        self.move(inst, obj.pos.x, obj.pos.y, obj.pos.z, speed=speed)         
                elif ('locationDescriptor') in goal:
                    properties = goal['locationDescriptor']
                    loc = self.get_described_loc_pos(properties,getattr(self.world, inst))
                    if (loc):
                        self.move(inst, loc[0], loc[1], speed=speed)    
        elif heading:
            n = float(parameters.distance.value)
            print(inst)
            name = getattr(inst, 'name')
            #pos = getattr(inst, 'pos') #self.getpos(inst)
            pos = self.getpos(name)
            newpos = vector_add(pos, vector_mul(n, self.headings[heading]))
            self.move(inst, newpos[0], newpos[1], newpos[2], speed=speed)
        print('solver: end move_to_destination')

    def solve_push_move(self, parameters):
        color = None
        size = None
        world = self.world
        home_pos = world.robot1_instance.pos
        print('solver: begin move_to_destination')
        #for parameters in ntuple.parameters:
        protagonist = self.get_described_obj(parameters.causer['objectDescriptor'])
        heading = parameters.affectedProcess.heading
        goal = parameters.affectedProcess.goal
        distance = parameters.affectedProcess.distance.value 
        inst =protagonist
        if parameters.causalProcess.acted_upon == None:
            tag = ['acted_upon']
            tagged = self.tag_ntuple(properties='', ntuple=self.ntuple, tag=tag)
            raise ClarificationError(message="push what?", ntuple=tagged, cue=True)


        obj = self.get_described_obj(parameters.causalProcess.acted_upon['objectDescriptor'])
        if goal:
            print("Not yet supported. Try pushing a box in a direction.")
        elif heading:
            n = float(distance)
            self.push_direction(heading, inst, obj, n)

        else:
            tag = ['heading', 'goal']
            tagged = self.tag_ntuple(properties='', ntuple=self.ntuple, tag=tag)
            raise ClarificationError(message="push it where?", ntuple=tagged)

    def push_direction(self, heading, inst, obj, n):
        """ Pushes in a certain direction. Used to simplify "solve push move" function. """
        addpos = vector_mul(-6, self.headings[heading])
        self.move_precise(inst, obj.pos.x + addpos[0], obj.pos.y + addpos[1])
        addpos = vector_mul(-3, self.headings[heading])
        self.move_push(inst, obj.pos.x + addpos[0], obj.pos.y + addpos[1], 2)

        #this is the part where it actually pushes forward. I think to make it right, you would need to repalce the following line:
        #addpos = vector_mul(4, self.headings[heading])

        #with this line
        addpos = vector_mul(n, self.headings[heading])

        self.move_push(inst, obj.pos.x + addpos[0], obj.pos.y + addpos[1],2 )



    #needs to be fixed, currently just returns the first conditional...
    def evaluate_condition(self, parameters):
        #params =params
        #for parameters in params:
        protagonist = parameters.protagonist
        predication = parameters.predication
        if ('referent' in protagonist.keys()):
            item = getattr(self.world, protagonist['referent'])
        else: 
            item = self.get_described_obj(protagonist['objectDescriptor'])
            if (item == None):
                return False
        return self.eval_condtion_one_item(item, predication)
        
    
    def eval_condtion_one_item(self, item, prediction):
        predictions = list(prediction.keys())
        for pred_prop in predictions:
            if ('relation' in prediction):
                if prediction['relation'] =='near':
                    item2 = self.get_described_obj(prediction['objectDescriptor'])
                    if not (self.is_near(item, self.get_described_obj(prediction['objectDescriptor']))):
                        print ("items are not near") 
                        return False
                    else:
                        return True
                        #print ("items are near") 
            elif not( hasattr(item, pred_prop)):
                #print ( "item does not have the " + pred_prop + " property" )
                return False
            elif not( getattr(item, pred_prop) == prediction [pred_prop]):
                #print ("item is not " + prediction [pred_prop] )
                return False
            #else:
                #print ("item is " + prediction [pred_prop] )
        return True

    def solve_conditional(self, ntuple):
        # Need to call just parameters.condition
        if (self.evaluate_condition(ntuple.parameters[0].condition[0])):  # Changed to index into complex condition, might need to fine-tune later
            self.solve_ntuple(Struct(parameters =ntuple.parameters[0].command))
        

    def solve_be2(self, parameters):
        if self.evaluate_condition(parameters):
            print("yes")
        else:
            print("no")
        #return self.evaluate_condition(parameters)
        #return self.evaluate_condition( ntuple.parameters)

    def solve_be(self, parameters):
        if hasattr(parameters, 'specificWh'):
            return self.eval_wh(parameters, self._return_type) #ntuple.return_type)
        return self.evaluate_condition(parameters)


    def eval_which(self, params, num, referentType):
        self._wh = True
        if num == 'singleton':
            obj = self.get_described_obj(params.protagonist['objectDescriptor'])
            if obj is not None:
                print(obj.name)
            self._wh = False
            return obj
        else:
            objs = self.get_described_objects(params.protagonist['objectDescriptor'], multiple=True)
            if type(objs[0]) == list:
                for i in objs[0]:
                    print(i.name)
            else:
                for i in objs:
                    print(i.name)
            self._wh = False

    def eval_what(self, params, num, referentType):
        return None

    def eval_where(self, params, num, referentType):
        p = params.protagonist
        if 'objectDescriptor' in p:
            p = p['objectDescriptor']
        obj = self.get_described_obj(p, multiple=True)
        if obj is not None:
            print('x:{0}, y:{1}'.format(obj.pos.x, obj.pos.y))
            return obj.pos

    # Evalutes "wh" question, like "which box is red?"  7/30/14 (ST)
    def eval_wh(self, params, returnType):
        num, referentType = returnType.split('(')
        referentType = referentType[0:-1]
        wh = params.specificWh
        whSpace = {'which': self.eval_which,
                   'what': self.eval_what,
                   'where': self.eval_where}
        return whSpace[wh](params, num, referentType)


    #takes in an location descriptor, and returns the location that matches the description
    def get_described_loc_pos(self, properties, protagonist= None):
        obj = self.get_described_obj(properties['objectDescriptor'])
        if properties['relation']=='behind':
            return self.behind( obj, protagonist)
        else:
            print (properties['relation'])

    #returns the location of the correpsoing part
    def get_described_part_pos(self,partDescription,protagonist= None):
        obj = self.get_described_obj(partDescription['objectDescriptor'])

        if (partDescription['relation']['side']=='north'):
            x = obj.pos.x 
            y = obj.pos.y +3
        elif (partDescription['relation']['side']=='east'):
            x = obj.pos.x +3
            y = obj.pos.y 
        elif (partDescription['relation']['side']=='south'):
            x = obj.pos.x 
            y = obj.pos.y -3
        elif (partDescription['relation']['side']=='west'):
            x = obj.pos.x -3
            y = obj.pos.y 
        else:
            print("problem: that type of description is not yet supported")
            return 
        #print ('the box is at:')
        #print (obj.pos )
        #print ('robot is going to:')
        #print (x,y)
        return (x,y)



    #returns the nearest box (within the threshold) 
    def get_near(self, candidates, protagonist= None):
        distance_threashold = 10
        locations = []
        for candidate in candidates:
                dist = self.distance(candidate, protagonist)
                if dist <= distance_threashold and dist >0:
                    locations += [candidate]
                    #distance_threashold = self.distance(candidate, protagonist)
        return locations

    def is_near(self, a, b):
        distance_threashold = 10
        return self.distance(a, b) <=distance_threashold

    def is_behind(self, object, reference):
        return 

    def get_described_locations(self, candidates, properties, protagonist=None):
        obj = self.get_described_obj(properties['objectDescriptor'])
        locations = []#the candiates that satisfy the properites
        if properties['relation']=='near':
            locations =  self.get_near(candidates, protagonist)
        if properties['relation']=='behind':
            return self.behind( obj, protagonist)
        return locations

    #takes in a list of candidate object, a location descriptor, and returns the object that matches the description
    def get_described_loc(self, candidates, properties, protagonist= None, multiple=False):
        locations = self.get_described_locations(candidates, properties, protagonist)
        if multiple:
            return locations
        if len(locations)> 1:
            print('Problem: there is more than one object that matches that description. Please be more specific.')
            return None
        elif len(locations)== 0:
            print('Problem: there is no object that matches that description. Please try again.')
            return None
        else:
            return locations[0]

    def get_described_objects(self, properties, protagonist=None, multiple=False):
        objs = []
        if 'referent' in properties:
            return [getattr(self.world, properties['referent'])]
        obj_type = properties["type"]
        if 'color' in properties:#deal with color
            color = properties['color']
            for item in self.world.__dict__.keys(): #gets all the items in the world. 
                if hasattr(getattr(self.world, item), 'color')and getattr(getattr(self.world, item), 'color')==color and getattr(getattr(self.world, item), 'type') == obj_type:
                    objs += [getattr(self.world, item)]
        else: 
            for item in self.world.__dict__.keys(): #gets all the boxes in the world. 
                if hasattr(getattr(self.world, item), 'type') and getattr(getattr(self.world, item), 'type') == obj_type:
                    objs += [getattr(self.world, item)]
        if 'size' in properties:
            size = properties['size']
            if size[0].lower() == 's':
                return [self.getsmallest(objs)]
            elif size[0].lower() == 'b':
                return [self.getbiggest(objs)]
        if 'locationDescriptor' in properties:
            if protagonist is None:
                objs = self.get_described_loc(objs, properties['locationDescriptor'], self.get_described_obj(properties['locationDescriptor']['objectDescriptor']), multiple=multiple)
            else:
                objs = self.get_described_loc(objs, properties['locationDescriptor'], protagonist, multiple=multiple)
            if not type(objs) == list:
                objs = [objs]
        return objs

    #takes in an object descriptor, and returns the object that matches the description
    #if noobject is found, or multiple objects are found, returns none and prints and error
    def get_described_obj(self, properties, protagonist= None, multiple=False):   
        objs = self.get_described_objects(properties, protagonist, multiple)
        if len(objs) == 1:
            self._recent = objs[0]
            return objs[0]
        elif len(objs) >1:
            if 'givenness' in properties:
                if properties['givenness'] == 'typeIdentifiable':
                    return random.choice(objs)
                if properties['givenness'] == 'distinct':
                    if self._recent in objs:
                        objs.remove(self._recent)
                    return random.choice(objs) # Should return random object but not most recent one
            if self._wh:
                print("More than one object matches that description.")
                self._wh = False
                return None
            message = self.assemble_string(properties)
            tagged = self.tag_ntuple({'objectDescriptor': properties}, self.ntuple)
            raise ClarificationError(message, tagged)
            return None
        else:
            print('Problem: that item does not exist')
            return None

    def tag_ntuple(self, properties, ntuple, tag=[]):
        """ Takes in properties and tags the ntuple where these properties occur. """
        p = ntuple.parameters
        for param in ntuple.parameters:
            p = param.__dict__
            for key, value in p.items():
                if type(value) == Struct:
                    p2 = value.__dict__
                    for k, v in p2.items():
                        if v == properties or k in tag:
                            temp = "*" + str(k)
                            p2[temp] = p2.pop(k)
                elif value == properties or key in tag:
                    temp = "*" + str(key)
                    p[temp] = p.pop(key)
                """
                elif type(value) == dict and self.search_ntuple(properties, value):
                    print("this is it")
                    temp = "*" + str(key)
                """

        return ntuple

    def search_ntuple(self, properties, descriptor):
        """ Searches a value in a "descriptor" dictionary (which is itself a dictionary) if it contains "properties". Does a deep search. """
        for key, value in descriptor.items():
            if value == properties['objectDescriptor']:   # Hack, address later
                return True
            elif type(value) == dict:
                return self.search_ntuple(properties,value)
        return False


    def assemble_string(self, properties):
        """ Takes in properties and assembles a string, to format: "which blue box", etc. """
        ont = properties['type']
        attributes = ""
        for key, value in properties.items():   # Creates string of properties
            if key == "color" or key == "size":
                attributes += " " + value 
        return "which" + str(attributes) + " " + str(ont) + "?"


    def move_precise(self,inst,a, b, c=0, tolerance=2, speed=1.5):
        self.move(inst,a, b, c,tolerance,  speed)

    def move_push(self,inst,a, b, c=0, tolerance=2, speed=1.5):
        self.move(inst,a, b, c,tolerance,  speed, True)

    
    #given an object, and a reference point, returns the 'behind' of the object
    def behind(self, object, reference):
        obj = object.pos
        ref = reference.pos
        xdiff = obj.x- ref.x
        ydiff = obj.y - ref.y
        if abs(xdiff) > abs(ydiff):
            if xdiff>0:
                new = (obj.x +3, obj.y)
            elif xdiff<0:
                new = (obj.x -3, obj.y)
        elif abs(xdiff) < abs(ydiff):
            if ydiff>0:
                new = (obj.x, obj.y+3)
            elif ydiff<0:
                new = (obj.x , obj.y-3)
        elif abs(xdiff) == abs(ydiff):
            if ydiff>0:
                newy =  obj.y+3
            elif ydiff<0:
                newy = obj.y-3
            if xdiff>0:
                newx =  obj.x+3
            elif xdiff<0:
                newx = obj.x-3
            new = (newx, newy)
        #print (obj)
        #print (ref)
        #print (new)
        return new
    #return the euclidian distance between location a and b
    def distance(self, a, b):
        return sqrt(pow((a.pos.x-b.pos.x ),2) + pow((a.pos.y-b.pos.y ),2) ) 

    def solve_step(self, ntuple):
        print('step:', ntuple)
        
    def close(self):
        self.world.robot1_instance.close()

class MockProblemSolver(RobotProblemSolver):
    def __init__(self, **kw):
        update(self, world=build('mock'))
        self.home_pos = self.world.robot1_instance.pos

    def getpos(self, inst):
        p = getattr(getattr(self.world, inst), 'pos')
        return (p.x, p.y, p.z) 

    def move(self,inst,a, b, c=0, tolerance=2, speed=1.5, collide = False):#tolerance=1.5, speed=2.0):
        print("the world was:")   
        pprint(self.world)     
 
        print("robot is at:")
        print(a,b)
        #(self.world.) 
        setattr(inst, 'pos',Struct(x =a, y=b, z =c ))

        print("the world is now:")   
        pprint(self.world)

    
 
class MorseProblemSolver(RobotProblemSolver):
    def __init__(self, **kw):
        update(self, world=build('morse'))
        home_pos = self.world.robot1_instance.pos

    #ax, ay are start location bx by are end location
    #returns True if there is an obstacle in the path
    def is_obstacle_in_path(self, ax, ay, bx, by ):
        collide = []
        slope = (1.0*(ay - by))/(ax - bx+.00001)

        # #loop though objects, to check for interesction
        for obj in self.world:
            if not (obj == 'robot1_instance'):
                #print (obj)
                #print((getattr(self.world, obj)))
                x = (getattr(self.world, obj)).pos.x
                y = (getattr(self.world, obj)).pos.y
                if (x < max(ax, bx))and (x > min(ax, bx)) and (y < max(ay, by))and (y > min(ay, by))and (y -( slope*(x - ax) + ay) < 4):# this is the avoidance threshhold. should be based on footprint...
                    #print ("collision")
                    
                    collide += [(x+5,y)]
                #else:
                    #print ("ok")
            #setattr(getattr(self.world, obj['name']), 'pos',Struct(x =obj['position'][0], y=obj['position'][1], z =obj['position'][2]) )
        return collide
        # #loop though values beween the poins to check for collisions
        # x = min(ax, bx) +1
        # while x < max (ax, bx)
        #     y = m(x – ax) + ay
        #     #check if that is a problem in data struct

        # if ax == bx:
        #     y = min(ay, by) +1
        #     while y < max (ay, by):
        #         x = ax
        #          #check if that is a problem in data struct

    #ax, ay are start location bx by are end location
    def avoid_obstacle(self, ax, ay, bx, by):
        obstacles = self.is_obstacle_in_path(ax, ay, bx, by )
        if  obstacles == []:
            #print ("clear path")
            return [(bx, by)]
        else: 
            temps = []
            prior = (ax,ay)
           # print ("temps are")
            #print (temps)
            for ox, oy in obstacles:
                temps += self.avoid_obstacle( ax, ay,ox,oy )
               # print ("temps are")
               # print (temps)
            temps += [(bx,by)]
            return temps

            # midx = (1.0*(ax+bx))/2.0
            # midy = (1.0*(ay+by))/2.0
            # dist = 1.0 * sqrt((ax-bx)*(ax-bx) + (ay-by)*(ay-by)) #lenth of hypotenuse
            # slope = (1.0*(ay - by))/(ax - bx+.00001)
            # perpendicular_slope = -1.0/slope
            # ydiff = perpendicular_slope  * dist *.5
            # xdiff = 1.0/perpendicular_slope * dist  *.5
            # tempx1 = midx + xdiff
            # tempy1 = midy + ydiff

            # tempx2 = midx - xdiff
            # tempy2 = midy - ydiff
            # print("printing everything for debugging")
            # print (" ax, ay, bx, by")
            # print( ax, ay, bx, by)
            # print ("mids")
            # print (midx, midy)
            # print ("temps")
            # print(tempx1, tempy1, tempx2, tempy2)
            # print("dist, pslope")
            # print (dist, perpendicular_slope)


            # return 

            # # print (dist)
            # # dx = dx/dist
            # # dy = dx/dist
            # # tempx1 = midx  + (dist/2.0)*dx
            # # tempy1 = midy + (dist/2.0)*dy
            # # tempx2 = midx  - (dist/2.0)*dx
            # # tempy2 = midy - (dist/2.0)*dy

            # #midx = (1.0*(ax+bx))/2.0
            # #midy = (1.0*(ay+by))/2.0

            # left1 = self.avoid_obstacle(ax, ay, tempx2, tempy2) 
            # left2 = self.avoid_obstacle(tempx2, tempy2, bx, by)
            # right1= self.avoid_obstacle(ax, ay, tempx1, tempy1) 
            # right2 = self.avoid_obstacle(tempx1, tempy1, bx, by) 
            # if (left1[1] + left2[1] <right1[1] + right2[1] ):
            #     return left1[0] + left2[0] , left1[1] + left2[1] +1
            # else:
            #     return right1[0] + right2[0] , right1[1] +right2[1]+1






    def getpos(self, inst):
        instance =getattr(self.world, inst)
        p = instance.pos
        return (p.x, p.y, p.z) 

    def move(self,inst,a, b, c=0, tolerance=4, speed=1.5, collide = False):#tolerance=1.5, speed=2.0):
        #inst =getattr(self.world, inst)
        #carry out the move action
        robotloc = self.world.robot1_instance.pos
        #print("printing avoidance")
        #print (self.avoid_obstacle( robotloc.x,robotloc.y , a, b))
        #print("pritndone")
        #print(self.avoid_obstacle( robotloc.x,robotloc.y , a, b))
        #print ("collide is")
       # print (collide)
        if collide == True:
            inst.move(x=a, y=b, z=0,tolerance = tolerance, speed = speed)
        else:
            for loc in self.avoid_obstacle( robotloc.x,robotloc.y , a, b):
                inst.move(x=loc[0], y=loc[1], z=0,tolerance = tolerance, speed = speed)
        newworld = inst.get_world_info()
            #update the location of all objects in the world
        for obj in newworld:
            setattr(getattr(self.world, obj['name']), 'pos',Struct(x =obj['position'][0], y=obj['position'][1], z =obj['position'][2]) )

         
        #print("robot is going to:")
        #print(a,b)
        #print("robot is now at:")
        #print(inst.pos)
        

    def move_old(self,inst,a, b, c=0, tolerance=3, speed=1.5, collide = False):#tolerance=1.5, speed=2.0):
        inst =getattr(self.world, inst)
        #carry out the move action
        tolerance = 3
        robotloc = self.world.robot1_instance.pos

        if collide == True:
            inst.move_collide(x=a, y=b, z=c,tolerance = tolerance, speed = speed)
        else: 
            inst.move(x=a, y=b, z=c,tolerance = tolerance, speed = speed)
        newworld = inst.get_world_info()
        #update the location of all objects in the world
        for obj in newworld:
            setattr(getattr(self.world, obj['name']), 'pos',Struct(x =obj['position'][0], y=obj['position'][1], z =obj['position'][2]) )
     
        #print("robot is going to:")
        #print(a,b)
        #print("robot is now at:")
        #print(inst.pos)
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
