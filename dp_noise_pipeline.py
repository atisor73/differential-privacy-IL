from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import opendp.prelude as dp
import pandas as pd

try:
    from tqdm.auto import tqdm
except ImportError:  # pragma: no cover - optional dependency
    tqdm = None

dp.enable_features("contrib")

RACE_COLS = ["white", "black", "asian", "other"]
DEFAULT_EPSILONS = [0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0, 15.0, 19, 25]
PROCESSED_DATA_DIR = Path("data/processed_data")
DEFAULT_OUTPUT_ROOT = PROCESSED_DATA_DIR / "DP_noise"
PROCESSED_BLOCK_PATH = PROCESSED_DATA_DIR / "DF_IL_2010_BLOCK.csv"
PROCESSED_TRACT_PATH = PROCESSED_DATA_DIR / "DF_IL_2010_TRACT.csv"
PROCESSED_COUNTY_PATH = PROCESSED_DATA_DIR / "DF_IL_2010_COUNTY.csv"
PROCESSED_STATE_PATH = PROCESSED_DATA_DIR / "DF_IL_2010_STATE.csv"
RAW_DATA_PATH = Path("data/il_pl2010_b/il_pl2010_b.csv")
RAW_USECOLS = [
    "STATE",
    "COUNTY",
    "TRACT",
    "BLOCK",
    "P0010001",
    "P0010003",
    "P0010004",
    "P0010005",
    "P0010006",
    "P0010007",
    "P0010008",
    "P0010009",
]


def format_epsilon(epsilon: float) -> str:
    return f"{epsilon:g}"


def epsilon_output_dir(output_root: Path, epsilon: float) -> Path:
    return output_root / f"epsilon_{format_epsilon(epsilon)}"


def progress_iter(items, enabled: bool, description: str):
    if enabled and tqdm is not None:
        return tqdm(items, desc=description)
    return items


def log(enabled: bool, message: str) -> None:
    if enabled:
        print(message, flush=True)


def load_base_data(raw_data_path: Path = RAW_DATA_PATH) -> tuple[pd.DataFrame, ...]:
    processed_paths = [
        PROCESSED_BLOCK_PATH,
        PROCESSED_TRACT_PATH,
        PROCESSED_COUNTY_PATH,
        PROCESSED_STATE_PATH,
    ]
    if all(path.exists() for path in processed_paths):
        block_df = pd.read_csv(PROCESSED_BLOCK_PATH, dtype={"geoid": "string", "parent_geoid": "string"})
        tract_df = pd.read_csv(PROCESSED_TRACT_PATH, dtype={"geoid": "string", "parent_geoid": "string"})
        county_df = pd.read_csv(PROCESSED_COUNTY_PATH, dtype={"geoid": "string", "parent_geoid": "string"})
        state_df = pd.read_csv(PROCESSED_STATE_PATH, dtype={"geoid": "string"})
        if (
            block_df["geoid"].is_unique
            and tract_df["geoid"].is_unique
            and county_df["geoid"].is_unique
            and state_df["geoid"].is_unique
        ):
            return block_df, tract_df, county_df, state_df

    df_raw = pd.read_csv(
        raw_data_path,
        usecols=RAW_USECOLS,
        dtype={
            "STATE": "string",
            "COUNTY": "string",
            "TRACT": "string",
            "BLOCK": "string",
        },
    )

    df_raw["white"] = df_raw["P0010003"]
    df_raw["black"] = df_raw["P0010004"]
    df_raw["asian"] = df_raw["P0010006"]
    df_raw["other"] = df_raw["P0010005"] + df_raw["P0010007"] + df_raw["P0010008"] + df_raw["P0010009"]
    df_raw["true_pop"] = df_raw["P0010001"]

    df_raw["state_geoid"] = df_raw["STATE"]
    df_raw["county_geoid"] = df_raw["STATE"] + df_raw["COUNTY"]
    df_raw["tract_geoid"] = df_raw["STATE"] + df_raw["COUNTY"] + df_raw["TRACT"]
    df_raw["block_geoid"] = df_raw["STATE"] + df_raw["COUNTY"] + df_raw["TRACT"] + df_raw["BLOCK"]

    block_df = (
        df_raw[
            ["block_geoid", "tract_geoid", "true_pop"] + RACE_COLS
        ]
        .rename(columns={"block_geoid": "geoid", "tract_geoid": "parent_geoid"})
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0)
    )

    tract_df = (
        df_raw.groupby(["tract_geoid", "county_geoid"], as_index=False)[["true_pop"] + RACE_COLS]
        .sum()
        .rename(columns={"tract_geoid": "geoid", "county_geoid": "parent_geoid"})
    )

    county_df = (
        df_raw.groupby(["county_geoid", "state_geoid"], as_index=False)[["true_pop"] + RACE_COLS]
        .sum()
        .rename(columns={"county_geoid": "geoid", "state_geoid": "parent_geoid"})
    )

    state_df = (
        df_raw.groupby(["state_geoid"], as_index=False)[["true_pop"] + RACE_COLS]
        .sum()
        .rename(columns={"state_geoid": "geoid"})
    )

    return block_df, tract_df, county_df, state_df


