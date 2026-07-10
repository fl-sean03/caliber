---
name: iff-parameters
description: Search, retrieve, compare, and export INTERFACE Force Field (IFF) parameters for molecular dynamics simulations. Use BEFORE searching literature for force field parameters — IFF covers metals, minerals, oxides, clays, and organic interfaces with validated, citation-ready values.
allowed-tools:
  - Bash
  - Read
  - Write
---

# INTERFACE Force Field Parameters

The Heinz Lab maintains a curated, versioned database of INTERFACE Force Field (IFF) parameters. **Always check here first** before searching literature for LJ parameters, bond constants, or other force field data.

## When to Use This Skill

Use this skill when you need:
- LJ parameters for metals (Au, Ag, Cu, Ni, Pt, Pd, Pb, Al)
- Parameters for metal oxides (Al₂O₃, SiO₂, clays)
- Parameters for ionic liquids, CO₂, MOFs
- CVFF (.frc) files for LAMMPS simulations
- CHARMM (.prm) files for NAMD/OpenMM simulations
- To compare two parameter sets
- To compose custom force fields from base + extensions

**Do NOT use this skill for:**
- EAM/MEAM potentials (use resource-acquisition instead)
- ReaxFF parameters (use resource-acquisition instead)
- ML potentials like MACE/CHGNet (use mlip-simulation instead)
- Materials not covered by IFF (check coverage below)

## Materials Coverage

| Bundle | Materials | Atom Types | Format |
|--------|-----------|------------|--------|
| cvff-interface-v1-5 | Ag, Al, Au, Cu, Ni, Pb, Pd, Pt, silica, clays | 180 | CVFF |
| cvff-iff-metal-oxides-v2 | Al₂O₃, SiO₂, clays, alumina surfaces | 280 | CVFF |
| cvff-iff-ils | Ionic liquids, CO₂, MOFs | 224 | CVFF |
| iff-charmm36-metal-alumina-v8 | FCC metals, Al₂O₃ | 239 | CHARMM |

**If your material is not listed above**, fall back to the `resource-acquisition` skill for literature search.

## Prerequisites

```bash
# Check if iff-parameters is installed
python3 -c "from iff_parameters import list_available; print('OK:', len(list_available()), 'bundles')"

# If not installed:
pip install git+https://github.com/fl-sean03/upm.git
pip install git+https://github.com/fl-sean03/iff-parameters.git
```

---

## Core Operations

### 1. Search by Material

"Do we have parameters for gold?"

```python
from iff_parameters import search_by_material

results = search_by_material("Au")
for r in results:
    print(f"  {r['name']} ({r['format']}) — {r['materials']}")
```

### 2. Search by Atom Type

"What are the LJ parameters for atom type Au?"

```python
from upm.registry.discovery import discover_local_packages
from upm.registry.index import PackageIndex
from iff_parameters import get_data_dir

index = PackageIndex(discover_local_packages(get_data_dir()))
results = index.search_atom_type("Au")

for r in results:
    print(f"  {r.package_name}: LJ_A={float(r.row['lj_a']):.1f}, LJ_B={float(r.row['lj_b']):.5f}")
```

### 3. Get All Parameters from a Bundle

"Load the full parameter set for canonical IFF v1.5"

```python
from upm.bundle.io import load_package
from iff_parameters import get_data_dir

bundle = load_package(get_data_dir() / "cvff-interface-v1-5" / "v1.0")

# Access any table
atom_types = bundle.tables["atom_types"]  # DataFrame
bonds = bundle.tables.get("bonds")        # DataFrame or None
angles = bundle.tables.get("angles")
torsions = bundle.tables.get("torsions")
equivalences = bundle.tables.get("equivalences")
```

### 4. Export .frc File for LAMMPS

"Give me a complete .frc file I can use with msi2lmp"

```python
from upm.bundle.io import load_package
from upm.codecs.msi_frc import write_frc
from iff_parameters import get_data_dir

bundle = load_package(get_data_dir() / "cvff-interface-v1-5" / "v1.0")
write_frc("simulation.frc", tables=bundle.tables, mode="full")
# → Complete .frc file ready for: msi2lmp systemname -class 1 -frc simulation.frc
```

