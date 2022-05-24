# FDG: A Precise Measurement of Fault Diagnosability Gain of Test Cases

[![DOI](https://zenodo.org/badge/489423364.svg)](https://zenodo.org/badge/latestdoi/489423364)

This is an artifact accompanying the paper **FDG: A Precise Measurement of
Fault Diagnosability Gain of Test Cases** (ISSTA 2022).

## Requirements
- H/W
  - A processor with the linux/amd64 architecture (only for RQ2-4)
- S/W
  - 🐍 Python 3.9.1
    - Installing dependencies
      ```shell
      pip install -r requirements.txt
      ```
      - (In OS X) If `libshm.dylib` is not loaded, please install `libomp`.
        ```shell
        brew install libomp
        ```
  - 🐳 docker (only for RQ2-4)

### Package structure
```bash
├── Defects4J-human-written-tests/ # RQ1
│   ├── utils/
│   │   ├── d4j.py
│   │   ├── metrics.py
│   │   └── FL.py
│   ├── output/
│   ├── data/
│   ├── simulate.py
│   └── README.md
├── Defects4J-generated-tests/     # RQ2-RQ4
│   ├── docker/
│   │  ├── resources/
│   │  └── Dockerfile
│   └── README.md
└── README.md
```

Following files contain more details.
- For RQ1: [`Defects4J-human-written-tests/README.md`](./Defects4J-human-written-tests/README.md)
- For RQ2-4: [`Defects4J-generated-tests/README.md`](./Defects4J-generated-tests/README.md)
