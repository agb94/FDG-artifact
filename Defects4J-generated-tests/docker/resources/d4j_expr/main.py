import random
import os
import re
import argparse
import torch
import datetime
import numpy as np
import pandas as pd
from env import EvoD4jEnv
from tqdm import tqdm
from tabulate import tabulate
from utils.evosuite import parse as parse_evosuite, test_path_to_class_name, class_name_to_test_path
from utils.cobertura import *
from utils.FL import *
from utils.metrics import *
from utils.UI import bcolors, coloring

def modification_date(filename):
    t = os.path.getmtime(filename)
    return datetime.datetime.fromtimestamp(t)

class EvalException(Exception):
  pass

def loop(project, version, tool, ts_id, selection_metric_name,
  budget=10, noise_prob=0.0, new=False, skip_broken=False, verbose=False):
  env = EvoD4jEnv(project, version, ts_id)

  print("* selection metric: {}".format(selection_metric_name))
  print("* subject: {}-{}b".format(project, version))
  print("* test suite: {}-{} ({})".format(tool, ts_id, env.extracted_dir))

  if "FDG:" in selection_metric_name:
    selection_metric = FDG
    metric_params = {'alpha': float(selection_metric_name.split(':')[-1])}
  else:
    selection_metric = eval(selection_metric_name)
    metric_params = {}

  if not os.path.exists(env.metadata_dir):
    raise EvalException("Metatdata not found")

  """
  with open(env.relevant_classes_file) as f:
    target_classes = [l.strip() for l in f]
  print("* {} target classes:".format(len(target_classes)))
  for c in target_classes:
    print("--- {}".format(c))
  """

  """
  Loading buggy methods
  """
  buggy_methods = []
  with open(env.buggy_methods_file, 'r') as f:
    signature_pattern = r"(.*)\$([^\$].*)\<([^\<]*)\>$"
    for l in f:
      m = re.search(signature_pattern, l.strip())
      if m:
        buggy_methods.append("{}.{}({})".format(m.group(1), m.group(2), m.group(3)))

  if not buggy_methods:
    raise EvalException("Omission Fault")

  if os.path.exists(env.covmat_path) and os.path.exists(env.oravec_path):
    coverage_matrix = pd.read_pickle(env.covmat_path)
    oracle_vector = pd.read_pickle(env.oravec_path)
    if oracle_vector.iloc[0]["value"] in TestResult:
      oracle_vector["value"] = list(map(lambda tr: tr.value, oracle_vector["value"]))
      oracle_vector.to_pickle(env.oravec_path)
  else:
    """
    Loading failing tests
    """
    with open(env.failing_tests, 'r') as f:
      failing_tests = f.read().strip().split("\n")

    print("* {} buggy methods:".format(len(buggy_methods)))
    for m in buggy_methods:
      print("--- {}".format(m))
    print("* {} failing tests".format(len(failing_tests)))
    for t in failing_tests:
      print("--- {}".format(t))

    """
    Loading test oracles
    """
    # FIXME: Building oracle results vector
    try:
      failing_at_fixed = []
      with open(env.oracle_path, 'r', encoding='utf-8') as f:
        for l in f:
          if l.startswith("--- "):
            failing_test = l[4:].strip().split("::")
            if len(failing_test) != 2:
              continue
            test_class, test_no = failing_test
            test_class = test_class.replace('.', '/') + '.java'
            test_no = int(test_no[4:])
            failing_at_fixed.append((test_class, str(test_no)))
      broken_at_fixed = []
      with open(env.broken_test_path, 'r', encoding='utf-8') as f:
        for l in f:
          broken_at_fixed.append(l.strip().split())
      print(failing_at_fixed, broken_at_fixed)
    except Exception as e:
      print("Error while loading oracles..", e)
      raise EvalException("Oracle Loading Error")

    """
    Collect all lines that appears in the coverage data (failing tests, generated tests)
    """
    lines = set()
    for test in failing_tests:
      coverage_path = os.path.join(env.coverage_dir, test + ".xml")
      lines.update(get_hits(coverage_path)['lid'].values.tolist())

    print("* {} lines collected".format(len(lines)))
    for coverage_file in os.listdir(env.evosuite_coverage_dir):
      if os.path.splitext(coverage_file)[1] == '.pkl':
        coverage_path = os.path.join(env.evosuite_coverage_dir, coverage_file)
        hits = pd.read_pickle(coverage_path)
        lines.update(hits['lid'].values.tolist())
    print("* {} lines collected".format(len(lines)))

    """
    Initialize the coverage vector generator
    """
    cov = CovVecGen(lines)

    """
    Collect tests' metadata
    """
    tests = []
    for test in failing_tests:
      coverage_path = os.path.join(env.coverage_dir, test + ".xml")
      cov_vector = cov.generate(get_hits(coverage_path)['lid'].values.tolist())
      tests.append(
        TestCase("initial_test", test, cov_vector, None, TestResult.FAILING)
      )

    num_generated_tests = 0
    test_contents = {}
    for coverage_file in os.listdir(env.evosuite_coverage_dir):
      if os.path.splitext(coverage_file)[1] == '.pkl':
        test_path = class_name_to_test_path(coverage_file[:-4].split('::')[0])
        test = coverage_file[:-4].split('::')[1]
        coverage_path = os.path.join(env.evosuite_coverage_dir, coverage_file)
        hits = pd.read_pickle(coverage_path)
        cov_vector = cov.generate(hits['lid'].values.tolist())
        if test_path not in test_contents:
          test_contents[test_path] = parse_evosuite(os.path.join(env.extracted_dir, test_path))[1]
        tc = TestCase(test_path, test, cov_vector, test_contents[test_path][test], TestResult.SUCCESS)
        if tc.id in failing_at_fixed:
          tc.oracle = TestResult.FAILING
        elif tc.id in broken_at_fixed:
          tc.oracle = TestResult.UNKNOWN if skip_broken else TestResult.FAILING
        tests.append(tc)
        num_generated_tests += 1
    print("* {}/{} generated tests are failed in fixed version".format(
          len(failing_at_fixed), num_generated_tests))

    """
    Construct coverage matrix and result vector
    """
    #FIXME: pickling this matrix and result vector
    coverage_matrix = pd.DataFrame([tc.coverage for tc in tests],
                                   index=[tc.id for tc in tests],
                                   columns=cov.elements)

    """
    result_vector = pd.DataFrame([tc.oracle if tc.origin == "initial_test" else TestResult.NEEDASK for tc in tests],
                                 index=[tc.id for tc in tests], columns=['value'])
    """
    oracle_vector = pd.DataFrame([tc.oracle.value for tc in tests],
                                 index=[tc.id for tc in tests], columns=['value'])

    coverage_matrix.to_pickle(env.covmat_path)
    oracle_vector.to_pickle(env.oravec_path)
  #print("* original coverage shape: {}".format(coverage_matrix.shape))
  #coverage_matrix, result_vector = minimize_matrix(coverage_matrix, result_vector)
  #print("* after minimization: {}".format(coverage_matrix.shape))

  is_failing = oracle_vector['value'] == TestResult.FAILING.value
  is_suspicious = np.sum(coverage_matrix.values[is_failing, :], axis=0) > 0
  total_methods = set(map(lambda t: t[0], coverage_matrix.columns.values))
  suspicious_methods = set(map(lambda t: t[0], coverage_matrix.columns.values[is_suspicious]))
  summary = pd.DataFrame([
      coverage_matrix.shape[0],
      np.sum(is_failing),
      coverage_matrix.shape[1],
      np.sum(is_suspicious),
      len(total_methods),
      len(suspicious_methods),
      len(buggy_methods),
    ], index=[
      "num_total_tests",
      "num_failing_tests",
      "num_lines",
      "num_suspicious_lines",
      "num_total_methods",
      "num_suspicious_methods",
      "num_buggy_methods"], columns=["value"])

  print(summary)
  summary.to_pickle(env.summary_path)

  if noise_prob == 0.0:
    tests_path = env.tests_path
    method_ranks_path = env.ranks_path
  else:
    tests_path = os.path.splitext(env.tests_path)[0] + f"_noise_{noise_prob}.pkl"
    method_ranks_path = os.path.splitext(env.ranks_path)[0] + f"_noise_{noise_prob}.pkl"

  tests_path = tests_path.replace("tests", "tests-{}".format(selection_metric_name))
  method_ranks_path = method_ranks_path.replace("ranks", "ranks-{}".format(selection_metric_name))

  if os.path.exists(tests_path) and os.path.exists(method_ranks_path):
    tests = pd.read_pickle(tests_path)
    method_ranks = pd.read_pickle(method_ranks_path)
    if "oracle" not in tests.columns:
      if noise_prob != 0.0:
        raise Exception("Something wrong..")
      oracles = []
      for test in tests["test"].values:
        oracles.append(oracle_vector.iloc[oracle_vector.index == test].values[0, 0])
      tests["oracle"] = oracles
      tests["response"] = oracles

    if tests.iloc[0]["oracle"] in TestResult:
      tests["oracle"] = list(map(lambda tr: tr.value, tests["oracle"]))
      tests["response"] = list(map(lambda tr: tr.value, tests["response"]))

    tests.to_pickle(tests_path)
    print(tests)
  else:
    print("********************************************")
    tests, method_ranks = select(coverage_matrix, oracle_vector, buggy_methods,
                                 selection_metric, budget, noise_prob,
                                 metric_params=metric_params,
                                 skip_broken=skip_broken, verbose=verbose)
    tests.to_pickle(tests_path)
    method_ranks.to_pickle(method_ranks_path)
  return method_ranks

