# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import pytest


# Test data directory
TEST_DATA_DIR = Path(__file__).parent / "data"


@pytest.fixture
def test_data_path() -> Path:
    """Path to test data directory."""
    return TEST_DATA_DIR


@pytest.fixture
def aces_amf_examples_path(test_data_path) -> Path:
    """Path to ACES example AMF files."""
    return test_data_path / "aces-examples"
