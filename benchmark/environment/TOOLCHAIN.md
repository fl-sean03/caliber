# Pinned toolchain — the reference environment

> **Scope.** This is the exact toolchain the Caliber oracle values and calibration runs
> were produced with, interrogated from the reference machine (not transcribed from
> plans). It is the source of truth for every version pin in
> [`Dockerfile`](Dockerfile). Release gate: an outside machine reproduces one full
> task run + grade from the public docs alone — see [`smoke_task.md`](smoke_task.md)
> and the honest gap list in [`GAPS.md`](GAPS.md).

All versions below were read from the live binaries/environment on the reference
machine (2026-07-13): QE headers from running `pw.x` on an empty input, LAMMPS from
`lmp -h`, python pins from `pip list` inside the `science-tools` env, CUDA from
`nvcc --version` + `nvidia-smi`. Local build provenance (paths under `~/builds/`) is
cited as reference-machine provenance only; nothing in the container depends on those
paths.

## Reference machine

| Item | Value |
|------|-------|
| OS | Ubuntu 24.04.4 LTS, kernel 6.8.0-124-generic, x86_64 |
| GPU | NVIDIA RTX 5080 Laptop (Blackwell, compute capability 12.0 = `sm_120`), 16 GB |
| Driver | 580.159.03 (driver-side CUDA API 13.0) |
| CUDA toolkit | 12.8 (`nvcc` V12.8.93, `/usr/local/cuda-12.8`) |
| GPU Fortran toolchain | NVIDIA HPC SDK 25.11 (nvfortran 25.11-0; bundled CUDA 12.9/13.0 math libs) |
| System compilers | GCC/gfortran 13.3.0 (Ubuntu 13.3.0-6ubuntu2~24.04.1) |
| MPI | Open MPI 4.1.6 (Ubuntu apt) |

## Pinned components

| Component | Exact version | How pinned in container | Why it matters for oracle/agent parity |
|-----------|---------------|-------------------------|----------------------------------------|
| Base OS | Ubuntu 24.04 | `nvidia/cuda:12.8.1-*-ubuntu24.04` base image | glibc + apt library versions (OpenBLAS, FFTW) feed every QE number |
| Quantum ESPRESSO (CPU) | **7.5** (released 2025-08-15); source tarball sha256 `7e1f7a9a21b63192f5135218bee20a5321b66582e4756536681b76e9c59b3cc8` | built from the checksummed source tarball in the builder stage; CMake flags copied verbatim from the reference build (MPI+OpenMP, Release) | the primary DFT oracle engine; SCF totals reproduced to 1e-8 Ry between reference CPU/GPU builds |
| QE CPU build deps | gfortran 13.3.0 · Open MPI 4.1.6 · OpenBLAS 0.3.26 · FFTW 3.3.10 · CMake 3.28.3 | Ubuntu 24.04 apt (the distro pins these exact versions) | BLAS/LAPACK + FFT backends are the main source of last-digit numeric drift |
| Quantum ESPRESSO (GPU, optional) | 7.5, NVHPC 25.11, OpenACC/CUDA, **serial only** (`QE_ENABLE_MPI=OFF`), `QE_GPU_ARCHS=sm_120`, `QE_FFTW_VENDOR=Internal` | optional build stage (documented, off by default); NVHPC SDK version pinned in an `ARG` | speed only — oracle values are CPU/GPU-consistent to 1e-8 Ry on the reference validation (bulk Si); serial-only by design (NVHPC hpcx MPI hangs) |
| LAMMPS | **stable 22 Jul 2025 — Update 4** (`stable_22Jul2025_update4`), GNU C++ 13.3.0, C++17 | built from the tagged GitHub release tarball in the builder stage | the MD oracle engine (EAM/sw/tersoff tasks; melting points, elastic constants) |
| LAMMPS packages | `GPU KSPACE MANYBODY MOLECULE RIGID`; GPU pkg: API=CUDA, precision=**mixed**, arch=`sm_120`; **no MPI** (serial STUBS), OpenMP ON | identical `-D PKG_*` CMake flags; `GPU_ARCH` is a build `ARG` (see hardware note below) | missing packages = task can't run; **mixed** GPU precision is a known determinism trade-off (flagged below) |
| Python | **3.11.15** (conda env `science-tools`) | micromamba env with `python=3.11` + `pip` pins | MLIP + analysis layer; ASE/pymatgen numerics feed reported values |
| numpy | 2.4.6 | `pip install numpy==2.4.6` | array numerics everywhere; numpy 1→2 breaks several MLIP stacks |
| scipy | 1.17.1 | pip pin | fitting/EOS analysis (e.g. Birch–Murnaghan) |
| ase | 3.29.0 | pip pin | the driver for every MLIP calculation |
| pymatgen | 2026.5.4 (core 2026.5.18) | pip pin | structure handling, symmetry, MP interop |
| torch | **2.11.0+cu128** | pip pin from the PyTorch cu128 index | MLIP inference backend; must match the CUDA runtime line |
| mace-torch | 0.3.16 | pip pin | MACE-MP-0 foundation model used in oracle cross-checks |
| chgnet | 0.4.2 | pip pin | CHGNet (weights bundled with the package) |
| matgl | 4.0.3 | pip pin | M3GNet; **only** `M3GNet-PES-MatPES-PBE-2025.2` exists in 4.x (the MP-2021 checkpoint was retired upstream) |
| torch-sim-atomistic | 0.3.0 | pip pin | high-throughput batched MLIP screening |
| e3nn / matscipy | 0.4.4 / 1.2.0 | pip pins | MACE dependency / analysis utilities |
| xtb | 6.7.1 (conda-forge) | conda-forge pin | semi-empirical QM (chemistry tasks) |
| CREST | 3.0.2 (conda-forge) | conda-forge pin | conformer sampling (chemistry tasks) |
| requests / PyYAML / pytest | 2.34.2 / 6.0.3 / 9.1.1 | pip pins | harness + judge client + scoring self-tests |
| Claude Code CLI | 2.1.207 (`claude`) | `npm install -g @anthropic-ai/claude-code@2.1.207` (Node 20 LTS) | the native-claude harness (`harnesses/native-claude/asw_native.py`) spawns `claude -p --input-format stream-json`; harness version is provenance |
| Frozen judge | OpenAI `gpt-5.5-2026-04-23` (API-side; pinned in `scoring/judge_openai.py`) | not containerized — reached at runtime via `OPENAI_API_KEY` | grading provenance; a floating judge alias would silently change grades |

