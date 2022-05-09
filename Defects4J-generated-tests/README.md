# Iterative Fault Localization (RQ2-RQ4)
## Prerequisite
- docker

## Getting Started

- 🚨 **Please make sure that the docker daemon is running on your machine.** If not, you will encounter the error: `Cannot connect to the Docker daemon at unix:///var/run/docker.sock`
- 🚨 Our docker image `agb94/fdg` only supports the  `linux/amd64` architecture. If the architecture of your processor is `arm64`, e.g. Apple sillicion, please try with another machine.

### **Step 0**. Are you busy now?
- Not really -> Goto **Step 1**
- Yes -> Goto **Step 4**

### **Step 1**. Setup Docker

```shell
cd docker/
docker pull agb94/fdg
# If you want to build the docker image from scratch, type:
# docker build --tag agb94/fdg .
# it may take several hours to complete
sh make_dirs.sh
docker run -dt --volume $(pwd)/resources/d4j_expr:/root/workspace --volume $(pwd)/results:/root/results --name fdg agb94/fdg
```

This will
- load the docker image `fdg:amd64`,
- create a docker container named `fdg`,
- and create a new Bash session in the container `fdg`

Now, go to **Step 2**.

### **Step 2**. Generate test cases using EvoSuite

The following command will generate the regression test cases for `<pid>-<vid>b` (ex. Lang-1b) in Defects4J using EvoSuite. This will take a while.

```bash
docker exec fdg sh generate_test.sh <pid> <vid> evosuite <test_suite_id> <time_budget_in_sec> <random_seed>
# ex) docker exec fdg sh generate_test.sh Lang 1 evosuite newTS 60 0
```

Result files:
- `./results/evosuite_test/<test_suite_id>/<pid>-<vid>`
  - The generated test suite
- `./results/evosuite_coverage/<test_suite_id>/<pid>-<vid>/`
  - The coverage of the generated test cases
  - Use `pandas.read_pickle` to load the coverage files.
- `./results/evosuite_report/<test_suite_id>/statistics.<pid>-<vid>.csv`
  - The EvoSuite report
- `./results/evosuite_oracle/<test_suite_id>/<pid>-<vid>.failing_tests`
  - A set of test cases that show different behaviours in the buggy and fixed versions
  - The test case oracles are obtained using the fixed version of the program, i.e., `<pid>-<vid>f`
  - The file can be empty if there is no test case capturing the faulty behaviour! It's not an error.

Go to **Step 3**.

### **Step 3**. Simulate Iterative FL
The following command will simulate the iterative SBFL scenario for `<pid>-<vid>b` using the EvoSuite-generated test suite with the id `<test_suite_id>`. You can set the noise probability in oracle querying using the `--noise` option.
```bash
docker exec fdg python3.6 main.py <pid> <vid> --tool evosuite --id <test_suite_id> --budget <query_budget> --selection <diagnosability_metric> --noise <noise_probability>
# ex) docker exec fdg python3.6 main.py Lang 1 --tool evosuite --id newTS --budget 10 --selection FDG:0.5 --noise 0.0
```
- The localisation results will be pickled and saved to `./results/localisation/<test_suite_id>/<pid>-<vid>-*`.
  - Use `pandas.read_pickle` to load the files.
  - `<pid>-<vid>-summary.pkl` contains the basic information of each buggy subject
  - `<pid>-<vid>-oracle.pkl` contains the ground-truth oracle of the generated test cases
    - `0`: fault-revealing test, `1`: non fault-revealing test
  - `<pid>-<vid>-oracle.pkl` records the 2-D coverage matrix of the generated test cases (columns: lines, index: test cases)
    - `0`: not covered
    - `1`: covered
  - `<pid>-<vid>-ranks-<diagnosability_metric>.pkl` contains the FL scores/ranks of methods at each iteration when the test case is selected based on `<diagnosability_metric>`
  - `<pid>-<vid>-tests-<diagnosability_metric>.pkl` contains the name of the selected test case and its fitness value at each iteration.

Go to **Step 5** after the simulation is done.

### **Step 4**. This is a quick recipe:

```shell
cd docker/
docker pull agb94/fdg
sh make_dirs.sh
docker run -dt --volume $(pwd)/resources/d4j_expr:/root/workspace --volume $(pwd)/results:/root/results --name fdg agb94/fdg
docker exec fdg sh generate_test.sh Lang 1 evosuite newTS 60 0
docker exec fdg python3.6 main.py Lang 1 --tool evosuite --id newTS --budget 10 --selection FDG:0.5 --noise 0.0
```
The results will be saved to `./results`.

Go to **Step 5** after the simulation is done.

### **Step 5**. Clean up the docker container

```shell
docker kill fdg # kill the container
docker rm fdg   # remove the container
```
