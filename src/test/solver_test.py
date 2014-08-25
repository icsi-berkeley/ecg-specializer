import unittest, sys
from solver import MorseProblemSolver

class Test(unittest.TestCase):

    def setUp(self):
        pass


    def tearDown(self):
        pass

    def test_ForceFail(self):
        assert False
        self.assertTrue( False)

if __name__ == "__main__":
        unittest.main()

#suite = unittest.TestLoader().loadTestsFromTestCase(SolverTest)
#unittest.TextTestRunner(verbosity=2).run(suite)
#print ("ran test")
