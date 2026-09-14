import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from avoi.actions import ActionSpec  # noqa: E402
from avoi.datasets.common import ObjectiveData  # noqa: E402


def synthetic_objective(n=240, seed=0, kind="categorical"):
    """Small synthetic objective used ONLY for unit tests of the machinery (never for experiments)."""
    rng = np.random.default_rng(seed)
    y = rng.integers(0, 2, n)
    m = 4
    vals = np.zeros((n, m), dtype=int)
    vals[:, 0] = np.where(rng.uniform(size=n) < 0.8, y, 1 - y)                 # reliable binary
    vals[:, 1] = np.where(rng.uniform(size=n) < 0.6, y, 1 - y)                 # weak binary
    vals[:, 2] = np.clip(y + rng.integers(0, 2, n), 0, 2)                      # 3-valued
    vals[:, 3] = rng.integers(0, 2, n)                                         # noise
    specs = [ActionSpec(f"a{j}", "OBJ", st, tuple(f"o{k}" for k in range(K)), tuple([1, -1, 0][:K]), ("user_identifier",))
             for j, (st, K) in enumerate([("configuration_state", 2), ("policy_document", 2), ("authentication_log", 3),
                                          ("ticket_record", 2)])]
    rec = rng.integers(1, 100, (n, m)).astype(float)
    byt = rec * 100
    sec = rng.uniform(0.01, 0.2, (n, m))
    priv = [[["user_identifier"] if j % 2 == 0 else [] for j in range(m)] for _ in range(n)]
    data = ObjectiveData("synthetic", "OBJ", specs, np.array([f"e{i}" for i in range(n)]), np.arange(n) % 12,
                         {"conflict": np.zeros(n, bool)}, "categorical", vals, sec, rec, byt, priv, None, "synthetic")
    return data, y


@pytest.fixture
def synth():
    return synthetic_objective()
