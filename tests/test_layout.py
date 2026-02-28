from pathlib import Path


def test_bins_assets_exist():
    project_root = Path(__file__).resolve().parents[1]
    assert (project_root / "bins" / "chip8-test-suite.ch8").exists()
    assert (project_root / "bins" / "tone.wav").exists()
