'''
Created on Jul 9, 2014

@author: lucag
'''
from xmlrpclib import ServerProxy
from feature import as_featurestruct

def test_remote(sentence='Robot1, move to location 1 2!'):
    analyzer = ServerProxy('http://localhost:8090')
    return [as_featurestruct(r, s) for r, s in analyzer.parse(sentence)]
    
    
