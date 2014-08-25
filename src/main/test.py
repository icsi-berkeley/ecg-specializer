def test_remote(sentence='Robot1, move to location 1 2!'):
    from feature import as_featurestruct
    a = ServerProxy('http://localhost:8090')
    d = a.parse(sentence)
    s = as_featurestruct(d[0])
    return s
    
def test_local(sentence='Robot1, move to location 1 2!'):
    from feature import as_featurestruct
    a = Analyzer('grammar/robots.prefs')
    d = a.parse(sentence)
    s = as_featurestruct(d[0])
    return s