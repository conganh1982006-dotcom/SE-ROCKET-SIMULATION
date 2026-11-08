import numpy as np
from experiments.studies import generate_local_dataset, sample_parameters


def test_local_dataset_is_safe_to_load_and_contains_valid_events(tmp_path):
    path = tmp_path/"dataset.npz"
    info = generate_local_dataset(path, n=3)
    assert info["physical_checks_passed"] == 3
    with np.load(path, allow_pickle=False) as data:
        assert not bool(data["official_wmlab"])
        assert len(data["offsets"]) == 4
        assert data["offsets"][-1] == len(data["t"])
        for lo, hi in zip(data["offsets"][:-1], data["offsets"][1:]):
            assert data["t"][lo] == 0
            assert abs(data["y"][hi-1,1]) < 1e-8
            assert np.all(np.diff(data["t"][lo:hi]) > 0)


def test_sampling_is_repeatable_and_allows_immediate_liftoff():
    first = list(sample_parameters(10, 123))
    assert first == list(sample_parameters(10, 123))
    assert first != list(sample_parameters(10, 456))
    assert all(1.2 <= p.q*p.ve/(p.m0*p.g) <= 15 for p in first)
