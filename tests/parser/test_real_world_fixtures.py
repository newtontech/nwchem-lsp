"""Parser smoke tests for downloaded NWChem example inputs."""

from pathlib import Path

import pytest

from nwchem_lsp.parser.nwchem_parser import NwchemParser

FIXTURE_DIR = Path(__file__).parents[1] / "fixtures" / "real_world" / "nwchem-official"


@pytest.mark.parametrize("fixture_path", sorted(FIXTURE_DIR.glob("*.nw")), ids=lambda p: p.name)
def test_official_nwchem_examples_parse(fixture_path: Path) -> None:
    """Real NWChem examples should load into the parser and expose structure."""
    parser = NwchemParser(fixture_path.read_text(encoding="utf-8"))

    blocks = parser.parse()

    assert blocks, f"{fixture_path.name} produced no parsed blocks"
    assert parser.get_all_sections(), f"{fixture_path.name} produced no parsed sections"
    assert any(block.name == "task" for block in blocks), f"{fixture_path.name} has no task block"
