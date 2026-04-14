import os
import sys
import contextlib
from typing import Dict, List
from datetime import datetime

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class _Tee:
    """Write to multiple text streams at once."""

    def __init__(self, *streams):
        self._streams = streams

    def write(self, data: str) -> int:
        for stream in self._streams:
            stream.write(data)
        return len(data)

    def flush(self) -> None:
        for stream in self._streams:
            stream.flush()


def write_urdf(modules: List[str], name: str = "robot", template_path: str = None) -> None:
    """
    Replace placeholders in a template file with contents from module files.
    """
    # Use default template path if none provided
    if template_path is None:
        template_path = os.path.join(SCRIPT_DIR, "_template")

    # Fail fast with a precise error if the template itself is missing.
    if not os.path.isfile(template_path):
        print(f"Error: Template file '{template_path}' not found.")
        return

    try:
        # Read the template file
        with open(template_path, "r", encoding="utf-8") as template_file:
            urdf_string = template_file.read()

        # Concatenate requested modules in order.
        content = f"  <!-- [URDF-WRITER] Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -->\n"

        for module_name in modules:
            file_path = os.path.join(SCRIPT_DIR, "..", "modules", module_name)
            if not os.path.exists(file_path):
                print(f"Warning: File '{file_path}' not found. Skipping...")
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as module_file:
                    module_text = module_file.read()

                content += (
                    f"\n  <!-- [URDF-WRITER] from module [{module_name}] -->\n"
                    + module_text
                )
            except Exception as e:
                print(f"Error reading file '{file_path}': {e}")
                continue

        urdf_string = urdf_string.replace("$NAME$", name).replace("$CONTENT$", content)

        output_dir = os.path.join(SCRIPT_DIR, "..", "urdf")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{name}.urdf")
        with open(output_path, "w", encoding="utf-8") as output_file:
            output_file.write(urdf_string)

        print(f"[{name}] written to '{output_path}'")

    except Exception as e:
        print(f"Error processing template: {e}")


def load_seed_config(seed_path: str) -> Dict[str, List[str]]:
    """Load URDF generation targets from a YAML seed file."""
    if not os.path.isfile(seed_path):
        raise FileNotFoundError(f"Seed file '{seed_path}' not found.")

    try:
        import yaml  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "PyYAML is required to read seed config. Install with 'pip install pyyaml'."
        ) from exc

    with open(seed_path, "r", encoding="utf-8") as seed_file:
        loaded = yaml.safe_load(seed_file)

    if not isinstance(loaded, dict):
        raise ValueError("Seed config must be a mapping of output-name -> module list.")

    seed_config: Dict[str, List[str]] = {}
    for output_name, modules in loaded.items():
        if not isinstance(output_name, str) or not output_name.strip():
            raise ValueError("Each seed key must be a non-empty output URDF name.")
        if not isinstance(modules, list) or not all(isinstance(m, str) for m in modules):
            raise ValueError(
                f"Seed entry '{output_name}' must be a list of module names (strings)."
            )
        seed_config[output_name] = modules

    return seed_config


# Example usage
if __name__ == "__main__":
    seed_path = os.path.join(SCRIPT_DIR, "..", "urdf", "_seed.yaml")
    logs_dir = os.path.join(SCRIPT_DIR, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(logs_dir, f"urdf-writer_{run_ts}.log")

    with open(log_path, "w", encoding="utf-8") as log_file:
        tee_stdout = _Tee(sys.stdout, log_file)
        tee_stderr = _Tee(sys.stderr, log_file)
        with contextlib.redirect_stdout(tee_stdout), contextlib.redirect_stderr(tee_stderr):
            print(f"[URDF-WRITER] Logging to '{log_path}'")
            seed_config = load_seed_config(seed_path)
            print(f"[URDF-WRITER] Loaded {len(seed_config)} targets from '{seed_path}'")

            for output_name, module_list in seed_config.items():
                write_urdf(module_list, output_name)
