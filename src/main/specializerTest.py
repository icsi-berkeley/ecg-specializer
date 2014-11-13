"""
@author: Sean Trott

This is a set of tests to run periodically on the Specializer.
It will check whether the N-Tuples being produced by the Specializer
are correct.

It should compare an N-Tuple against some frozen set of N-Tuples.

Ideally, the tests should be modular; the Analyzer or Solver shouldn't be run to test
the N-Tuples. This means that certain FeatureStructs (SemSpecs) might also
have to be frozen, and read into the testing file to be "specialized."

*For now, I might just use it in conjunction with the JYTHON Analyzer, until I figure out
an easy way to save SemSpecs and freeze them in a directory. So currently, this requires
the Jython analyzer to be running too - this isn't much of an inconvience for now.

Tests to write:
-definitions (define...)
-ref resolution (some of this has been done)

"""

from specializer import *
from json import loads
from feature import StructJSONEncoder
import unittest
from pprint import pprint

specializer = RobotSpecializer()

analyzer = Analyzer("http://localhost:8090")


def create_JSON(file):
	""" Extracts a JSON Struct from dumped file. """
	data = json.load(file)
	file.close()
	return loads(json.dumps(data), object_hook=StructJSONEncoder.as_struct)

def struct_to_vars(struct):
	""" Returns a dictionary of STRUCT. """
	temp = vars(struct)
	for key, value in temp.items():
		if key == "parameters" or key == 'condition' or key == 'command':
			value[:] = [struct_to_vars(i) if type(i) == Struct else i for i in value]
		elif type(value) == Struct:
			temp[key] = struct_to_vars(value)
	return temp


class TestSpecializer(unittest.TestCase):

	def test_simple_move(self):
		""" Should run a simple test of the sentence, "Robot1, move to Box1!". """
		simple = create_JSON(open('src/main/test_tuples/Robot1_move_to_Box1', 'r'))
		semspec = analyzer.parse("Robot1, move to Box1!")
		specialized = specializer.specialize(semspec[0])
		self.assertEqual(struct_to_vars(specialized), struct_to_vars(simple))

	def test_serial_move(self):
		""" Runs a test of the sentence, "Robot1, move North then return!". """
		serial = create_JSON(open('src/main/test_tuples/Robot1_move_North_then_return', 'r'))
		semspec = analyzer.parse("Robot1, move North then return!")
		specialized = specializer.specialize(semspec[0])
		self.assertEqual(struct_to_vars(specialized), struct_to_vars(serial))

	def test_conditional(self):
		""" Runs a test of conditional sentences: "Robot1, if the box near the green box is red, move to the blue box!". """
		conditional = create_JSON(open('src/main/test_tuples/Robot1_if_the_box_near_the_green_box_is_red_move_to_the_blue_box', 'r'))
		semspec = analyzer.parse("Robot1, if the box near the green box is red, move to the blue box!")
		specialized = specializer.specialize(semspec[0])
		self.assertEqual(struct_to_vars(specialized), struct_to_vars(conditional))

	def test_push(self):
		""" Runs a test of 'push' command: "Robot1, push Box1 North. """
		push = create_JSON(open('src/main/test_tuples/Robot1_push_the_big_red_box_North', 'r'))
		semspec = analyzer.parse("Robot1, push the big red box North!")
		specialized = specializer.specialize(semspec[0])
		self.assertEqual(struct_to_vars(specialized), struct_to_vars(push))

	def test_referent_resolution(self):
		""" Runs several tests of referent resolution. Not all use imported JSON structs. Also tests one-anaphora."""
		# TEST referent resolution ("it")
		specializer.specialize(analyzer.parse("Robot1, move to the blue box!")[0])
		new_res = struct_to_vars(specializer.specialize(analyzer.parse("Robot1, push it North!")[0]))
		referent = new_res['parameters'][0]['causalProcess']['acted_upon']
		self.assertEqual(referent, {'objectDescriptor': {'givenness': 'uniquelyIdentifiable', 'color': 'blue', 'type': 'box'}})
		# TEST one-anaphora
		new_res = struct_to_vars(specializer.specialize(analyzer.parse("Robot1, push the green one North!")[0]))
		referent2 = new_res['parameters'][0]['causalProcess']['acted_upon']
		self.assertEqual(referent2, {'objectDescriptor': {'givenness': 'uniquelyIdentifiable', 'color': 'green', 'type': 'box'}})

	def test_where(self):
		""" Runs test of "where is Box1?". """
		specialized = specializer.specialize(analyzer.parse("where is Box1?")[0])
		where = create_JSON(open('src/main/test_tuples/where_is_Box1', 'r'))
		self.assertEqual(struct_to_vars(specialized), struct_to_vars(where))

	def test_which(self):
		""" Runs several tests of 'which', for both plural and singular cases. """
		which1 = create_JSON(open('src/main/test_tuples/which_boxes_are_red', 'r'))
		specialized = specializer.specialize(analyzer.parse("which boxes are red?")[0])
		self.assertEqual(struct_to_vars(specialized), struct_to_vars(which1))
		which2 = create_JSON(open('src/main/test_tuples/which_box_is_near_the_green_box', 'r'))
		specialized2 = specializer.specialize(analyzer.parse("which box is near the green box?")[0])
		self.assertEqual(struct_to_vars(specialized2), struct_to_vars(which2))

	def test_yesno(self):
		""" Runs a test of yes/no questions, like "is Box1 red?". """
		yes = create_JSON(open('src/main/test_tuples/is_Box1_red', 'r'))
		specialized = specializer.specialize(analyzer.parse("is Box1 red?")[0])
		self.assertEqual(struct_to_vars(specialized), struct_to_vars(yes))

	def test_define_visit(self):
		""" Runs a test of several different definitions. "define visit as...", """
		specializer.specialize(analyzer.parse("define visit QL1 as move to QL1 then return.")[0])
		specialized = specializer.specialize(analyzer.parse("Robot1, visit the big red box!")[0])
		self.assertEqual(specialized.parameters[0].action, "move")
		self.assertEqual(specialized.parameters[0].goal, {'objectDescriptor': {'type': 'box', 'color': 'red', 'size': 'big', 'givenness': 'uniquelyIdentifiable'}})

	
	def test_define_task(self):
		""" Runs a test of: "define task QO1 and QO2 as move to QO1 then push QO2 North." """
		specializer.specialize(analyzer.parse("define task QO1 and QO2 as move to QO1 then push QO2 North.")[0])
		specialized = specializer.specialize(analyzer.parse("Robot1, task Box1 and Box2!")[0])
		self.assertEqual(struct_to_vars(specialized), struct_to_vars(create_JSON((open('src/main/test_tuples/Robot1_task_Box1_and_Box2', 'r')))))
		self.assertEqual(specialized.parameters[0]['action'], 'move')
		self.assertEqual(struct_to_vars(specialized)['parameters'][1]['action'], 'push_move')




if __name__ == '__main__':
	unittest.main()





