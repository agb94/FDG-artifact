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
docker exec fdg python3.6 main.py <pid> <vid> --tool evosuite --id <test_suite_id> --budget <query_budget(s)> --selection <FDG:alpha|Split|Cover|DDU|EntBug|Total|DDU|Add|RAPTER|TfD|FLINT|Prox|S3> --noise <noise_probability>
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

## Detailed Description

### RQ2: IFL Performance

The results for RQ2 show how the FL accuracy changes as new test cases are added to the test suite (Figure 5).
In our artifact, the following command shows how the rank of the faulty method changes when selecting 10 test cases for `Lang-1b` using the fault diagnosability metric `FDG:0.5` from the newly generated test suite `newTS`.
```shell
docker exec fdg python3.6 main.py Lang 1 --tool evosuite --id newTS --budget 10 --selection FDG:0.5 --noise 0.0
```

Example output (please note that the output can be different based on the random seed used in the test generation phase):
```
* selection metric: FDG:0.5
* subject: Lang-1b
* test suite: evosuite-newTS (/root/results/evosuite_test/newTS/Lang-1)
                        value
num_total_tests            33
num_failing_tests           1
num_lines                 112
num_suspicious_lines       38
num_total_methods          14
num_suspicious_methods      5
num_buggy_methods           1
********************************************
  Iter  Test                                                                                Fitness    Oracle    Response    Ranks
------  --------------------------------------------------------------------------------  ---------  --------  ----------  -------
     0  [('initial_test', 'org.apache.commons.lang3.math.NumberUtilsTest::TestLang747')]                                         5
     1  ('org/apache/commons/lang3/math/NumberUtils_ESTest.java', 'test27')                0.524161         1           1        2
     2  ('org/apache/commons/lang3/math/NumberUtils_ESTest.java', 'test18')                0.526924         1           1        2
     3  ('org/apache/commons/lang3/math/NumberUtils_ESTest.java', 'test19')                0.49969          1           1        1
     4  ('org/apache/commons/lang3/math/NumberUtils_ESTest.java', 'test16')                0.533589         1           1        1
     5  ('org/apache/commons/lang3/math/NumberUtils_ESTest.java', 'test23')                0.514621         1           1        1
     6  ('org/apache/commons/lang3/math/NumberUtils_ESTest.java', 'test26')                0.504069         1           1        1
     7  ('org/apache/commons/lang3/math/NumberUtils_ESTest.java', 'test24')                0.5004           1           1        1
     8  ('org/apache/commons/lang3/math/NumberUtils_ESTest.java', 'test22')                0.497579         1           1        1
     9  ('org/apache/commons/lang3/math/NumberUtils_ESTest.java', 'test21')                0.495339         1           1        1
    10  ('org/apache/commons/lang3/math/NumberUtils_ESTest.java', 'test20')                0.493514         1           1        1
```
You can see that the rank of the faulty method becomes higher (5 -> 1) as more test cases are added. Using this artifact, you can generate those results that support our findings in RQ2.

### RQ3: Robustness

To answer RQ3, we showed how much SBFL performance changes based on the different labelling error rates (Figure 6).
You can control the error rate (or noise probability) of the simulated human responses using the
`--noise <prop>` option of the `main.py` script. It will **randomly** flip the test oracle querying response
with a probability of `<prob>` at each iteration. 

```shell
# the noise probability is set to 0.3!
docker exec fdg python3.6 main.py Lang 1 --tool evosuite --id newTS --budget 10 --selection FDG:0.5 --noise 0.3
```

```
* selection metric: FDG:0.5
* subject: Lang-1b
* test suite: evosuite-newTS (/root/results/evosuite_test/newTS/Lang-1)
* 1 buggy methods:
--- org.apache.commons.lang3.math.NumberUtils.createNumber(Ljava/lang/String;)
* 1 failing tests
--- org.apache.commons.lang3.math.NumberUtilsTest::TestLang747
[] []
* 38 lines collected
* 112 lines collected
* 0/32 generated tests are failed in fixed version
                        value
num_total_tests            33
num_failing_tests           1
num_lines                 112
num_suspicious_lines       38
num_total_methods          14
num_suspicious_methods      5
num_buggy_methods           1
********************************************
  Iter  Test                                                                                Fitness    Oracle    Response    Ranks
------  --------------------------------------------------------------------------------  ---------  --------  ----------  -------
     0  [('initial_test', 'org.apache.commons.lang3.math.NumberUtilsTest::TestLang747')]                                         5
     1  ('org/apache/commons/lang3/math/NumberUtils_ESTest.java', 'test27')                0.524161         1           0        4
     2  ('org/apache/commons/lang3/math/NumberUtils_ESTest.java', 'test22')                0.610181         1           0        4
     3  ('org/apache/commons/lang3/math/NumberUtils_ESTest.java', 'test21')                0.636902         1           0        4
     4  ('org/apache/commons/lang3/math/NumberUtils_ESTest.java', 'test26')                0.625367         1           1        4
     5  ('org/apache/commons/lang3/math/NumberUtils_ESTest.java', 'test12')                0.601704         1           1        1
     6  ('org/apache/commons/lang3/math/NumberUtils_ESTest.java', 'test20')                0.581225         1           1        1
     7  ('org/apache/commons/lang3/math/NumberUtils_ESTest.java', 'test23')                0.567799         1           0        1
     8  ('org/apache/commons/lang3/math/NumberUtils_ESTest.java', 'test24')                0.571513         1           1        1
     9  ('org/apache/commons/lang3/math/NumberUtils_ESTest.java', 'test17')                0.56482          1           1        1
    10  ('org/apache/commons/lang3/math/NumberUtils_ESTest.java', 'test14')                0.559519         1           1        1
```
Now, the simulated human responses (`Response` column) are sometimes incorrect.
For example, in Iter 1, it simulates a wrong response answering that `test27` captures the incorrect behaviour of the program `Lang-1b` (`Reponse: 0`), even though the test case `test27` does not reveal any incorrect behaviour of the program (`Oracle: 1`). You can see that the rank of faulty elements becomes `1` after adding more test cases compared to the previous example.

Using this artifact, you can simulate the error in the human labelling step (in Figure 3), and consequently evaluate the robustness of any fault diagnosability metric. 


### RQ4: Parameter Tuning

```shell
docker exec fdg python3.6 main.py Lang 1 --tool evosuite --id newTS --budget 10 --selection FDG:<alpha> --noise 0.0
```

Our proposed fault diagnosability metric `FDG` has one parameter `alpha` that controls the relative weights of `Split` and `Cover` which are subcomponents of `FDG`.

RQ4 concerns how `alpha` affects the performance of `FDG`.

In this artifact, you can easily control the alpha value uing the `--selection` option of `main.py`, e.g., `--selection FDG:0.4` or `--selection FDG:0.8`. 