The harness and scoring layers themselves are stdlib-only Python (plus `requests` for
the judge client) — no additional pins needed beyond the interpreter.

## Hardware-specificity: where the oracle could be machine-dependent

**Governing mitigation — method-pinning.** Caliber's ground truth is defined by
*inputs + method* (pseudopotential files with checksums, cutoffs, k-meshes,
convergence thresholds, potential files, ensemble/timestep settings), not by the
hardware that executed them. Sealed anchor tolerances are set orders of magnitude
wider than cross-platform numerical noise (anchors are physical tolerances — meV/atom,
mJ/m², K — not last-digit float equality). A run on different silicon that follows
the pinned method must land inside the same anchors. The residual risks below are
therefore about *rare tail events*, not expected grade flips — but they are real and
stated honestly.

| Risk | Detail | Residual exposure & mitigation |
|------|--------|--------------------------------|
| GPU non-determinism | cuBLAS/cuFFT reduction order is not bitwise-reproducible run-to-run, and the LAMMPS GPU package uses **mixed** precision | SCF convergence thresholds (≤1e-8 Ry) and MD ensemble averaging absorb this; reference cross-check showed CPU vs GPU QE agreement to 1e-8 Ry. Residual: a marginal SCF could converge in ±1 iteration; MD trajectories diverge chaotically (only *ensemble* observables are anchored, never trajectories). |
| `sm_120` binaries | Reference GPU builds target Blackwell only; they will not run on A100 (`sm_80`) / H100 (`sm_90`) | `GPU_ARCH` is a container build `ARG`; CPU paths (QE CPU-MPI, LAMMPS serial) are the parity baseline and are architecture-independent. Oracle values must never be *defined* by a GPU-only run without a CPU cross-check. |
| FFT backend variance | Reference CPU QE uses system FFTW 3.3.10; the GPU build deliberately uses QE's internal FFTW (OpenMP-runtime clash) + cuFFT; other builds may use MKL | Differences appear at ~1e-10–1e-8 Ry, far inside anchor tolerances. Residual: pathological near-degenerate systems; avoided at task-authoring time (anchors must be stable under backend swap). |
| BLAS backend + threading | OpenBLAS 0.3.26 with OpenMP; threaded reductions are order-nondeterministic; MKL substitution changes last digits | Same tolerance argument. Container pins OpenBLAS via apt. Run convention `OMP_NUM_THREADS=1` under `mpirun` (oversubscription changes wall time, not values). |
| MLIP inference device | torch on GPU (TF32/cuDNN autotune) vs CPU can differ at ~1e-5 eV/atom; different GPU generations differ less | Anchor tolerances for MLIP-derived quantities are meV-scale or larger. Weights are version-pinned via package pins; checksummed weight escrow is an open gap (GAPS.md). |
| MPI decomposition | QE totals can vary in the last digits with rank count | Reference validation: serial vs `-np 4` agreed to 1e-8 Ry. Oracle methods record the rank count used. |
| Driver / CUDA runtime skew | Container ships CUDA 12.8 runtime; the *host driver* is outside the image (reference: 580.159.03) | Standard nvidia-container-toolkit constraint: host driver must support CUDA 12.8. Documented in smoke_task.md prerequisites. |

**Bottom line:** correctness parity rests on the CPU code paths + method-pinning +
physically-wide anchors; GPU is an accelerator, not an arbiter. Any future task whose
anchor would be sensitive to the differences above is mis-authored and must be caught
at authoring time (backend-swap stability is part of oracle sign-off).

## Provenance of the reference builds

- QE 7.5 builds (CPU-MPI and GPU-serial) live at `~/builds/qe/` on the reference
  machine, with full build commands, the source checksum, validation inputs, and a
  CPU/GPU cross-validation table in `~/builds/qe/BUILD_NOTES.md`. The Dockerfile's QE
  stage is a transcription of that build recipe.
- LAMMPS lives at `~/builds/lammps/build/lmp` (CMake cache retained; flags read from
  it directly).
- The python env is the `science-tools` conda env on the reference machine; this
  document is the *pinned* record of it (the Dockerfile consumes these pins directly).
