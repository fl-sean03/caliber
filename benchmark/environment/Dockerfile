# =============================================================================
# Caliber reference environment — DRAFT Dockerfile (v0)
#
# Goal: an outside machine reproduces one full Caliber task run + grade from the
# public docs alone (see smoke_task.md). Every version below is pinned from the
# interrogated reference machine — see TOOLCHAIN.md; do not bump a pin without
# updating TOOLCHAIN.md and re-validating the oracle cross-checks.
#
# Status: HONEST DRAFT. Known gaps between this file and a green `docker build`
# are enumerated in GAPS.md (QE external-submodule fetch, LAMMPS tarball
# checksum, MLIP weight escrow, image size). Nothing here is aspirational
# hand-waving: every build recipe is a transcription of the reference build.
#
# Build (CPU oracle stack, default):
#   docker build -f benchmark/environment/Dockerfile -t caliber:v0 .
# Build for a non-Blackwell GPU (e.g. A100):
#   docker build --build-arg GPU_ARCH=sm_80 -t caliber:v0-sm80 .
# Optional GPU-QE variant (NVHPC, large):
#   docker build --target runtime-gpuqe -t caliber:v0-gpuqe .
#
# Run context: the repository root (COPY paths assume it).
# =============================================================================

# ---- global pins (from TOOLCHAIN.md — the single source of truth) ----------
ARG UBUNTU_VERSION=24.04
ARG CUDA_VERSION=12.8.1
ARG QE_VERSION=7.5
ARG QE_SHA256=7e1f7a9a21b63192f5135218bee20a5321b66582e4756536681b76e9c59b3cc8
ARG LAMMPS_TAG=stable_22Jul2025_update4
# Reference GPU is Blackwell (sm_120). Override for other silicon; correctness
# parity rests on the CPU paths either way (TOOLCHAIN.md, hardware table).
ARG GPU_ARCH=sm_120
ARG NVHPC_VERSION=25.11
ARG PYTHON_VERSION=3.11
ARG CLAUDE_CODE_VERSION=2.1.207
ARG NODE_MAJOR=20

# =============================================================================
# Stage 1: qe-cpu-builder — Quantum ESPRESSO 7.5, CPU + MPI + OpenMP
#
# Plain Ubuntu base: the CPU oracle path has zero CUDA dependency, and building
# it on the distro toolchain reproduces the reference build exactly
# (gfortran 13.3, Open MPI 4.1.6, OpenBLAS 0.3.26, FFTW 3.3.10 — all pinned by
# Ubuntu 24.04 apt, which is why the base image version is itself a pin).
# =============================================================================
FROM ubuntu:${UBUNTU_VERSION} AS qe-cpu-builder
ARG QE_VERSION
ARG QE_SHA256

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential gfortran cmake git ca-certificates curl \
        openmpi-bin libopenmpi-dev libfftw3-dev libopenblas-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Source is fetched by checksum, not by trust in the URL.
WORKDIR /build
RUN curl -fsSL -o qe.tar.gz \
        "https://gitlab.com/QEF/q-e/-/archive/qe-${QE_VERSION}/q-e-qe-${QE_VERSION}.tar.gz" \
    && echo "${QE_SHA256}  qe.tar.gz" | sha256sum -c - \
    && tar xf qe.tar.gz && rm qe.tar.gz

# NOTE (GAPS.md G1): QE's CMake fetches three external submodules at configure
# time (wannier90, libmbd, devicexlib) — this step needs network. Vendoring
# them for a hermetic build is an open gap.
RUN mkdir build-cpu && cd build-cpu \
    && cmake -DCMAKE_C_COMPILER=mpicc -DCMAKE_Fortran_COMPILER=mpif90 \
             -DQE_ENABLE_MPI=ON -DQE_ENABLE_OPENMP=ON \
             -DCMAKE_BUILD_TYPE=Release \
             -DCMAKE_INSTALL_PREFIX=/opt/qe/cpu \
             /build/q-e-qe-${QE_VERSION} \
    && make -j"$(nproc)" \
    && make install \
    && cd / && rm -rf /build

# =============================================================================
# Stage 2: lammps-builder — LAMMPS stable_22Jul2025_update4, GPU package
#
# Needs the CUDA *devel* image for nvcc (geryon/GPU-package kernels). Built
# WITHOUT MPI to mirror the reference binary exactly (serial + OpenMP + GPU;
# the reference lmp links LAMMPS MPI STUBS). Mixed GPU precision matches the
# reference — a deliberate, documented determinism trade-off (TOOLCHAIN.md).
# =============================================================================
FROM nvidia/cuda:${CUDA_VERSION}-devel-ubuntu${UBUNTU_VERSION} AS lammps-builder
ARG LAMMPS_TAG
ARG GPU_ARCH

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential cmake git ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

# GAPS.md G2: upstream publishes no sha256 for release tarballs; the tag pin is
# the current integrity anchor. Record a checksum on first green build.
WORKDIR /build
RUN curl -fsSL -o lammps.tar.gz \
        "https://github.com/lammps/lammps/archive/refs/tags/${LAMMPS_TAG}.tar.gz" \
    && tar xf lammps.tar.gz && rm lammps.tar.gz

