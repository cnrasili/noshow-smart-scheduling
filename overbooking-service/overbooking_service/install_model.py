"""Install a delivered no-show model into the overbooking service.

Usage: python -m overbooking_service.install_model [--source ../ml/models]
The model is checked as at service startup and with the acceptance checks; the installed
model is replaced only when every check passes. Restart the service to load it.
"""

import argparse
import logging
import shutil
from pathlib import Path

from overbooking_service.config import SERVICE_ROOT, settings
from overbooking_service.model_checks import acceptance_problems
from overbooking_service.predictor import MODEL_FILE, SCHEMA_FILE, Predictor

# ml/models/ in the repository, where the prediction model side delivers the model
DEFAULT_SOURCE = SERVICE_ROOT.parent / "ml" / "models"


class InstallError(Exception):
    """The delivered model cannot be installed."""


def check_model(source: Path) -> Predictor:
    """Load the delivered model and run the acceptance checks; raise InstallError on problems."""
    missing = [name for name in (MODEL_FILE, SCHEMA_FILE) if not (source / name).is_file()]
    if missing:
        raise InstallError(f"Missing in {source}: {', '.join(missing)}")
    try:
        predictor = Predictor.load(source)
    except Exception as exc:
        raise InstallError(f"The model cannot be loaded: {exc}") from exc
    try:
        problems = acceptance_problems(predictor)
    except Exception as exc:
        raise InstallError(f"The model fails to predict: {exc}") from exc
    if problems:
        raise InstallError("The model fails the acceptance checks:\n- " + "\n- ".join(problems))
    return predictor


def install_model(source: Path, target: Path) -> Predictor:
    """Check the model in source and copy it into target; target is unchanged on failure."""
    source, target = source.resolve(), target.resolve()
    if source == target:
        raise InstallError("The source folder is the installed model folder")
    predictor = check_model(source)

    # Copy next to the installed files first, then swap them in
    target.mkdir(parents=True, exist_ok=True)
    for name in (MODEL_FILE, SCHEMA_FILE):
        shutil.copyfile(source / name, target / f"{name}.new")
    for name in (MODEL_FILE, SCHEMA_FILE):
        (target / f"{name}.new").replace(target / name)
    return predictor


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="Delivered model")
    args = parser.parse_args()
    # Shows the scikit-learn version warning of the model loader
    logging.basicConfig(level=logging.WARNING, format="Warning: %(message)s")

    try:
        predictor = install_model(args.source, settings.model_dir)
    except InstallError as exc:
        raise SystemExit(f"Model not installed. {exc}") from None
    print(
        f"Installed model {predictor.version} ({len(predictor.feature_names)} features) "
        f"into {settings.model_dir}."
    )
    print("Restart the overbooking service to load it.")


if __name__ == "__main__":
    main()
