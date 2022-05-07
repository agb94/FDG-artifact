import numpy as np
import torch
import argparse
import json
import os
from utils.metrics import *
from utils.d4j import load
from utils.FL import *
from tqdm import tqdm
from sklearn.preprocessing import binarize

def simulate(X, y, initial_tests, spec_cache=None, score_cache=None,
             fitness_function=FDG, sbfl_formula=ochiai, weight=ochiai):
    N, M = X.shape

    tests = list(initial_tests[:])

    if spec_cache is None:
        spec_cache = spectrum(X[tests],y[tests])

    if score_cache is None:
        score_cache = sbfl_formula(*spec_cache)

    if sbfl_formula == weight:
        weights = score_cache[:]
    else:
        weights = weight(*spec_cache)

    # Optimization
    if fitness_function in [Split, FDG]:
        _, cX = torch.unique(X[tests], return_inverse=True, sorted=False, dim=1)
        cX = torch.unsqueeze(cX, 0)
    elif fitness_function == DDU_fast:
        _, cX = torch.unique(X[tests], return_inverse=True, sorted=False, dim=1)
        cX = torch.unsqueeze(cX, 0)
        unique_activities, activity_counts = torch.unique(X[tests],
            return_counts=True, sorted=False, dim=0)
    elif fitness_function == S3:
        target = torch.sum(X[tests], dim=0) > 0

    if fitness_function in [RAPTER, FLINT, EntBug]:
        comparator = lambda a, b: a < b
    else:
        comparator = lambda a, b: a > b

    best_fitness, selected_tests = None, None

    for i in tqdm(range(N), colour='green'):
        if i in tests:
            continue
        if fitness_function in [Split, FDG]:
            fitness = fitness_function(cX, X[i], w=weights)
        elif fitness_function == S3:
            fitness = fitness_function(X[tests, :], X[i], w=weights, 
                target=target, y=y[tests])
        elif fitness_function == FLINT:
            fitness = fitness_function(X[tests, :], X[i], spectrum=spec_cache, 
                y=y[tests])
        elif fitness_function == Prox:
            fitness = fitness_function(X[tests, :], X[i], y=y[tests])
        elif fitness_function == DDU_fast:
            fitness = fitness_function(X[tests, :], X[i], cX=cX, 
                unique_activities=unique_activities, 
                activity_counts=activity_counts)
        else:
            fitness = fitness_function(X[tests, :], X[i], w=weights)

        if best_fitness is None or comparator(fitness, best_fitness):
            # first ascent
            best_fitness = fitness
            selected_tests = [i]

    # Update Spectrum
    if selected_tests is not None:
        e_p, n_p, e_f, n_f = spec_cache
        for t in selected_tests:
            if y[t] == 0:
                # Fail
                e_f += X[t]
                n_f += (1 - X[t])
            else:
                # Pass
                e_p += X[t]
                n_p += (1 - X[t])
        spec_cache = e_p, n_p, e_f, n_f
        score_cache = sbfl_formula(*spec_cache)

    return selected_tests, best_fitness, spec_cache, score_cache

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--pid', '-p', type=str, default=None)
    parser.add_argument('--start', '-s', type=int, default=None)
    parser.add_argument('--end', '-e', type=int, default=None)
    parser.add_argument('--output', '-o', type=str, default="output.json")
    parser.add_argument('--metric', '-m', type=str, default="FDG")
    parser.add_argument('--weight', '-w', type=str, default="ochiai")
    parser.add_argument('--formula', '-f', type=str, default="ochiai")
    parser.add_argument('--iter', type=int, default=20)
    args = parser.parse_args()

    formula = eval(args.formula)
    weight = eval(args.weight)
    fitness_function = eval(args.metric)

    """
    Defects4J Simulation
    """
    excluded = {
        'Lang': [2, 23, 56],
        'Chart': [],
        'Time': [21],
        'Math': [],
        'Closure': [63, 93]      
    }
    projects = {
        'Lang':    (1, 65),
        'Chart':   (1, 26),
        'Time':    (1, 27),
        'Math':    (1, 106),
        'Closure': (1, 133)
    }

    if args.pid:
        start = args.start if args.start else projects[args.pid][0]
        end = args.end if args.end else projects[args.pid][1]
        
        projects = {
            args.pid: (start, end)
        }

    simulation_results = {}

    try:
        for p in projects:
            start, end = projects[p]
            for n in range(start, end + 1):
                if n in excluded[p]:
                    # check if excluded
                    continue

                key = f"{p}-{n}"
                loaded_data = load(p, n)
                if loaded_data is None:
                    simulation_results[key] = None
                    continue

                X, y, methods, testcases, faulty_methods = loaded_data
                num_failing_tests = int(np.sum(y == 0))
                print(f"[{key}] # failing tests in the test suite: {num_failing_tests}")

                # initialize
                simulation_results[key] = []
                starting_index = 0

                X = torch.tensor(binarize(X), dtype=torch.float32)
                y = torch.tensor(y, dtype=torch.float32)

                for ti in range(starting_index, num_failing_tests):
                    results = {
                        # the indices of selected test cases
                        "tests": [],
                        # the rankings of faulty methods at each iteration
                        "ranks": [],
                        "fitness_history": [],
                        "full_ranks": None
                    }

                    # for faster fault localization
                    spec_cache = None  # spectrum cache
                    score_cache = None # FL score cache

                    failing_idx = np.where(y == 0)[0].tolist()
                    initial_tests = failing_idx[ti:ti+1]

                    spec_cache = spectrum(X[initial_tests], y[initial_tests])
                    score_cache = formula(*spec_cache)
                    ranks = get_ranks_of_faulty_elements(methods, score_cache,
                        faulty_methods, level=0)
                    full_ranks = get_ranks_of_faulty_elements(methods,
                        formula(*spectrum(X, y)), faulty_methods, level=0)
                    results["tests"].append(initial_tests)
                    results["ranks"].append(ranks)
                    print(f"[{key}] Starting iteration with a failing test {[testcases[t] for t in initial_tests]} ({ti + 1}/{num_failing_tests}).")
                    print(f"[{key}] With the initial test, faulty method(s) {faulty_methods} is (are) ranked at {ranks}.")
                    fitness = float(fitness_function(
                        X[initial_tests], w=score_cache, cX=X[initial_tests]))
                    results["fitness_history"].append(fitness)
                    results["full_ranks"] = full_ranks

                    while not len(results["ranks"]) > args.iter:
                        selected, fitness, spec_cache, score_cache = simulate(
                            X, y, sum(results["tests"], []),
                            spec_cache=spec_cache,
                            score_cache=score_cache,
                            fitness_function=fitness_function,
                            weight=weight,
                            sbfl_formula=formula)

                        if selected == None:
                            break

                        ranks = get_ranks_of_faulty_elements(
                            methods, score_cache, faulty_methods, level=0)
                        results["tests"].append(selected)
                        results["ranks"].append(ranks)
                        results["fitness_history"].append(float(fitness))
                        print(f"[{key}] Selected test: {[testcases[t] for t in selected]} (score: {fitness:.5f}). Now the faulty methods are ranked at {ranks}.")

                    simulation_results[key].append(results)

    except KeyboardInterrupt as e:
        print(e)
    finally:
        simulation_results[key].append(results)
        with open(args.output, "w") as f:
            json.dump(simulation_results, f, sort_keys=True,
                ensure_ascii=False, indent=4)
        print(f"* Results are saved to {args.output}")