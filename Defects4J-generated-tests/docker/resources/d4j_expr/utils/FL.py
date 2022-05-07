import numpy as np
import pandas as pd
from scipy.stats import rankdata, entropy
from enum import Enum

class TestResult(Enum):
  FAILING = 0
  SUCCESS = 1
  NEEDASK = 2
  UNKNOWN = 3

class TestCase:
  def __init__(self, origin, name, coverage, contents, oracle):
    self.origin = origin
    self.name = name
    self.coverage = coverage
    self.contents = contents
    self.oracle = oracle

  @property
  def id(self):
    return (self.origin, self.name)

class CovVecGen:
  def __init__(self, elements):
    elements = list(sorted(list(elements)))
    self.elements = elements
    self.index = {e:i for i, e in enumerate(elements)}

  def generate(self, covered):
    #if any([e not in self.elements for e in covered]):
    #  raise Exception("Unseen elements")
    vector = np.zeros(len(self.elements))
    for e in covered:
      if e in self.index:
        vector[self.index[e]] = 1.
    return vector

def ranking(l, method='max'):
    return rankdata(-np.array(l), method=method)

def matrix_to_index(X, y):
  X, y = np.array(X), np.array(y)
  assert np.all(X >= 0)
  assert np.all(np.isin(y, [0, 1]))

  e_f = np.sum(X[y==0], axis=0)
  n_f = np.sum(y == 0) - e_f
  e_p = np.sum(X[y==1], axis=0)
  n_p = np.sum(y == 1) - e_p
  return e_p, n_p, e_f, n_f

def ochiai(e_p, n_p, e_f, n_f):
  e = e_f > 0
  scores = np.zeros(e_p.shape[0])
  scores[e] = e_f[e]/np.sqrt((e_f[e]+n_f[e])*(e_f[e]+e_p[e]))
  scores[~e] = .0
  return scores

def extend_columns(a, n):
  b = np.zeros((a.shape[0], a.shape[1]+n))
  b[:,:-n] = a
  return b

def minimize_matrix(coverage_matrix, result_vector):
  is_failing_test = result_vector['value'] == TestResult.FAILING
  covered_by_failings = np.sum(coverage_matrix.values[is_failing_test, :], axis=0) > 0
  useful_tests = np.sum(np.logical_and(coverage_matrix, covered_by_failings), axis=1) > 0
  return coverage_matrix.loc[useful_tests, :], result_vector.loc[useful_tests]

def slice_data(coverage_matrix, result_vector):
  is_valid = result_vector['value'].isin([TestResult.FAILING.value, TestResult.SUCCESS.value]).values
  return coverage_matrix.loc[is_valid, :], result_vector.loc[is_valid, :]

def get_ranks(elements, scores, level=0, return_entropy=False, return_score=False, verbose=False):
  if len(elements) > 0:
    max_level = len(elements[0])
    idx = pd.MultiIndex.from_arrays(
      [[t[l] for t in elements] for l in range(max_level)],
      names=[str(l) for l in range(max_level)])
    s = pd.Series(scores, name='scores', index=idx)
    if max_level - 1  == level:
      aggr = s
    else:
      aggr = s.max(level=level)
    if verbose:
      print(aggr)
    if return_entropy and return_score:
      return aggr.index.values, ranking(aggr.values), entropy(aggr.values), aggr.values
    elif return_score:
      return aggr.index.values, ranking(aggr.values), aggr.values
    elif return_entropy:
      return aggr.index.values, ranking(aggr.values), entropy(aggr.values)
    else:
      return aggr.index.values, ranking(aggr.values)
  else:
    return []
