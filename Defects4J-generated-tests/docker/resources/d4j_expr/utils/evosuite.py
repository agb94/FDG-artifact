import re

EVOSUITE_PATTERNS = {
  "tc_no": r"//Test case number: (\d+)",
  "line_goal": r"\* Goal \d+\. ([^:]+): Line (\d+)",
  "cov_end": "*/",
}

def test_path_to_class_name(test_path):
    return test_path[:-5].replace('/', '.')

def class_name_to_test_path(class_name):
    return class_name.replace('.', '/')+'.java'

def parse(path):
  coverages = {}
  tests = {}
  with open(path, "r") as test_file:
    test_name = None
    cov_read = False
    for l in test_file:
      stripped = l.strip()
      m = re.search(EVOSUITE_PATTERNS["tc_no"], stripped)
      if m:
        tc_no = m.group(1)
        test_name = "test" + str(tc_no)
        coverages[test_name] = []
        tests[test_name] = []
        cov_read = True
        continue
      if not cov_read:
        if test_name and l.rstrip() != "}":
          tests[test_name].append(l)
        continue
      if stripped == EVOSUITE_PATTERNS["cov_end"]:
        cov_read = False
        continue
      m = re.search(EVOSUITE_PATTERNS["line_goal"], stripped)
      if m:
        coverages[test_name].append((m.group(1), m.group(2)))
  for test_name in tests:
    tests[test_name] = "".join(tests[test_name]).strip()
  return coverages, tests

def carve(path, test_names):
  tests = []
  with open(path, "r") as test_file:
    tc_no = None
    test_remove = False
    for l in test_file:
      stripped = l.strip()
      m = re.search(EVOSUITE_PATTERNS["tc_no"], stripped)
      if m:
        tc_no = m.group(1)
        test_name = "test" + str(tc_no)
        if test_name not in map(str, test_names):
          test_remove = True
        else:
          test_remove = False
      if test_remove and l.rstrip() != "}":
        continue
      tests.append(l)
  return "".join(tests)

def get_test_by_line(path, line):
  with open(path, "r") as test_file:
    tc_no = None
    line_counter = 0
    for l in test_file:
      line_counter += 1
      stripped = l.strip()
      m = re.search(EVOSUITE_PATTERNS["tc_no"], stripped)
      if m:
        tc_no = m.group(1)
      if line_counter == line:
        return tc_no
  return None
