import numpy as np
import pandas as pd
import torch
from scipy.stats import rankdata

def ranking(l, method='max'):
    return rankdata(-np.array(l), method=method)

def get_ranks(elements, scores, level=0):
  if len(elements) > 0:
    max_level = len(elements[0])
    idx = pd.MultiIndex.from_arrays(
      [[t[l] for t in elements] for l in range(max_level)],
      names=[str(l) for l in range(max_level)])
    s = pd.Series(scores, name='scores', index=idx)
    if max_level - 1  == level:
      aggr = s
    else:
      aggr = s.groupby(level=level).max()
    return aggr.index.values, ranking(aggr.values)
  else:
    return []

def get_ranks_of_faulty_elements(elements, scores, faulty_elements, level=0):
    elems, ranks = get_ranks(elements, scores, level=level)
    rank_map = {e: int(r) for e, r in zip(elems, ranks)}
    return [rank_map[fe] for fe in faulty_elements]

def spectrum(X, y):
    e_p = torch.sum(X[y==1], dim=0)
    n_p = torch.sum(y) - e_p
    e_f = torch.sum(X[y==0], dim=0)
    n_f = torch.sum(1 - y) - e_f
    return e_p, n_p, e_f, n_f

def ochiai(e_p, n_p, e_f, n_f):
    e = e_f > 0
    value = torch.zeros(e.shape[0])
    value[e] = e_f[e]/torch.sqrt((e_f[e]+n_f[e])*(e_f[e]+e_p[e]))
    value[~e] = .0
    return value

def wong2(e_p, n_p, e_f, n_f):
    return e_f - e_p

def op2(e_p, n_p, e_f, n_f):
    return e_f-e_p/(e_p+n_p+1)

def dstar(e_p, n_p, e_f, n_f, star=2):
    return np.power(e_f,star)/(e_p+n_f)

def tarantula(e_p, n_p, e_f, n_f):
    t_p = e_p + n_p
    t_f = e_f + n_f
    p_ratio = e_p / t_p
    p_ratio[t_p == 0] = .0
    f_ratio = e_f / t_f
    f_ratio[t_f == 0] = .0
    value =  f_ratio / (p_ratio + f_ratio)
    value[torch.isnan(value)] = .0
    return value
