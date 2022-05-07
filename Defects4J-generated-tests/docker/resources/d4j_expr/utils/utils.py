import argparse
import xml.etree.ElementTree as ET
import re

EVOSUITE_PATTERNS = {
  "tc_no": r"//Test case number: (\d+)",
  "line_goal": r"\* Goal \d+\. ([^:]+): Line (\d+)",
  "cov_end": "*/",
}

def parse_evosuite(path):
  coverages = {}
  tests = {}
  with open(path, "r") as test_file:
    tc_no = None
    cov_read = False
    for l in test_file:
      stripped = l.strip()
      m = re.search(EVOSUITE_PATTERNS["tc_no"], stripped)
      if m:
        tc_no = m.group(1)
        coverages[tc_no] = []
        tests[tc_no] = []
        cov_read = True
        continue
      if not cov_read:
        if tc_no and l.rstrip() != "}":
          tests[tc_no].append(l)
        continue
      if stripped == EVOSUITE_PATTERNS["cov_end"]:
        cov_read = False
        continue
      m = re.search(EVOSUITE_PATTERNS["line_goal"], stripped)
      if m:
        coverages[tc_no].append((m.group(1), m.group(2)))
  for t in tests:
    tests[t] = "".join(tests[t]).strip()
  return coverages, tests

def carve_evosuite(path, test_numbers):
  tests = []
  with open(path, "r") as test_file:
    tc_no = None
    test_remove = False
    for l in test_file:
      stripped = l.strip()
      m = re.search(EVOSUITE_PATTERNS["tc_no"], stripped)
      if m:
        tc_no = m.group(1)
        if tc_no not in map(str, test_numbers):
          test_remove = True
        else:
          test_remove = False
      if test_remove and l.rstrip() != "}":
        continue
      tests.append(l)
  return "".join(tests)

def parse_cobertura(path):
  tree = ET.parse(path)
  root = tree.getroot()
  # key: (class_name, method_name, signature)
  # value: hitcount
  covered_classes = []
  hits = {}
  packages = root[1]
  for package in packages:
    for classes in package:
      for _class in classes:
        class_name = _class.attrib["name"]
        class_file_name = _class.attrib["filename"]
        line_rate = float(_class.attrib["line-rate"])
        num_lines = len(_class[1])
        if line_rate > 0:
          covered_classes.append(class_name)
        #    print(class_name, line_rate)
        for method in _class[0]:
          method_name = method.attrib["name"]
          method_signature = method.attrib["signature"]
          method_id = "{}.{}{}".format(class_name, method_name, method_signature)
          for line in method[0]:
            hits[(method_id, line.attrib["number"])] = int(line.attrib["hits"])
  return hits, covered_classes

def extend_columns(a, n):
  b = np.zeros((a.shape[0], a.shape[1]+n))
  b[:,:-n] = a
  return b

class bcolors:
  HEADER = '\033[95m'
  OKBLUE = '\033[94m'
  OKGREEN = '\033[92m'
  WARNING = '\033[93m'
  FAIL = '\033[91m'
  ENDC = '\033[0m'
  BOLD = '\033[1m'
  UNDERLINE = '\033[4m'
  
def coloring(msg, color):
  return f"{color}{msg}{bcolors.ENDC}"