### 5. Export .prm File for NAMD

```python
from upm.bundle.io import load_package
from upm.codecs.charmm_prm import write_prm
from iff_parameters import get_data_dir

bundle = load_package(get_data_dir() / "iff-charmm36-metal-and-alumina-phases-v8" / "v1.0")
write_prm("simulation.prm", tables=bundle.tables)
```

### 6. Compare Two Parameter Sets

"What's different between the base IFF and the metal oxides version?"

```python
from upm.registry.diff import diff_tables
from upm.bundle.io import load_package
from iff_parameters import get_data_dir

dd = get_data_dir()
pkg1 = load_package(dd / "cvff-interface-v1-5" / "v1.0")
pkg2 = load_package(dd / "cvff-iff-metal-oxides-v2" / "v1.0")

diff = diff_tables(pkg1.tables, pkg2.tables)
print(diff.summary())
# Shows: added types, removed types, changed parameter values
```

### 7. Compose Custom Force Field (Base + Extension + Patch)

"I need IFF v1.5 as a base, plus the metal oxide types, with a tweaked Au epsilon"

```python
from upm.compose import ParameterLayer, stack_layers, export_frc
from iff_parameters import get_data_dir
from pathlib import Path

dd = get_data_dir()

# Load base and extension
base = ParameterLayer.from_bundle(Path(dd) / "cvff-interface-v1-5" / "v1.0")
ext = ParameterLayer.from_bundle(Path(dd) / "cvff-iff-metal-oxides-v2" / "v1.0")

# Create a parameter patch (only the values you want to change)
patch = ParameterLayer.from_dict(
    {"atom_types": {"Au": {"lj_b": 7100.0, "lj_a": 2400000.0}}},
    name="au-optimized",
)

# Stack: base + extension + patch (later layers override earlier)
stacked = stack_layers([base, ext, patch])

# Export monolithic .frc for msi2lmp
export_frc(stacked, "custom_simulation.frc")
```

---

## Integration with LAMMPS Simulations

When setting up a LAMMPS simulation that needs IFF parameters:

1. **Check coverage:** `search_by_material("your_material")`
2. **If covered:** Export .frc file and use with msi2lmp
3. **If NOT covered:** Fall back to `resource-acquisition` skill for literature search
4. **Always cite:** Include the IFF reference in your report

### LAMMPS Workflow Example

```python
# 1. Export the force field
from upm.bundle.io import load_package
from upm.codecs.msi_frc import write_frc
from iff_parameters import get_data_dir

bundle = load_package(get_data_dir() / "cvff-interface-v1-5" / "v1.0")
write_frc("/path/to/sim/cvff_iff.frc", tables=bundle.tables, mode="full")

# 2. Run msi2lmp (in Bash)
# msi2lmp systemname -class 1 -frc cvff_iff.frc

# 3. The generated data file has all parameters embedded
```

---

## Citation

When using IFF parameters, always cite:

> Heinz, H.; Lin, T.-J.; Mishra, R. K.; Emami, F. S. "Thermodynamically Consistent Force Fields for the Assembly of Inorganic, Organic, and Biological Nanostructures: The INTERFACE Force Field." *Langmuir* 2013, 29, 1754–1765. DOI: 10.1021/la3038846

Check individual bundle provenance for additional citations:
```python
import json
from iff_parameters import get_data_dir

manifest = json.loads((get_data_dir() / "cvff-interface-v1-5" / "v1.0" / "manifest.json").read_text())
doi = manifest.get("provenance", {}).get("publication_doi")
```

---

## Troubleshooting

**"No bundles found"** — Package not installed. Run:
```bash
pip install git+https://github.com/fl-sean03/iff-parameters.git
```

**"Atom type not found"** — The material may not be covered by IFF. Check coverage table above. Fall back to `resource-acquisition` for literature search.

**"Which bundle should I use?"** — For LAMMPS: use `cvff-*` bundles. For NAMD/OpenMM: use `iff-charmm36-*`. If unsure, use `cvff-interface-v1-5` as the broadest baseline.

**"Parameters seem wrong"** — Always cross-reference with the original publication. Use `diff_tables()` to compare against the canonical v1.5 baseline.
