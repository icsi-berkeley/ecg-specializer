from functools import singledispatch # possibly unnecessary
from specializerTools import *

ana = Analyzer("http://localhost:8090")

class DispatchSpecializer(UtilitySpecializer):
	def __init__(self):
		UtilitySpecializer.__init__(self)


	def specialize(self, fs):
		print(repr(fs))
		


d = DispatchSpecializer()
imperative = ana.parse("Robot1, move to the red box!")

