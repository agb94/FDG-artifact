import argparse, os
from utils.cobertura import *

if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument('coverage_dir', type=str)
  parser.add_argument('save_dir', type=str)
  args = parser.parse_args()

  classes = {}
  for f in os.listdir(args.coverage_dir):
    if not f.endswith(".xml"):
      continue
    coverage_file = os.path.join(args.coverage_dir, f)
    hits = get_hits(coverage_file)
    grouped = hits.groupby('class')['method'].apply(set)
    for cls, methods in grouped.iteritems():
      if cls in classes:
        classes[cls].update(methods)
      else:
        classes[cls] = methods
  num_total_methods = .0
  for cls in classes:
    with open(os.path.join(args.save_dir, cls), 'w') as f:
      f.write("\n".join(list(classes[cls])))
      num_total_methods += len(list(classes[cls]))

  for cls in classes:
    ratio = len(list(classes[cls])) / num_total_methods
    with open(os.path.join(args.save_dir, cls + '.budget'), 'w') as f:
      f.write(str(ratio))
