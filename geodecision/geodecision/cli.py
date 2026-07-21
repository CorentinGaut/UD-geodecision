"""Console script for geodecision.

Each subcommand takes a single JSON parameters file and delegates to the
matching module's run(json_params) function - see that module's schema.py
for the expected fields. After a successful run, the JSON config itself is
copied into the run's output_folder as run_config.json, so every output
directory documents exactly what parameters produced it.
"""
import argparse
import json
import os
import shutil
import sys

from .accessibility.accessibility import run as compute_accessibility_run
from .graph.download import run as download_graph_run
from .osmquery.methods import run as fetch_polygons_run
from .visualization.plot_isochrones import run as visualize_run

COMMANDS = {
        "download-graph": download_graph_run,
        "fetch-polygons": fetch_polygons_run,
        "compute-accessibility": compute_accessibility_run,
        "visualize": visualize_run,
        }


def _save_run_config(json_config, output_folder):
    """
    Description
    ------------

    Copy the JSON config used for a run into its own output folder, so the
    output directory is self-documenting and the run is reproducible.

    Parameters
    -----------

    - json_config (str):
        - Path to the JSON parameters file that was used for the run
    - output_folder (str):
        - The run's output folder (params["output_folder"])
    """
    os.makedirs(output_folder, exist_ok=True)
    shutil.copy(json_config, os.path.join(output_folder, "run_config.json"))


def main():
    """Console script for geodecision."""
    parser = argparse.ArgumentParser(
            description="geodecision - urban accessibility/graph analysis pipeline"
            )
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name in COMMANDS:
        sub = subparsers.add_parser(name)
        sub.add_argument("json_config", help="Path to a JSON parameters file")

    args = parser.parse_args()

    run_fn = COMMANDS[args.command]
    run_fn(args.json_config)

    with open(args.json_config) as f:
        params = json.load(f)
    output_folder = params.get("output_folder")
    if output_folder:
        _save_run_config(args.json_config, output_folder)
        print(f"'{args.command}' completed. Output folder: {output_folder}")
    else:
        print(f"'{args.command}' completed.")

    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
