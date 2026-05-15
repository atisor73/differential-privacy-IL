from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd

from dp_noise_pipeline import (
    DEFAULT_EPSILONS,
    PROCESSED_DATA_DIR,
    RACE_COLS,
    add_opendp_laplace_noise,
    aggregate_noised_blocks_to_higher_levels,
    epsilon_output_dir,
    epsilon_outputs_exist,
    format_epsilon,
    load_base_data,
    log,
    progress_iter,
    save_pipeline_outputs,
    summarize_saved_outputs,
)

DEFAULT_OUTPUT_ROOT = PROCESSED_DATA_DIR / "DP_noise_constrained"


def project_to_simplex(values: np.ndarray, target_sum: float) -> np.ndarray:
    """
    Euclidean projection onto the nonnegative simplex:
    {x : x_i >= 0, sum_i x_i = target_sum}.

    This keeps the adjusted race vector as close as possible to the raw noisy
    race vector while enforcing a fixed per-block total.
    """
    if target_sum <= 0:
        return np.zeros_like(values, dtype=float)

    sorted_values = np.sort(values)[::-1]
    cssv = np.cumsum(sorted_values)
    rho_candidates = sorted_values - (cssv - target_sum) / (np.arange(len(values)) + 1) > 0
    rho = np.nonzero(rho_candidates)[0][-1]
    theta = (cssv[rho] - target_sum) / (rho + 1)
    return np.maximum(values - theta, 0.0)


def round_preserving_total(values: np.ndarray, target_total: int) -> np.ndarray:
    """
    Convert a nonnegative real-valued vector to integers while preserving its
    target total using largest-remainder rounding.
    """
    if target_total <= 0:
        return np.zeros_like(values, dtype=int)

    floors = np.floor(values).astype(int)
    remainder = target_total - int(floors.sum())

    if remainder <= 0:
        return floors

    fractions = values - floors
    order = np.argsort(-fractions, kind="stable")
    rounded = floors.copy()
    rounded[order[:remainder]] += 1
    return rounded


def postprocess_block_race_counts_constrained(
    df: pd.DataFrame,
    cols: list[str] = RACE_COLS,
) -> pd.DataFrame:
    """
    Project each block's noisy race vector onto a nonnegative integer vector
    whose entries sum to a single block-level target total.

    The target total is the clipped-and-rounded noisy population total, rather
    than the sum of independently clipped race cells. This avoids the strong
    upward bias created by flooring every negative race count separately.

    This is TDA-inspired constrained postprocessing, but it is not a full
    top-down optimization across the entire geography hierarchy.
    """
    out = df.copy()
    noisy_cols = [f"noisy_{col}" for col in cols]
    noisy_matrix = out[noisy_cols].to_numpy(dtype=float, copy=True)
    target_totals = np.clip(np.rint(out["noisy_pop"].to_numpy(dtype=float)), a_min=0, a_max=None).astype(int)
    adjusted = np.zeros_like(noisy_matrix, dtype=int)

    for idx, (row_values, target_total) in enumerate(zip(noisy_matrix, target_totals)):
        projected = project_to_simplex(row_values, float(target_total))
        adjusted[idx, :] = round_preserving_total(projected, int(target_total))

    for col_index, col in enumerate(cols):
        out[f"adj_{col}"] = adjusted[:, col_index]

    out["adj_pop"] = adjusted.sum(axis=1)
    return out


def run_block_dp_pipeline_constrained(
    block_df: pd.DataFrame,
    tract_df: pd.DataFrame,
    county_df: pd.DataFrame,
    state_df: pd.DataFrame,
    epsilon: float,
    verbose: bool = False,
) -> dict[str, pd.DataFrame]:
    epsilon_label = format_epsilon(epsilon)
    log(verbose, f"[epsilon={epsilon_label}] adding OpenDP Laplace noise to block race counts")
    block_noised = add_opendp_laplace_noise(block_df, epsilon=epsilon, cols=RACE_COLS)

    log(verbose, f"[epsilon={epsilon_label}] constrained block postprocessing")
    block_adj = postprocess_block_race_counts_constrained(block_noised, cols=RACE_COLS)

    log(verbose, f"[epsilon={epsilon_label}] aggregating blocks to tract/county/state")
    outputs = aggregate_noised_blocks_to_higher_levels(
        block_adj=block_adj,
        tract_df=tract_df,
        county_df=county_df,
        state_df=state_df,
        cols=RACE_COLS,
    )

    for level_df in outputs.values():
        level_df["epsilon"] = epsilon

    return outputs


def run_epsilons(
    epsilons: list[float] = DEFAULT_EPSILONS,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    verbose: bool = True,
    use_tqdm: bool = True,
) -> tuple[pd.DataFrame, dict[float, dict[str, pd.DataFrame]]]:
    start = time.time()
    log(verbose, f"Loading base data for {len(epsilons)} epsilon run(s)")
    block_df, tract_df, county_df, state_df = load_base_data()
    log(
        verbose,
        "Loaded base data: "
        f"{len(block_df):,} blocks, {len(tract_df):,} tracts, {len(county_df):,} counties, {len(state_df):,} states",
    )

    all_results: dict[float, dict[str, pd.DataFrame]] = {}
    output_root.mkdir(parents=True, exist_ok=True)

    for epsilon in progress_iter(epsilons, use_tqdm, "Constrained OpenDP epsilons"):
        epsilon_start = time.time()
        epsilon_label = format_epsilon(epsilon)
        if epsilon_outputs_exist(output_root, epsilon):
            log(verbose, f"Skipping epsilon={epsilon_label}; outputs already exist in {epsilon_output_dir(output_root, epsilon)}")
            continue

        log(verbose, f"Starting epsilon={epsilon_label}")
        results = run_block_dp_pipeline_constrained(
            block_df=block_df,
            tract_df=tract_df,
            county_df=county_df,
            state_df=state_df,
            epsilon=epsilon,
            verbose=verbose,
        )

        epsilon_dir = epsilon_output_dir(output_root, epsilon)
        save_pipeline_outputs(results, epsilon_dir)
        all_results[epsilon] = results
        log(verbose, f"[epsilon={epsilon_label}] saved CSVs to {epsilon_dir}")
        log(verbose, f"Finished epsilon={epsilon_label} in {time.time() - epsilon_start:.1f}s")

    summary_df = summarize_saved_outputs(output_root, epsilons)
    summary_df.to_csv(output_root / "DP_noise_error_summary.csv", index=False)
    log(verbose, f"Saved summary CSV to {output_root / 'DP_noise_error_summary.csv'}")
    log(verbose, f"Completed all epsilon runs in {time.time() - start:.1f}s")

    return summary_df, all_results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate OpenDP noised outputs with constrained block-level "
            "postprocessing that preserves a single adjusted total per block."
        )
    )
    parser.add_argument(
        "--epsilons",
        nargs="+",
        type=float,
        default=DEFAULT_EPSILONS,
        help="Space-separated epsilon values to run.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Directory where per-epsilon outputs should be saved.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-stage log messages.",
    )
    parser.add_argument(
        "--no-tqdm",
        action="store_true",
        help="Disable tqdm progress bars.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary_df, _ = run_epsilons(
        epsilons=args.epsilons,
        output_root=args.output_root,
        verbose=not args.quiet,
        use_tqdm=not args.no_tqdm,
    )
    print(f"Saved constrained outputs to {args.output_root}")
    print(summary_df)


if __name__ == "__main__":
    main()
