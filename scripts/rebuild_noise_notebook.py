from pathlib import Path

import nbformat as nbf


def build_notebook() -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook()
    nb.metadata = {
        "kernelspec": {
            "display_name": "Python 3 (ipykernel)",
            "language": "python",
            "name": "python3",
        },
        "language_info": {
            "name": "python",
            "version": "3.9.16",
        },
    }

    cells = [
        nbf.v4.new_markdown_cell(
            "# OpenDP Noise Runs\n\n"
            "This notebook generates block-level OpenDP Laplace noise for several epsilon values, "
            "aggregates the adjusted counts to tract/county/state, and saves each run under "
            "`data/processed_data/DP_noise/epsilon_<value>/`.\n\n"
            "The hierarchy is rebuilt from `data/il_pl2010_b/il_pl2010_b.csv` so the saved "
            "GEOIDs remain unique statewide during aggregation.\n"
        ),
        nbf.v4.new_code_cell(
            "from pathlib import Path\n\n"
            "import matplotlib.pyplot as plt\n"
            "import pandas as pd\n"
            "import seaborn as sns\n\n"
            "from dp_noise_pipeline import (\n"
            "    DEFAULT_EPSILONS,\n"
            "    DEFAULT_OUTPUT_ROOT,\n"
            "    epsilon_output_dir,\n"
            "    format_epsilon,\n"
            "    run_epsilons,\n"
            ")\n"
        ),
        nbf.v4.new_code_cell(
            "EPSILONS = DEFAULT_EPSILONS\n"
            "OUTPUT_ROOT = DEFAULT_OUTPUT_ROOT\n\n"
            "RERUN_GENERATION = False\n"
            "summary_path = OUTPUT_ROOT / 'DP_noise_error_summary.csv'\n\n"
            "if RERUN_GENERATION or not summary_path.exists():\n"
            "    summary_df, _ = run_epsilons(EPSILONS, OUTPUT_ROOT)\n"
            "\n"
            "summary_df = pd.read_csv(summary_path)\n"
            "summary_df\n"
        ),
        nbf.v4.new_code_cell(
            "saved_paths = {\n"
            "    format_epsilon(eps): epsilon_output_dir(OUTPUT_ROOT, eps)\n"
            "    for eps in EPSILONS\n"
            "}\n"
            "saved_paths\n"
        ),
        nbf.v4.new_code_cell(
            "example_epsilon = EPSILONS[1] if len(EPSILONS) > 1 else EPSILONS[0]\n"
            "example_block = pd.read_csv(\n"
            "    epsilon_output_dir(OUTPUT_ROOT, example_epsilon) / 'DF_IL_2010_BLOCK_DP.csv'\n"
            ").copy()\n"
            "example_block['pop_error'] = example_block['adj_pop'] - example_block['true_pop']\n\n"
            "plt.figure(figsize=(8, 4))\n"
            "sns.histplot(example_block['pop_error'], bins=50)\n"
            "plt.title(f'Block-Level Population Error (epsilon={example_epsilon:g})')\n"
            "plt.xlabel('Error')\n"
            "plt.ylabel('Count')\n"
            "plt.show()\n"
        ),
        nbf.v4.new_code_cell(
            "plt.figure(figsize=(8, 4))\n"
            "sns.lineplot(data=summary_df, x='epsilon', y='mean_abs_error', hue='level', marker='o')\n"
            "plt.title('Mean Absolute Error by Epsilon and Geography')\n"
            "plt.ylabel('MAE')\n"
            "plt.show()\n"
        ),
        nbf.v4.new_code_cell(
            "pd.read_csv(OUTPUT_ROOT / 'DP_noise_error_summary.csv')\n"
        ),
    ]

    nb.cells = cells
    return nb


def main() -> None:
    notebook = build_notebook()
    target = Path("noise.ipynb")
    target.write_text(nbf.writes(notebook))


if __name__ == "__main__":
    main()
