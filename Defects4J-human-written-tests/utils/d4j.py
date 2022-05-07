import os
import pandas as pd
import numpy as np
from sklearn.preprocessing import binarize

data_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'data'
)

def path(rpath):
    return os.path.join(data_path, rpath)

def get_coverage_matrix(p, n):
    saved_matrix_path = path("coverage_matrix/{}/{}-{}.pkl".format(p, p, n))
    if os.path.exists(saved_matrix_path):
        return pd.read_pickle(saved_matrix_path)
    else:
        return None

def get_failing_tests(p, n):
    with open(path("failing_tests/{}/{}".format(p, n)), 'r') as f:
        failing_tests = list(map(lambda l:l.strip(), f.readlines()))
    return failing_tests

def get_faulty_methods(p, n):
    with open(path("buggy_methods/{}-{}".format(p, n)), 'r') as f:
        elems = list(map(lambda l: l.strip(), f.readlines()))
    return elems

def get_faulty_lines(p, n):
    import json
    elems = []
    with open(path("buggy_lines/{}-{}".format(p, n))) as json_file:
        data = json.load(json_file)
        for method in data:
            for line in data[method]:
                elems.append((method, line))
    return elems

def load(p, n):
    # Load the coverage matrix
    coverage_matrix = get_coverage_matrix(p, n)
    if coverage_matrix is None:
        print(f"[{p}-{n}] exception: no coverage matrix")
        return None

    elements = coverage_matrix.index.values
    testcases = coverage_matrix.columns.values

    # Load the failing tests information
    failing_tests = get_failing_tests(p, n)
    if not failing_tests:
        print(f"[{p}-{n}] exception: no failing tests")
        return None

    X = np.transpose(coverage_matrix.values)
    y = np.array([ int(t not in failing_tests) for t in testcases ])

    if not np.all(X >= 0):
        #print(testcases[np.unique(np.where(X < 0)[0])])
        X[X < 0] = 1
        print(f"[{p}-{n}] warning: X < 0 exists")
        #return None

    faulty_methods = get_faulty_methods(p, n)
    if not faulty_methods:
        print(f"[{p}-{n}] exception: no faulty methods")
        return None

    is_faulty = np.isin(list(map(lambda t: t[0], elements)), faulty_methods)
    """
    methods = {}
    for i, elem in enumerate(elements):
        if elem[0] not in methods:
            methods[elem[0]] = []
        methods[elem[0]].append(i)
    """
    return binarize(X), y, elements, testcases, faulty_methods