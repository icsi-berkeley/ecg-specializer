"""Created on Mar 6, 2014 by @author lucag.
"""

from pymorse import Morse  
from utils import update, Struct
from pprint import pprint

def print_pos(pose):
    print("I'm currently at %s" % pose)



def test_robot1():
    with Morse() as simu:
        inst = simu.robot1_instance
        
        ss = inst.camera.get()
        for o in ss['visible_objects']:
            pprint(o['name'], o['position'])
        
        # subscribes to updates from the Pose sensor by passing a callback
#         inst.pose.subscribe(print_pos)
    
        # sends a destination
        inst.motion.publish({'x' : 10.0, 'y': 5.0, 'z': 0.0,
                             'tolerance' : 0.5, 'speed' : 1.0})
    
        # Leave a couple of millisec to the simulator to start the action
        simu.sleep(0.1)
    
        # waits until we reach the target
        while inst.motion.get_status() != 'Arrived':
            simu.sleep(3)
    
        print('Here we are!')

class Box(object):
    """A simple box object that knows where it is 
    """
    def __init__(self, name, type, pos, color, size):
        update(self, name=name, type = type, pos=pos, color=color, size = size,simulator=Morse())
        #print(self.simulator.__dict__)
        #print ('\n')
      #  inst = getattr(self.simulator, self.name)
        #inst.pose.subscribe(self.setpos)
    
    def setpos(self, pos):
        self.pos = Struct(**pos)


class Robot(object):
    """A simple controller for a Morse simulated robot.
    """
    def __init__(self, name):
        update(self, name=name, pos=Struct(x=0.0, y=0.0, z=0.0), simulator=Morse())
        inst = getattr(self.simulator, self.name)
        inst.robot_pose.subscribe(self.setpos)

    def get_pos():
        return  pose

    def setpos(self, pos):
        self.pos = Struct(**pos)


    def move(self, **to):
        inst = getattr(self.simulator, self.name)
        inst.motion.publish(to)
        #inst.motion.goto(to['x'],to['y'] ,to['tolerance'],to['speed'])
        #print(inst.motion.get_configurations())
        # Leave a couple of ms to the simulator to start the action.
        self.simulator.sleep(0.1)
    
        # waits until we reach the target
        while inst.motion.get_status() != "Arrived":
            self.simulator.sleep(0.5) 

    def move_collide(self, **to):
        inst = getattr(self.simulator, self.name)
        inst.motion_collide.publish(to)
        #inst.motion.goto(to['x'],to['y'] ,to['tolerance'],to['speed'])
        inst.motion._obstacle_avoidance = False
        print(inst.motion._obstacle_avoidance )
        print(inst.motion.get_configurations())
        # Leave a couple of ms to the simulator to start the action.
        self.simulator.sleep(1)
    
       

            
       
    def get_world_info(self):
        inst = getattr(self.simulator, self.name)
        return inst.camera.get()['visible_objects']
         #update the model of the wold (based on damages you did...)
        
      
    def close(self):
        self.simulator.quit()
        
def test_robot2():
    r = Robot('robot1_instance')
    for _ in range(2):
        r.move(x=10.0, y=5.0, z=0.0)
        r.move(x=0.0, y=0.0, z=0.0)
    
if __name__ == '__main__':
    test_robot1()    
