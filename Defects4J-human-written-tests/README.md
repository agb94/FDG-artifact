# Prioritisation Simulation (RQ1)

## Development Environment 
- Python 3.9.1
- Installing dependencies
  ```shell
  pip install -r requirements.txt
  ```
  - (OS X) If `libshm.dylib` is not loaded, please install `libomp`.
    ```shell
    brew install libomp
    ```

## Precomputed Simulation Results

The precomputed results are available in the directory `output/`.
- `tests`: the index of the test case (following the order in the coverage matrix) selected at each iteration
- `ranks`: the rank of faulty methods at each iteration
- `fitness_history`: the fitness of the selected test cases at each iteration
- `full_ranks`: the rank of faulty methods when using all available test cases

Please note that the recorded fitness values in `FDG.json` are twice the original values, e.g., `Split+Cover`, not `0.5*(Split+Cover)`. Since the implementation has been fixed, you don't need to consider this in the replication step.

## Getting Started

### **Step 1**. Extract coverage files
Our simulation needs the coverage matrix of faulty programs.
Due to the storage limit, we have included the coverage matrix of only the `Lang` project. Before running the simulation, you need to extract the files:

```shell
cd data/coverage_matrix 
sh extract.sh Lang
cd ../../
```

### **Step 2**. Run the simulation

Use the following command to run the simulation for bugs `<project>-<start>b` ~ `<project>-<end>b`:
```shell
python simulate.py --pid <project> --start <start> --end <end> --output <path_to_output> --formula <ochiai|wong2|dstar|op2|tarantula> --metric <diagnosability_metric> --iter <num_iterations>
```
The results will be save to `<path_to_output>`.

For example, if you want to run the simulation for `Lang-3b`, ..., `Lang-5b`, type:
```shell
python simulate.py --pid Lang --start 3 --end 5 --output output.json --formula ochiai --metric FDG --iter 5
```
It will take some time. If you want to accelerate execution using GPU, please install PyTorch with CUDA.


## Detailed Description

The generated .json output file contains the information about how the ranks of faulty methods are changed whenever a new test case is added. For example, consider the following data point in output/FDG.json:

```json
"Lang-1": [
    {
        "fitness_history": "... truncated ...",
        "full_ranks": [
            1
        ],
        "ranks": [
            [5], [2], [2], [1], [1], [1], [1], [1], [1], [1], [1]
        ],
        "tests": [
            [645], [340], [213], [982], [417], [1698], [735], [975], [1332], [1353], [1551]
        ]
    }
]
```

When we use only the initial failing test case `645` (FYI, this is the index of the test case in the columns of the input coverage matrix) for SBFL, the faulty method is ranked 5th place. When we select three more test cases 340, 213, 982 using the diagnosability metric `FDG` and add them to the test suite, the rank of the faulty method becomes 1.

In our paper, Figure 2 and Table 2 shows how the ranks of the faulty method are changed depending on the choice of a fault diagnosability metric. Using the data in `output/,` you can reproduce the `mAP` and `acc@n` results in Figure 2 and Table 2.