# Package set = exactly the reference build's ON list:
#   GPU KSPACE MANYBODY MOLECULE RIGID
# (covers eam/sw/tersoff many-body tasks, molecular FF tasks, kspace
# electrostatics, rigid-body integrators used by the pilot slate).
RUN cd lammps-${LAMMPS_TAG} && mkdir build && cd build \
    && cmake ../cmake \
        -D CMAKE_BUILD_TYPE=Release \
        -D BUILD_MPI=no \
        -D BUILD_OMP=yes \
        -D PKG_GPU=on -D GPU_API=cuda -D GPU_PREC=mixed -D GPU_ARCH=${GPU_ARCH} \
        -D PKG_KSPACE=on -D PKG_MANYBODY=on -D PKG_MOLECULE=on -D PKG_RIGID=on \
        -D CMAKE_INSTALL_PREFIX=/opt/lammps \
    && make -j"$(nproc)" \
    && make install \
    && cd / && rm -rf /build

# =============================================================================
# Stage 3 (OPTIONAL, skipped by default): qe-gpu-builder — QE 7.5 on NVHPC
#
# The GPU QE build is a speed path, never the parity arbiter (TOOLCHAIN.md).
# It is heavy (NVHPC devel image is ~10+ GB) and Blackwell-pinned on the
# reference machine, so it lives behind the `runtime-gpuqe` target. BuildKit
# skips this stage entirely unless that target is requested.
#
# Reference-build facts transcribed here:
#   * SERIAL ONLY (QE_ENABLE_MPI=OFF): NVHPC's bundled hpcx MPI hangs; never
#     mpirun this binary.
#   * QE_FFTW_VENDOR=Internal is REQUIRED: linking system fftw3_omp (GNU
#     OpenMP) against nvfortran's nvomp aborts at runtime with `libgomp: TODO`.
#     GPU FFTs use cuFFT regardless, so internal CPU FFTW costs nothing.
#   * Only the `pw` target is built; install is a manual copy of bin/pw.x.
# =============================================================================
FROM nvcr.io/nvidia/nvhpc:${NVHPC_VERSION}-devel-cuda_multi-ubuntu${UBUNTU_VERSION} AS qe-gpu-builder
ARG QE_VERSION
ARG QE_SHA256
ARG GPU_ARCH

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        cmake git ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
RUN curl -fsSL -o qe.tar.gz \
        "https://gitlab.com/QEF/q-e/-/archive/qe-${QE_VERSION}/q-e-qe-${QE_VERSION}.tar.gz" \
    && echo "${QE_SHA256}  qe.tar.gz" | sha256sum -c - \
    && tar xf qe.tar.gz && rm qe.tar.gz

RUN mkdir build-gpu && cd build-gpu \
    && cmake -DCMAKE_C_COMPILER=nvc -DCMAKE_Fortran_COMPILER=nvfortran \
             -DQE_ENABLE_MPI=OFF -DQE_ENABLE_CUDA=ON -DQE_ENABLE_OPENACC=ON \
             -DQE_ENABLE_OPENMP=ON -DQE_GPU_ARCHS=${GPU_ARCH} \
             -DQE_FFTW_VENDOR=Internal \
             -DCMAKE_BUILD_TYPE=Release \
             /build/q-e-qe-${QE_VERSION} \
    && make -j"$(nproc)" pw \
    && mkdir -p /opt/qe/gpu/bin && cp bin/pw.x /opt/qe/gpu/bin/pw.x \
    && cd / && rm -rf /build

# =============================================================================
# Stage 4: runtime — the default deliverable image
#
# CUDA *runtime* base (not devel): LAMMPS GPU + torch need the CUDA runtime
# libs only; dropping nvcc/headers saves multiple GB. Host driver must support
# CUDA 12.8 (nvidia-container-toolkit; reference driver 580.159.03).
# =============================================================================
FROM nvidia/cuda:${CUDA_VERSION}-runtime-ubuntu${UBUNTU_VERSION} AS runtime
ARG PYTHON_VERSION
ARG CLAUDE_CODE_VERSION
ARG NODE_MAJOR

ENV DEBIAN_FRONTEND=noninteractive

# Runtime libraries for the QE CPU build (MPI, BLAS, FFTW — the exact apt pins
# the binary was linked against) + Node for the Claude Code CLI harness.
RUN apt-get update && apt-get install -y --no-install-recommends \
        openmpi-bin libopenmpi3t64 libfftw3-double3 libfftw3-single3 \
        libopenblas0-openmp libgfortran5 libgomp1 \
        ca-certificates curl bzip2 git tini \
    && curl -fsSL "https://deb.nodesource.com/setup_${NODE_MAJOR}.x" | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Simulation engines from the builder stages.
COPY --from=qe-cpu-builder /opt/qe/cpu /opt/qe/cpu
COPY --from=lammps-builder /opt/lammps /opt/lammps