def add_opendp_laplace_noise(
    df: pd.DataFrame,
    epsilon: float,
    cols: list[str] = RACE_COLS,
) -> pd.DataFrame:
    """
    Add independent Laplace noise to each race count using OpenDP.

    Sensitivity is 1 per cell query, so Laplace scale is 1 / epsilon.
    """
    if epsilon <= 0:
        raise ValueError("epsilon must be positive")

    out = df.copy()
    scale = 1.0 / epsilon

    measurement = dp.m.make_laplace(
        dp.vector_domain(dp.atom_domain(T=float, nan=False)),
        dp.l1_distance(T=float),
        scale=scale,
    )

    for col in cols:
        out[f"noisy_{col}"] = measurement(out[col].astype(float).tolist())

    out["noisy_pop"] = out[[f"noisy_{col}" for col in cols]].sum(axis=1)
    out["epsilon"] = epsilon
    return out


def postprocess_block_race_counts(
    df: pd.DataFrame,
    cols: list[str] = RACE_COLS,
) -> pd.DataFrame:
    """
    Clip noisy counts at zero, round to integers, and recompute population totals.
    """
    out = df.copy()

    for col in cols:
        noisy_col = f"noisy_{col}"
        adj_col = f"adj_{col}"
        out[adj_col] = out[noisy_col].clip(lower=0).round().astype(int)

    out["adj_pop"] = out[[f"adj_{col}" for col in cols]].sum(axis=1)
    return out


def aggregate_noised_blocks_to_higher_levels(
    block_adj: pd.DataFrame,
    tract_df: pd.DataFrame,
    county_df: pd.DataFrame,
    state_df: pd.DataFrame,
    cols: list[str] = RACE_COLS,
) -> dict[str, pd.DataFrame]:
    """
    Aggregate adjusted block counts upward using the existing geography hierarchy.
    """
    adj_cols = [f"adj_{col}" for col in cols]

    tract_lookup = tract_df[["geoid", "parent_geoid", "true_pop"] + cols].copy()
    county_lookup = county_df[["geoid", "parent_geoid", "true_pop"] + cols].copy()
    state_lookup = state_df[["geoid", "true_pop"] + cols].copy()

    tract_adj = (
        block_adj.groupby("parent_geoid", as_index=False)[adj_cols + ["adj_pop"]]
        .sum()
        .rename(columns={"parent_geoid": "geoid"})
        .merge(tract_lookup, on="geoid", how="left", validate="one_to_one")
    )

    county_adj = (
        tract_adj.groupby("parent_geoid", as_index=False)[adj_cols + ["adj_pop"]]
        .sum()
        .rename(columns={"parent_geoid": "geoid"})
        .merge(county_lookup, on="geoid", how="left", validate="one_to_one")
    )

    state_adj = (
        county_adj.groupby("parent_geoid", as_index=False)[adj_cols + ["adj_pop"]]
        .sum()
        .rename(columns={"parent_geoid": "geoid"})
        .merge(state_lookup, on="geoid", how="left", validate="one_to_one")
    )

    return {
        "block": block_adj,
        "tract": tract_adj,
        "county": county_adj,
        "state": state_adj,
    }


