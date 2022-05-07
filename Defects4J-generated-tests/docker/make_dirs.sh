[ ! -d results ] && mkdir results
for dirname in "evosuite_config" "evosuite_coverage" "evosuite_oracles" "evosuite_report" "evosuite_test" "metadata"; do
  [ ! -d results/$dirname ] && mkdir results/$dirname && echo "Created a new directory: results/$dirname"
done