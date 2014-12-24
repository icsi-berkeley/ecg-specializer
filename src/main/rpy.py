from rpy2 import robjects
from rpy2.robjects import *
from rpy2.robjects.packages import importr
graphics = importr('graphics')
grdevices = importr('grDevices')
base = importr('base')
stats = importr('stats')


"""
grdevices.X11()

x = IntVector([1, 2, 3])
y = IntVector([5, 6, 7])

s = StrVector(['test', 'test1,', 'test2'])

graphics.plot(x, y, xlab= "test", ylab = "test2", col='blue')

robjects.r.barplot(x, names=s)
"""