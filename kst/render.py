"""Discover and render Kubernetes Kustomize manifests."""

import argparse
import subprocess
from pathlib import Path

import yaml


KUSTOMIZATION_FILES = (
    "kustomization.yaml",
    "kustomization.yml",
    "Kustomization",
)

REFERENCE_KEYS = (
    "resources",
    "components",
    "patchesStrategicMerge",
    "transformers",
    "generators",
    "crds",
    "configurations",
)


def kustomization_file(directory):
    """Return the Kustomization configuration file, if present."""
    for name in KUSTOMIZATION_FILES:
        candidate = directory / name
        if candidate.is_file():
            return candidate
    return None


def find_kustomizations(repo_path, manifest_paths):
    """Find Kustomization directories within manifest paths."""
    repo_path = Path(repo_path).resolve()
    directories = set()

    for manifest_path in manifest_paths:
        root = repo_path / manifest_path

        if not root.exists():
            continue

        if root.is_file():
            if root.name in KUSTOMIZATION_FILES:
                directories.add(root.parent.resolve())
            continue

        for name in KUSTOMIZATION_FILES:
            for path in root.rglob(name):
                if path.is_file():
                    directories.add(path.parent.resolve())

    return sorted(directories)


def read_config(directory):
    """Read a Kustomization configuration."""
    path = kustomization_file(directory)

    if path is None:
        return {}

    with path.open(encoding="utf-8") as stream:
        config = yaml.safe_load(stream) or {}

    if not isinstance(config, dict):
        raise ValueError(f"Invalid Kustomization: {path}")

    return config


def local_references(directory):
    """Find local resource, patch, and transformer references."""
    config = read_config(directory)
    references = set()

    for key in REFERENCE_KEYS:
        for entry in config.get(key, []) or []:
            if isinstance(entry, str):
                references.add((directory / entry).resolve())

    for entry in config.get("patches", []) or []:
        if isinstance(entry, dict) and isinstance(
            entry.get("path"), str
        ):
            references.add((directory / entry["path"]).resolve())

    for key in ("configMapGenerator", "secretGenerator"):
        for generator in config.get(key, []) or []:
            if not isinstance(generator, dict):
                continue

            for source_key in ("files", "envs"):
                for entry in generator.get(source_key, []) or []:
                    if not isinstance(entry, str):
                        continue

                    source = entry.split("=", 1)[-1]
                    references.add((directory / source).resolve())

            env_file = generator.get("env")
            if isinstance(env_file, str):
                references.add((directory / env_file).resolve())

    return references


def find_top_level_kustomizations(directories):
    """Exclude Kustomizations referenced by other Kustomizations."""
    directories = {Path(d).resolve() for d in directories}
    referenced = set()

    for directory in directories:
        try:
            targets = local_references(directory)
        except (OSError, ValueError, yaml.YAMLError):
            # Keep invalid configurations for the rendering failure report.
            continue

        for target in targets:
            if target.is_dir() and target in directories:
                referenced.add(target)

    return sorted(directories - referenced)


def find_consumed_files(directories):
    """Find files consumed by Kustomizations."""
    consumed = set()
    visited = set()

    def visit(directory):
        directory = Path(directory).resolve()

        if directory in visited:
            return

        visited.add(directory)

        kfile = kustomization_file(directory)

        if kfile is None:
            return

        consumed.add(kfile.resolve())

        for target in local_references(directory):
            if target.is_file():
                consumed.add(target)
            elif target.is_dir():
                if kustomization_file(target):
                    visit(target)
                else:
                    for path in target.rglob("*"):
                        if path.is_file() and path.suffix in (
                            ".yaml", ".yml"
                        ):
                            consumed.add(path.resolve())

    for directory in directories:
        visit(directory)

    return consumed


def render_kustomizations(repo_path, manifest_paths, output_dir):
    """Render top-level Kustomizations and report failures."""
    repo_path = Path(repo_path).resolve()
    output_dir = Path(output_dir).resolve()

    directories = find_kustomizations(repo_path, manifest_paths)
    top_level = find_top_level_kustomizations(directories)

    rendered = []
    consumed = set()
    failures = []

    for directory in top_level:
        relative = directory.relative_to(repo_path)
        filename = ("__".join(relative.parts) if relative.parts else "root") + ".yaml"
        destination = output_dir / filename
        # Remove stale output before attempting a new render.
        if destination.exists():
            destination.unlink()

        try:
            result = subprocess.run(
                ["kubectl", "kustomize", str(directory)],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0 or not result.stdout.strip():
                message = result.stderr.strip() or "empty output"
                raise RuntimeError(message)

            output_dir.mkdir(parents=True, exist_ok=True)
            destination.write_text(
                result.stdout, encoding="utf-8"
            )

            rendered.append(destination)
            consumed.update(find_consumed_files([directory]))

        except (OSError, RuntimeError, ValueError, yaml.YAMLError) as exc:
            failures.append((str(relative), str(exc)))

    return rendered, consumed, failures
def build_analysis_file_list(repo_path, manifest_paths, output_dir):
    """Return rendered manifests and unconsumed plain YAML files."""
    from .manifests import skip_reason

    repo_path = Path(repo_path).resolve()

    rendered, consumed, failures = render_kustomizations(
        repo_path, manifest_paths, output_dir
    )

    plain_files = []

    for manifest_path in manifest_paths:
        root = repo_path / manifest_path

        if not root.exists():
            continue

        candidates = [root] if root.is_file() else root.rglob("*")

        for path in candidates:
            if not path.is_file() or path.suffix not in (".yaml", ".yml"):
                continue

            if path.resolve() in consumed:
                continue

            text = path.read_text(encoding="utf-8", errors="replace")

            if skip_reason(str(path), text) is None:
                plain_files.append(str(path.relative_to(repo_path)))

    return sorted(set(plain_files)) + [str(path) for path in rendered], failures

def main():
    """Command-line entry point."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-path", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--manifest-path", action="append", required=True)

    args = parser.parse_args()

    files, failures = build_analysis_file_list(
    args.repo_path,
    args.manifest_path,
    args.output_dir,
)

    for path in files:
        print(path)

    for directory, error in failures:
        print(f"render failed: {directory}: {error}", file=__import__("sys").stderr)

    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