# --- Python: micromamba + the pinned science-tools stack ---------------------
# micromamba (single static binary) instead of a full conda: same conda-forge
# solver for xtb/CREST (Fortran binaries distributed only via conda-forge),
# tiny footprint, no base-env sprawl.
ENV MAMBA_ROOT_PREFIX=/opt/micromamba
RUN curl -fsSL https://micro.mamba.pm/api/micromamba/linux-64/latest \
        | tar -xj -C /usr/local/bin --strip-components=1 bin/micromamba \
    && micromamba create -y -n science-tools -c conda-forge \
        python=${PYTHON_VERSION} pip \
        xtb=6.7.1 crest=3.0.2 \
    && micromamba clean -a -y

# Exact pins from TOOLCHAIN.md. torch comes from the cu128 wheel index so the
# +cu128 build matches the container's CUDA runtime. Order matters: torch
# first, so the MLIP packages resolve against it instead of dragging in a
# different build.
# NOTE (GAPS.md G3): MLIP *weights* (MACE-MP-0, M3GNet-MatPES) are downloaded
# at first use, not baked here — checksummed escrow is an open gap.
RUN micromamba run -n science-tools pip install --no-cache-dir \
        --extra-index-url https://download.pytorch.org/whl/cu128 \
        torch==2.11.0 \
    && micromamba run -n science-tools pip install --no-cache-dir \
        numpy==2.4.6 scipy==1.17.1 \
        ase==3.29.0 pymatgen==2026.5.4 matscipy==1.2.0 \
        mace-torch==0.3.16 chgnet==0.4.2 matgl==4.0.3 e3nn==0.4.4 \
        torch-sim-atomistic==0.3.0 \
        requests==2.34.2 pyyaml==6.0.3 pytest==9.1.1

# --- Agent harness: Claude Code CLI (native-claude session-holder) -----------
# The harness itself (benchmark/harnesses/native-claude/asw_native.py) is
# stdlib Python; its only external dependency is this pinned CLI. Other
# harnesses (native-codex, native-grok) install their own CLIs — out of scope
# for v0 (GAPS.md G6).
RUN npm install -g "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}"

# --- Benchmark code -----------------------------------------------------------
# Build context = repo root. Only the public benchmark tree ships in the image;
# sealed keys/oracles live off-repo and are mounted at grade time (smoke_task.md).
COPY benchmark/ /opt/caliber/benchmark/

# --- Non-root user + /workspace convention ------------------------------------
# Agent runs never execute as root: a benchmark that grants an autonomous agent
# root inside its own scoring container is asking for un-diagnosable state.
# /workspace is the ONLY writable convention the harness relies on; each task
# rep gets /workspace/<task>/rep<r>/ws (mirrors the sweep layout).
RUN useradd -m -u 1000 -s /bin/bash caliber \
    && mkdir -p /workspace \
    && chown -R caliber:caliber /workspace /opt/caliber

ENV PATH=/opt/qe/cpu/bin:/opt/lammps/bin:${MAMBA_ROOT_PREFIX}/envs/science-tools/bin:${PATH} \
    QE_CPU=/opt/qe/cpu/bin \
    LMP=/opt/lammps/bin/lmp \
    OMP_NUM_THREADS=1

USER caliber
WORKDIR /workspace

# Secrets (ANTHROPIC_API_KEY, OPENAI_API_KEY) are injected at `docker run -e`;
# they are never baked into any layer — see smoke_task.md.
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/bin/bash"]

# =============================================================================
# Stage 5 (optional target): runtime-gpuqe — runtime + the NVHPC GPU pw.x
#
# Adds the serial GPU QE binary plus the NVHPC runtime libs it needs. The
# binary RPATHs into the SDK tree, so the relevant runtime subset must ship at
# the same prefix; the honest v0 approach copies the needed lib dirs (large —
# size optimization is GAPS.md G5).
# =============================================================================
FROM runtime AS runtime-gpuqe
ARG NVHPC_VERSION
USER root
COPY --from=qe-gpu-builder /opt/qe/gpu /opt/qe/gpu
COPY --from=qe-gpu-builder /opt/nvidia/hpc_sdk/Linux_x86_64/${NVHPC_VERSION}/compilers/lib \
     /opt/nvidia/hpc_sdk/Linux_x86_64/${NVHPC_VERSION}/compilers/lib
COPY --from=qe-gpu-builder /opt/nvidia/hpc_sdk/Linux_x86_64/${NVHPC_VERSION}/math_libs \
     /opt/nvidia/hpc_sdk/Linux_x86_64/${NVHPC_VERSION}/math_libs
COPY --from=qe-gpu-builder /opt/nvidia/hpc_sdk/Linux_x86_64/${NVHPC_VERSION}/cuda \
     /opt/nvidia/hpc_sdk/Linux_x86_64/${NVHPC_VERSION}/cuda
RUN chown -R caliber:caliber /opt/qe/gpu
ENV QE_GPU=/opt/qe/gpu/bin
USER caliber
# Serial only — never `mpirun` the GPU pw.x (NVHPC hpcx MPI hang, see stage 3).
