from pathlib import Path


def test_project_layout_assets_exist():
    project_root = Path(__file__).resolve().parents[1]
    assert (project_root / "roms" / "chip8-test-suite.ch8").exists()
    assert (project_root / "assets" / "tone.wav").exists()
    assert (project_root / "dumps").exists()
