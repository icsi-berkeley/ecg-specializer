'''
Created on Jul 9, 2014

@author: stevedoubleday
'''
import unittest, sys,  pickle
from solver import MorseProblemSolver
# import nose.tools 
# from nose.tools import assert_equal
# from nose.tools import assert_not_equal
# from nose.tools import assert_raises
# from nose.tools import raises

class Test(unittest.TestCase):


    def setUp(self):
        pass


    def tearDown(self):
        pass


    def testName(self):
        print(sys.version_info)
        assert 'b' == 'b'    
        pass
    def testForceFail(self):
        assert False
    def testMorseSolver(self):
#         f=open('src/main/pickled.p','rb')
#         ntuple=pickle.load(f)
        ntuple='{"__JSON_Struct__": {"parameters": [ { "__JSON_Struct__": {"control_state": "ongoing",   "goal": {"referent": "box2_instance"}, "direction": "RD", "acted_upon": "robot1_instance","kind": "execute", "action": "move",  "heading": "null", "distance": {"__JSON_Struct__": {"value": 4, "units": "square" }}}}], "return_type": "error_descriptor", "predicate_type": "command"}}'
        print(ntuple)
        solver = MorseProblemSolver()
        solver.setMockMove(True)
        solver.solve(ntuple)
        coords = solver.coords
        print(coords)
        assert coords[0] == -2.0
        assert coords[1] == -3.0
        assert coords[2] == 1.0
#         MorseProblemSolver().solve(ntuple)
        assert True    

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()