def select(coverage_matrix, oracle_vector, buggy_methods,
           selection_metric, budget=10, noise_prob=0.0, metric_params={},
           skip_broken=False, verbose=False):

  result_vector = oracle_vector.copy()
  result_vector[[tc[0] != "initial_test" for tc in result_vector.index]] = TestResult.NEEDASK.value

  all_methods = list(set([m for m, l in coverage_matrix.columns]))
  method_ranks = pd.DataFrame(all_methods, index=all_methods, columns=['method'])
  is_buggy = [any([m.startswith(bm) for bm in buggy_methods]) for m in all_methods]
  if not any(is_buggy):
    raise EvalException("No buggy methods among the covered ones")
  method_ranks['is_buggy'] = is_buggy

  selected_fitness, selected_test, oracle, response = None, None, None, None
  tests = pd.DataFrame([], columns=["iteration", "test", "fitness", "oracle", "response"])
  rows = []
  i = 0
  while True:
    s_covmat, s_resvec = slice_data(coverage_matrix, result_vector)
    current_test_inputs = s_covmat.index.values
    #print("current inputs:", current_test_inputs)
    if current_test_inputs.shape[0] == 0:
      raise Exception("No valid initial inputs")
    X = torch.tensor(s_covmat.values)
    y = torch.tensor((s_resvec['value'] == TestResult.SUCCESS.value).values.astype(np.uint8))

    e_p, n_p, e_f, n_f = matrix_to_index(X, y)
    scores = ochiai(e_p, n_p, e_f, n_f)
    methods, ranks, entropy, mscores = get_ranks(s_covmat.columns.values, scores, level=0, return_entropy=True, return_score=True, verbose=verbose)

    mr_map = dict(zip(methods, ranks))
    ms_map = dict(zip(methods, mscores))
    method_ranks[f"rank-{i}"] = method_ranks['method'].map(mr_map)
    method_ranks[f"score-{i}"] = method_ranks['method'].map(ms_map)

    buggy_ranks = method_ranks[method_ranks['is_buggy'] == True][f"rank-{i}"].values

    weighted_momentum = None
    if i > 0:
      momentum = method_ranks[f"rank-{i}"] - method_ranks[f"rank-{i-1}"]
      weighted_momentum = np.sum(np.abs(momentum) * 1/method_ranks[f"rank-{i}"])

    if verbose:
      # print(method_ranks)
      print("Ranks of buggy elements:", coloring(buggy_ranks, bcolors.OKGREEN))

    row = [
      i, selected_test if selected_test is not None else current_test_inputs,
      selected_fitness, oracle, response, buggy_ranks
    ]
    rows.append(row)

    if not i < budget:
      break

    i += 1

    if verbose:
      print("\nIteration {}".format(i))

    weights = scores
    fitnesses = []
    test_iterator = enumerate(coverage_matrix.index)
    if verbose:
      test_iterator = tqdm(test_iterator)
    target = torch.any(X.type(torch.bool), dim=0)

    if selection_metric == FDG:
      _, AG = torch.unique(X, sorted=False, return_inverse=True, dim=1)
      AG = AG.reshape(1, -1)

    for j, test in test_iterator:
      if result_vector.iloc[j]['value'] != TestResult.NEEDASK.value:
        continue
      x = torch.tensor(coverage_matrix.iloc[j].values)
      if torch.all(x == 0):
        # skip if zero coverage
        continue
      fitness = selection_metric(X if selection_metric != FDG else AG, x,
        w=torch.tensor(weights), target=target, y=y, **metric_params)
      fitnesses.append((fitness, test, j))
    fitnesses.sort()
    fitnesses.reverse()

    if fitnesses:
      selected_fitness, selected_test, selected_index = fitnesses[0]
    else:
      break
    if verbose:
      print("{} ({})".format(selected_test, round(selected_fitness, 3)))

    oracle = oracle_vector.iloc[selected_index]['value']
    if random.random() < noise_prob:
      if oracle == TestResult.FAILING.value:
        response = TestResult.SUCCESS.value
      elif oracle == TestResult.SUCCESS.value:
        response = TestResult.FAILING.value
    else:
      response = oracle

    tests = tests.append({"iteration": i, "test": selected_test, "fitness": selected_fitness, "oracle": oracle, "response": response}, ignore_index=True)

    result_vector.iloc[selected_index]['value'] = response

    if verbose:
      print("oracle:", oracle)
      print("response:", response)

  print(tabulate(rows, headers=["Iter", "Test", "Fitness", "Oracle", "Response", "Ranks"]))
  return tests, method_ranks

if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument('project', type=str)
  parser.add_argument('version', type=int)
  parser.add_argument('--noise', '-n', type=float, default=0.0)
  parser.add_argument('--tool', '-t', type=str, default='evosuite')
  parser.add_argument('--id', '-i', type=str, default='1')
  parser.add_argument('--budget', '-b', type=int, default=3)
  parser.add_argument('--selection', '-s', type=str, default="FDG:0.5")
  parser.add_argument('--verbose', '-v', action="store_true")
  parser.add_argument('--new', action="store_true")
  parser.add_argument('--skip-broken', action="store_true")
  args = parser.parse_args()

  """
  Setting basic variables
  """
  loop(args.project, args.version, args.tool, args.id, args.selection,
       budget=args.budget, noise_prob=args.noise, new=args.new,
       skip_broken=args.skip_broken, verbose=args.verbose)
