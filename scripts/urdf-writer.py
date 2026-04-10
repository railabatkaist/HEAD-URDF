import os
import sys
import contextlib
from typing import List
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


# Example usage
if __name__ == "__main__":
    logs_dir = os.path.join(SCRIPT_DIR, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(logs_dir, f"urdf-writer_{run_ts}.log")

    with open(log_path, "w", encoding="utf-8") as log_file:
        tee_stdout = _Tee(sys.stdout, log_file)
        tee_stderr = _Tee(sys.stderr, log_file)
        with contextlib.redirect_stdout(tee_stdout), contextlib.redirect_stderr(tee_stderr):
            print(f"[URDF-WRITER] Logging to '{log_path}'")

            write_urdf(["_fixed-base", "head"], "head")
            write_urdf(["_fixed-base", "head", "head-sensor_d455"], "head-d455")
            write_urdf(["_fixed-base", "head", "head-sensor_mid360"], "head-mid360")
            write_urdf(["_fixed-base", "head", "head-face", "head-sensor_d455", "head-sensor_mid360"], "head-full")
