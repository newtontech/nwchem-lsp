"""NWChem keywords database module.

This module provides comprehensive data structures and functions for NWChem
input file keywords, including top-level sections, task operations,
DFT functionals, basis sets, and chemical elements.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set


@dataclass
class KeywordInfo:
    """Information about an NWChem keyword."""

    name: str
    description: str
    section: str
    required: bool = False
    arguments: Optional[List[str]] = None
    example: Optional[str] = None


# Chemical elements
ELEMENTS: List[str] = [
    "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne",
    "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca",
    "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr", "Y", "Zr",
    "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn",
    "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd",
    "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb",
    "Lu", "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
    "Tl", "Pb", "Bi", "Po", "At", "Rn", "Fr", "Ra", "Ac", "Th",
    "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk", "Cf", "Es", "Fm",
    "Md", "No", "Lr", "Rf", "Db", "Sg", "Bh", "Hs", "Mt", "Ds",
    "Rg", "Cn", "Nh", "Fl", "Mc", "Lv", "Ts", "Og",
]

# DFT Exchange-Correlation Functionals
DFT_FUNCTIONALS: List[str] = [
    "LDA", "S", "BLYP", "PBE", "BP86", "PW91", "B97-D",
    "B3LYP", "PBE0", "BHLYP", "B3PW91", "B1LYP",
    "TPSS", "M06-L", "M06", "M06-2X", "M06-HF",
    "SCAN", "RSCAN", "R2SCAN",
    "LC-BLYP", "LC-PBE", "CAM-B3LYP", "wB97", "wB97X", "wB97X-D",
    "M11", "M11-L", "M08-HX", "M08-SO", "MN12-L", "MN12-SX",
    "X3LYP", "O3LYP", "B97-1", "B97-2", "B98", "PBEsol",
]

# Common basis sets
BASIS_SETS: List[str] = [
    "STO-3G", "3-21G", "6-31G", "6-311G",
    "6-31G*", "6-31G(d)", "6-31G**", "6-31G(d,p)",
    "6-311G*", "6-311G(d)", "6-311G**", "6-311G(d,p)",
    "6-31+G*", "6-31++G**", "6-311+G*", "6-311++G**",
    "cc-pVDZ", "cc-pVTZ", "cc-pVQZ", "cc-pV5Z", "cc-pV6Z",
    "aug-cc-pVDZ", "aug-cc-pVTZ", "aug-cc-pVQZ", "aug-cc-pV5Z",
    "cc-pCVDZ", "cc-pCVTZ", "cc-pCVQZ",
    "def2-SVP", "def2-TZVP", "def2-TZVPP", "def2-QZVP", "def2-QZVPP",
    "LANL2DZ", "LANL2TZ", "SDD", "DGDZVP", "MINI", "MIDI",
]

# Task operations
TASK_OPERATIONS: List[str] = [
    "energy", "gradient", "optimize", "saddle", "hessian",
    "frequencies", "freq", "vib", "property", "dynamics",
    "thermodynamics", "tce", "ccsd", "ccsd(t)", "ccsd[t]",
    "mp2", "mp3", "mp4", "rimp2", "mcscf", "selci",
    "pspw", "band", "paw", "ofpw",
]

# Top-level NWChem keywords
TOP_LEVEL_KEYWORDS: Dict[str, KeywordInfo] = {
    "geometry": KeywordInfo(
        name="geometry",
        description="Define molecular geometry section",
        section="top",
        required=True,
        arguments=["units", "angstroms", "bohr", "autosym", "noautoz", "nocenter", "center"],
        example="geometry units angstroms\\n  O  0.0  0.0  0.0\\n  H  0.0  0.8  0.6\\n  H  0.0 -0.8  0.6\\nend",
    ),
    "basis": KeywordInfo(
        name="basis",
        description="Define basis set specification",
        section="top",
        required=True,
        arguments=["spherical", "cartesian"],
        example="basis spherical\\n  * library 6-31G*\\nend",
    ),
    "charge": KeywordInfo(
        name="charge",
        description="Set total molecular charge",
        section="top",
        required=False,
        arguments=["integer"],
        example="charge 0",
    ),
    "scf": KeywordInfo(
        name="scf",
        description="Self-Consistent Field (Hartree-Fock) calculation",
        section="top",
        required=False,
        arguments=["singlet", "doublet", "triplet", "quartet", "quintet", "rhf", "uhf", "rohf", "mcscf", "thresh", "maxiter", "direct", "semidirect"],
        example="scf\\n  singlet\\n  rhf\\n  maxiter 100\\nend",
    ),
    "dft": KeywordInfo(
        name="dft",
        description="Density Functional Theory calculation",
        section="top",
        required=False,
        arguments=["xc", "grid", "tolerances", "convergence", "iterations", "direct", "noio", "odft", "cdft", "mult"],
        example="dft\\n  xc b3lyp\\n  grid fine\\n  convergence energy 1e-8\\nend",
    ),
    "mp2": KeywordInfo(
        name="mp2",
        description="Second-order Moller-Plesset perturbation theory",
        section="top",
        required=False,
        arguments=["tight", "freeze", "scratch disk", "ri", "cd", "thize", "thize_g"],
        example="mp2\\n  freeze atomic\\nend",
    ),
    "ccsd": KeywordInfo(
        name="ccsd",
        description="Coupled Cluster Singles and Doubles",
        section="top",
        required=False,
        arguments=["tce", "freeze", "thresh", "maxiter", "io", "diis", "nodis", "ccsd(t)"],
        example="ccsd\\n  freeze atomic\\n  thresh 1e-6\\nend",
    ),
    "ecp": KeywordInfo(
        name="ecp",
        description="Effective Core Potential specification",
        section="top",
        required=False,
        arguments=["library"],
        example="ecp\\n  Pt library LANL2DZ\\nend",
    ),
    "task": KeywordInfo(
        name="task",
        description="Execute a computational task",
        section="top",
        required=True,
        arguments=TASK_OPERATIONS,
        example="task dft optimize",
    ),
    "set": KeywordInfo(
        name="set",
        description="Set a variable or parameter",
        section="top",
        required=False,
        arguments=["variable_name", "value"],
        example="set geometry:units bohr",
    ),
    "unset": KeywordInfo(
        name="unset",
        description="Unset a variable",
        section="top",
        required=False,
        arguments=["variable_name"],
        example="unset geometry:units",
    ),
    "echo": KeywordInfo(
        name="echo",
        description="Echo a string to output",
        section="top",
        required=False,
        arguments=["string"],
        example='echo "Starting calculation"',
    ),
    "start": KeywordInfo(
        name="start",
        description="Specify restart file name",
        section="top",
        required=False,
        arguments=["filename"],
        example="start water",
    ),
    "restart": KeywordInfo(
        name="restart",
        description="Restart from a previous calculation",
        section="top",
        required=False,
        arguments=["filename"],
        example="restart water",
    ),
    "permanent_dir": KeywordInfo(
        name="permanent_dir",
        description="Set permanent directory for large files",
        section="top",
        required=False,
        arguments=["path"],
        example="permanent_dir /tmp/scratch",
    ),
    "scratch_dir": KeywordInfo(
        name="scratch_dir",
        description="Set scratch directory for temporary files",
        section="top",
        required=False,
        arguments=["path"],
        example="scratch_dir /tmp/scratch",
    ),
    "memory": KeywordInfo(
        name="memory",
        description="Set memory limits for calculation",
        section="top",
        required=False,
        arguments=["total", "stack", "heap", "global"],
        example="memory total 4 gb",
    ),
    "title": KeywordInfo(
        name="title",
        description="Set a title for the calculation",
        section="top",
        required=False,
        arguments=["string"],
        example='title "Water molecule optimization"',
    ),
    "print": KeywordInfo(
        name="print",
        description="Control printing level",
        section="top",
        required=False,
        arguments=["none", "low", "medium", "high", "debug"],
        example="print high",
    ),
}

# DFT-specific keywords
DFT_KEYWORDS: Dict[str, KeywordInfo] = {
    "xc": KeywordInfo(name="xc", description="Exchange-correlation functional", section="dft", arguments=DFT_FUNCTIONALS),
    "grid": KeywordInfo(name="grid", description="Numerical integration grid", section="dft", arguments=["coarse", "medium", "fine", "xfine", "ultrafine"]),
    "convergence": KeywordInfo(name="convergence", description="SCF convergence criteria", section="dft", arguments=["energy", "density", "gradient"]),
    "iterations": KeywordInfo(name="iterations", description="Maximum number of SCF iterations", section="dft", arguments=["integer"]),
    "direct": KeywordInfo(name="direct", description="Force direct SCF (recalculate integrals)", section="dft"),
    "noio": KeywordInfo(name="noio", description="Disable disk I/O for integrals", section="dft"),
    "odft": KeywordInfo(name="odft", description="Open-shell DFT calculation", section="dft"),
    "mult": KeywordInfo(name="mult", description="Spin multiplicity", section="dft", arguments=["integer"]),
}

# SCF-specific keywords
SCF_KEYWORDS: Dict[str, KeywordInfo] = {
    "singlet": KeywordInfo(name="singlet", description="Singlet spin state", section="scf"),
    "doublet": KeywordInfo(name="doublet", description="Doublet spin state", section="scf"),
    "triplet": KeywordInfo(name="triplet", description="Triplet spin state", section="scf"),
    "rhf": KeywordInfo(name="rhf", description="Restricted Hartree-Fock", section="scf"),
    "uhf": KeywordInfo(name="uhf", description="Unrestricted Hartree-Fock", section="scf"),
    "rohf": KeywordInfo(name="rohf", description="Restricted open-shell Hartree-Fock", section="scf"),
    "maxiter": KeywordInfo(name="maxiter", description="Maximum number of SCF iterations", section="scf", arguments=["integer"]),
    "thresh": KeywordInfo(name="thresh", description="Convergence threshold", section="scf", arguments=["float"]),
}

# Geometry keywords
GEOMETRY_KEYWORDS: Dict[str, KeywordInfo] = {
    "units": KeywordInfo(name="units", description="Units for geometry coordinates", section="geometry", arguments=["angstroms", "bohr", "nanometers", "picometers"]),
    "autosym": KeywordInfo(name="autosym", description="Automatic symmetry detection", section="geometry"),
    "noautoz": KeywordInfo(name="noautoz", description="Disable automatic Z-matrix generation", section="geometry"),
    "center": KeywordInfo(name="center", description="Center geometry at origin", section="geometry"),
    "nocenter": KeywordInfo(name="nocenter", description="Do not center geometry", section="geometry"),
    "system": KeywordInfo(name="system", description="Periodic boundary conditions", section="geometry", arguments=["crystal", "slab", "polymer", "helix"]),
}

# Basis set keywords
BASIS_KEYWORDS: Dict[str, KeywordInfo] = {
    "spherical": KeywordInfo(name="spherical", description="Use spherical harmonic basis functions", section="basis"),
    "cartesian": KeywordInfo(name="cartesian", description="Use Cartesian basis functions", section="basis"),
    "library": KeywordInfo(name="library", description="Use basis set from library", section="basis", arguments=BASIS_SETS),
    "file": KeywordInfo(name="file", description="Read basis set from file", section="basis", arguments=["filename"]),
}

# All keywords by section
ALL_KEYWORDS: Dict[str, Dict[str, KeywordInfo]] = {
    "top": TOP_LEVEL_KEYWORDS,
    "dft": DFT_KEYWORDS,
    "scf": SCF_KEYWORDS,
    "geometry": GEOMETRY_KEYWORDS,
    "basis": BASIS_KEYWORDS,
}


def get_keyword_info(name: str, section: str = "top") -> Optional[KeywordInfo]:
    """Get information about a specific keyword."""
    section_dict = ALL_KEYWORDS.get(section, {})
    return section_dict.get(name.lower())


def get_all_keywords() -> List[str]:
    """Get a list of all available keyword names."""
    keywords: Set[str] = set()
    for section_dict in ALL_KEYWORDS.values():
        keywords.update(section_dict.keys())
    return sorted(list(keywords))


def get_keywords_by_section(section: str) -> List[str]:
    """Get keywords for a specific section."""
    section_dict = ALL_KEYWORDS.get(section.lower(), {})
    return sorted(list(section_dict.keys()))


def get_section_keywords(section: str) -> Dict[str, KeywordInfo]:
    """Get all keyword info objects for a specific section."""
    return ALL_KEYWORDS.get(section.lower(), {}).copy()


def is_valid_keyword(name: str, section: str = "top") -> bool:
    """Check if a keyword is valid."""
    return get_keyword_info(name, section) is not None


def get_keyword_sections() -> List[str]:
    """Get a list of all available keyword sections."""
    return sorted(list(ALL_KEYWORDS.keys()))
