

import os
import re
import argparse
import pandas as pd
from tqdm import tqdm

FL_DIR = f"./docker/results/localisation/"

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('test_suite_id', type=str)
    parser.add_argument('time_budget', type=int)
    parser.add_argument('metric', type=str)
    parser.add_argument('--max-query-budget', '-q', type=int, default=10)
    parser.add_argument('--output', '-o', type=str, default="./output.pkl")
    args = parser.parse_args()

    ts_id = args.test_suite_id
    time_budget = args.time_budget
    metric = args.metric
    query_budgets = list(range(args.max_query_budget + 1))
    result_dir = os.path.join(FL_DIR, ts_id)
    output_path = args.output

    rows = []
    for filename in tqdm(os.listdir(result_dir), colour="green"):
        if filename.startswith("."):
            continue

        if f"ranks-{metric}" not in filename:
            continue

        groups = re.search("(\w+)-(\d+)-ranks", filename)
        if not groups:
            continue
        project, version = groups.group(1), groups.group(2)

        groups = re.search("noise_(\d\.\d)\.pkl", filename)
        if groups:
            noise_prob = float(groups.group(1))
            if noise_prob not in noise_probs:
                continue
        else:
            noise_prob = 0.0
        
        ranks = pd.read_pickle(
            os.path.join(result_dir, filename)
        )
        for query_budget in range(max(query_budgets) + 1):
            if f"rank-{query_budget}" in ranks.columns:
                buggy_ranks = ranks.loc[
                    ranks['is_buggy'] == True,
                    f"rank-{query_budget}"].values
            for buggy_rank in buggy_ranks:
                if query_budget in query_budgets:
                    rows.append(
                        [ts_id, project, version, time_budget, query_budget, noise_prob, buggy_rank]
                    )
    df = pd.DataFrame(
        data=rows,
        columns=['Test Suite', 'Project', 'Version',
            'Time Budget', 'Query Budget', 'Noise Probability', 'Rank']
    )

    print(df)
    df.to_pickle(output_path)
    print(f"Saved to {output_path}")