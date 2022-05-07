import os
import re
import argparse
import sys
import shutil
import numpy as np
import pandas as pd
import subprocess
import shlex
from copy import deepcopy
from env import EvoD4jEnv
from tabulate import tabulate
from utils.evosuite import parse as parse_evosuite, carve as carve_evosuite, get_test_by_line, test_path_to_class_name
from utils.cobertura import get_hits
from utils.FL import *
from utils.UI import bcolors, coloring

if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument('project', type=str)
  parser.add_argument('version', type=int)
  parser.add_argument('--tool', '-t', type=str, default='evosuite')
  parser.add_argument('--id', '-i', type=str, default='1')
  args = parser.parse_args()

  project = args.project
  version = args.version
  ts_id = args.id
  tool = args.tool

  env = EvoD4jEnv(project, version, ts_id)

  testcases = {}
  for dp, dn, fn in os.walk(env.extracted_dir):
    for f in fn:
      if f.endswith("ESTest.java"):
        relpath = os.path.relpath(os.path.join(dp, f), start=env.extracted_dir)
        testcases[relpath] = []
        coverage, test_content = parse_evosuite(os.path.join(dp, f))
        for test in sorted(coverage.keys()):
          testcases[relpath].append(test)

  if os.path.exists(env.minimised_dir):
    shutil.rmtree(env.minimised_dir)

  removed = set()
  """
  Minimize test suite
  """
  remainings = deepcopy(testcases)
  shutil.copytree(env.extracted_dir, env.minimised_dir)
  print(env.extracted_dir, env.minimised_dir)


  budget = 5
  i = 0
  while True:
    for test_path in remainings:
      if remainings[test_path]:
        with open(os.path.join(env.minimised_dir, test_path), 'w') as f:
          f.write(carve_evosuite(os.path.join(env.extracted_dir, test_path), remainings[test_path]))
      elif os.path.exists(os.path.join(env.minimised_dir, test_path)):
        os.remove(os.path.join(env.minimised_dir, test_path))
        os.remove(os.path.join(env.minimised_dir, test_path.replace("ESTest", "ESTest_scaffolding")))
        print("{} removed".format(test_path))
    #os.system("tar -cvzf {}.{}")

    if os.path.exists(env.minimised_suite_file):
      os.remove(env.minimised_suite_file)

    os.system("cd {} && tar -cjf ../{} *".format(
      env.minimised_dir,
      os.path.basename(env.minimised_suite_file)
    ))

    cp = subprocess.run(
      shlex.split("defects4j test -s {}".format(env.minimised_suite_file)),
      cwd=env.fixed_tmp_dir,
      universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if cp.returncode == 0 or not i < budget:
      break

    i += 1
    error_locs = []
    for line in cp.stderr.split('\n'):
      m = re.search(r"\[javac\]\s+{}\/\.test_suite\/(.*\.java):(\d+):".format(env.fixed_tmp_dir), line.strip())
      if m:
        error_locs.append((m.group(1), int(m.group(2))))

    print("=============== {}th trials =================".format(i))
    print(error_locs)

    for loc in error_locs:
      test = get_test_by_line(os.path.join(env.minimised_dir, loc[0]), loc[1])
      if test is not None and test in remainings[loc[0]]:
        remainings[loc[0]].remove(test)
        removed.add((loc[0], test))
        print("{} {} removed".format(loc[0], test))

  if cp.returncode == 0:
    print(cp.stdout)
    shutil.copy(
      os.path.join(env.fixed_tmp_dir, "failing_tests"),
      env.oracle_path
    )
    with open(env.broken_test_path, 'w') as f:
      for test in removed:
        f.write("{} {}\n".format(test[0], test[1]))
    print("succeed.")
  else:
    print("fail.")
    exit(1)

  print(remainings)

  # Coverage measurement
  os.makedirs(env.evosuite_coverage_dir, exist_ok=True)
  for test_path in testcases:
    if not testcases[test_path]:
      continue
  
    for test in testcases[test_path]:
      test_specifier = "{}::{}".format(test_path_to_class_name(test_path), test)
      save_path = os.path.join(env.evosuite_coverage_dir, "{}.pkl".format(test_specifier))
  
      if os.path.exists(save_path):
        print("exists: ", save_path)
        continue

      print("generating: ", save_path)
      print("- target classes: ", env.relevant_classes_file)
      print("- command: defects4j coverage -s {} -i {} -t {}".format(
            env.minimised_suite_file,
            env.relevant_classes_file,
            test_specifier
      ))
  
      cp = subprocess.run(
        shlex.split("defects4j coverage -s {} -i {} -t {}".format(
          env.minimised_suite_file,
          env.relevant_classes_file,
          test_specifier
        )),
        cwd=env.buggy_tmp_dir,
        universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
      )
      print(cp.stdout, cp.stderr)

      if cp.returncode == 0:
        coverage_xml = os.path.join(env.buggy_tmp_dir, "coverage.xml")
      else:
        coverage_xml = None

      if coverage_xml:
        hits = get_hits(coverage_xml)
        hits.to_pickle(save_path)
        os.remove(coverage_xml)
      else:
        print("failed")
  print()

  if os.path.exists(env.minimised_dir):
    shutil.rmtree(env.minimised_dir)

  if os.path.exists(env.minimised_suite_file):
    os.remove(env.minimised_suite_file)