def summarize_error(
    df: pd.DataFrame,
    true_col: str = "true_pop",
    released_col: str = "adj_pop",
) -> pd.Series:
    err = df[released_col] - df[true_col]
    abs_err = err.abs()

    return pd.Series(
        {
            "n": len(df),
            "mean_error": err.mean(),
            "mean_abs_error": abs_err.mean(),
            "median_abs_error": abs_err.median(),
            "max_abs_error": abs_err.max(),
            "rmse": np.sqrt((err**2).mean()),
        }
    )


def run_block_dp_pipeline(
    block_df: pd.DataFrame,
    tract_df: pd.DataFrame,
    county_df: pd.DataFrame,
    state_df: pd.DataFrame,
    epsilon: float,
    verbose: bool = False,
) -> dict[str, pd.DataFrame]:
    log(verbose, f"[epsilon={format_epsilon(epsilon)}] adding OpenDP Laplace noise to block race counts")
    block_noised = add_opendp_laplace_noise(block_df, epsilon=epsilon, cols=RACE_COLS)
    log(verbose, f"[epsilon={format_epsilon(epsilon)}] clipping and rounding block counts")
    block_adj = postprocess_block_race_counts(block_noised, cols=RACE_COLS)

    log(verbose, f"[epsilon={format_epsilon(epsilon)}] aggregating blocks to tract/county/state")
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


def save_pipeline_outputs(outputs: dict[str, pd.DataFrame], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    file_names = {
        "block": "DF_IL_2010_BLOCK_DP.csv",
        "tract": "DF_IL_2010_TRACT_DP.csv",
        "county": "DF_IL_2010_COUNTY_DP.csv",
        "state": "DF_IL_2010_STATE_DP.csv",
    }

    for level_name, df in outputs.items():
        df.to_csv(output_dir / file_names[level_name], index=False)


def epsilon_outputs_exist(output_root: Path, epsilon: float) -> bool:
    output_dir = epsilon_output_dir(output_root, epsilon)
    required_files = [
        output_dir / "DF_IL_2010_BLOCK_DP.csv",
        output_dir / "DF_IL_2010_TRACT_DP.csv",
        output_dir / "DF_IL_2010_COUNTY_DP.csv",
        output_dir / "DF_IL_2010_STATE_DP.csv",
    ]
    return all(path.exists() for path in required_files)


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

    rows: list[dict[str, float | int | str]] = []
    all_results: dict[float, dict[str, pd.DataFrame]] = {}

    output_root.mkdir(parents=True, exist_ok=True)

    for epsilon in progress_iter(epsilons, use_tqdm, "OpenDP epsilons"):
        epsilon_start = time.time()
        epsilon_label = format_epsilon(epsilon)
        if epsilon_outputs_exist(output_root, epsilon):
            log(verbose, f"Skipping epsilon={epsilon_label}; outputs already exist in {epsilon_output_dir(output_root, epsilon)}")
            continue
        log(verbose, f"Starting epsilon={epsilon_label}")
        results = run_block_dp_pipeline(
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

        for level_name, df in results.items():
            stats = summarize_error(df).to_dict()
            stats["epsilon"] = epsilon
            stats["level"] = level_name
            rows.append(stats)

        log(verbose, f"Finished epsilon={epsilon_label} in {time.time() - epsilon_start:.1f}s")

    summary_df = pd.DataFrame(rows).sort_values(["level", "epsilon"]).reset_index(drop=True)
    summary_df.to_csv(output_root / "DP_noise_error_summary.csv", index=False)
    log(verbose, f"Saved summary CSV to {output_root / 'DP_noise_error_summary.csv'}")
    log(verbose, f"Completed all epsilon runs in {time.time() - start:.1f}s")

    return summary_df, all_results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate OpenDP noised outputs across epsilons.")
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
        help="Disable tqdm progress bars even if tqdm is installed.",
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
    print(f"Saved outputs to {args.output_root}")
    print(summary_df)


if __name__ == "__main__":
    main()
