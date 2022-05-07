import xml.etree.ElementTree as ET
import pandas as pd

def parse(path):
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

def get_hits(path):
  tree = ET.parse(path)
  root = tree.getroot()
  packages = root[1]
  data = []
  for package in packages:
    for classes in package:
      for _class in classes:
        class_name = _class.attrib["name"]
        for method in _class[0]:
          method_name = method.attrib["name"]
          method_signature = method.attrib["signature"]
          method_id = "{}.{}{}".format(class_name, method_name, method_signature)
          for line in method[0]:
            hits = int(line.attrib["hits"])
            if hits > 0:
              data.append([
                method_id,
                (method_id, line.attrib["number"]),
                class_name,
                method_name + method_signature,
                line.attrib["number"],
                hits
              ])
  return pd.DataFrame(data, columns=["mid", "lid", "class", "method", "line", "hits"])
