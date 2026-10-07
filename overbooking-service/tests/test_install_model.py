import json
import logging
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest
from sklearn.linear_model import LogisticRegression

from overbooking_service import install_model as installer
from overbooking_service.config import settings
from overbooking_service.install_model import InstallError, install_model
from overbooking_service.model_checks import acceptance_problems
from overbooking_service.predictor import MODEL_FILE, SCHEMA_FILE, Predictor

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ml"))
from export_model import export_model  # noqa: E402

FEATURES = [
    "lead_days",
    "weekday",
    "age",
    "gender_male",
    "scholarship",
    "hipertension",
    "diabetes",
    "alcoholism",
    "handcap",
    "prior_appt_count",
    "prior_noshow_count",
]


def model(names: list[str], lead: float = 0.02, prior_noshows: float = 0.5) -> LogisticRegression:
    """A logistic regression with fixed coefficients on lead time and past no-shows."""
    coefficients = [
        lead if i == 0 else prior_noshows if i == len(names) - 1 else 0.0 for i in range(len(names))
    ]
    result = LogisticRegression()
    result.classes_ = np.array([0, 1])
    result.coef_ = np.array([coefficients])
    result.intercept_ = np.array([-1.3])
    result.n_features_in_ = len(names)
    return result


def deliver(folder: Path, names: list[str] = FEATURES, version: str = "test-v1", **kw) -> Path:
    export_model(model(names, **kw), names, version, positive_class=1, output_dir=folder)
    return folder


def edit_schema(folder: Path, **changes) -> None:
    path = folder / SCHEMA_FILE
    schema = json.loads(path.read_text(encoding="utf-8")) | changes
    path.write_text(json.dumps(schema), encoding="utf-8")


@pytest.fixture
def target(tmp_path: Path) -> Path:
    # A copy of the installed model, so refusals can be checked against it
    folder = tmp_path / "installed"
    shutil.copytree(settings.model_dir, folder)
    return folder


def contents(folder: Path) -> dict[str, bytes]:
    return {name: (folder / name).read_bytes() for name in (MODEL_FILE, SCHEMA_FILE)}


def test_valid_model_is_installed(tmp_path: Path, target: Path):
    source = deliver(tmp_path / "delivered")
    predictor = install_model(source, target)
    assert predictor.version == "test-v1"
    assert contents(target) == contents(source)
    assert not list(target.glob("*.new"))
    # The installed model passes the acceptance checks the service tests run
    assert acceptance_problems(Predictor.load(target)) == []


@pytest.mark.parametrize(
    ("prepare", "message"),
    [
        (
            lambda folder: deliver(folder, [name.title().replace("_", "") for name in FEATURES]),
            "missing in the schema",
        ),
        (lambda folder: deliver(folder, lead=-0.02, prior_noshows=-0.5), "do not score higher"),
        (lambda folder: (deliver(folder), edit_schema(folder, positive_class="Yes")), "cannot be"),
        (lambda folder: (deliver(folder), (folder / SCHEMA_FILE).unlink()), "Missing in"),
        (
            lambda folder: (deliver(folder), (folder / MODEL_FILE).write_bytes(b"no model")),
            "cannot",
        ),
    ],
    ids=["feature-names", "ranking", "positive-class", "missing-file", "broken-file"],
)
def test_invalid_model_is_refused_and_installed_model_kept(tmp_path, target, prepare, message):
    source = tmp_path / "delivered"
    prepare(source)
    before = contents(target)
    with pytest.raises(InstallError, match=message):
        install_model(source, target)
    assert contents(target) == before


def test_installing_from_the_installed_folder_is_refused(target: Path):
    with pytest.raises(InstallError, match="installed model folder"):
        install_model(target, target)


def test_scikit_learn_version_difference_is_a_warning(tmp_path, target, caplog):
    source = deliver(tmp_path / "delivered")
    edit_schema(source, sklearn_version="0.1.0")
    with caplog.at_level(logging.WARNING):
        install_model(source, target)
    assert "scikit-learn 0.1.0" in caplog.text


def test_command_installs_and_reports(tmp_path, target, monkeypatch, capsys):
    source = deliver(tmp_path / "delivered", version="rf-v1")
    monkeypatch.setattr(settings, "model_dir", target)
    monkeypatch.setattr(sys, "argv", ["install_model", "--source", str(source)])
    installer.main()
    out = capsys.readouterr().out
    assert "Installed model rf-v1 (11 features)" in out
    assert "Restart the overbooking service" in out


def test_command_refusal_exits_with_the_reason(tmp_path, target, monkeypatch):
    monkeypatch.setattr(settings, "model_dir", target)
    monkeypatch.setattr(sys, "argv", ["install_model", "--source", str(tmp_path / "empty")])
    with pytest.raises(SystemExit, match="Model not installed. Missing in"):
        installer.main()
