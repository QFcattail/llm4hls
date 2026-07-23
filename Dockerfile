# =============================================================================
# FPGA Agent - FPT'26 Track A submission Docker image
#
# This Dockerfile packages the agent + harness + Python deps so the whole
# pipeline (csim/synth/cosim/grade) runs inside the container. It mirrors the
# official contest/fpt26-harness/vitis.dockerfile dependency layer but uses a
# plain Ubuntu base (the Xilinx runtime base image is unavailable offline and
# not needed for software-only csim/synth/cosim).
#
# Vitis 2025.2 itself is NOT baked into the image (~92 GB, license-bound).
# Instead it is bind-mounted from the host at run time and located via the
# LLM4HLS_VITIS_HLS_ROOT env var -- exactly the model the official
# run-vitis.sh uses. See docker-run.sh for the mount wiring.
#
# Build:
#   docker build -t fpga-agent:0.7.4 .
#
# Run (mount host Vitis + tasks, then run one task):
#   ./docker-run.sh contest/fpt26-harness/tasks/projection_bugfix
#   ./docker-run.sh contest/fpt26-harness/tasks/projection_bugfix --backend deepseek
#
# The agent runs as a non-root user "agent" (uid 1000) with passwordless sudo.
# =============================================================================

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# ---- 1. Locale + basic tools (mirrors official vitis.dockerfile) -----------
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl wget git sudo locales bash \
      && locale-gen en_US.UTF-8 \
      && rm -rf /var/lib/apt/lists/*

ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

# ---- 2. Vitis HLS runtime dependencies (from official vitis.dockerfile) ----
# These libraries are required by vitis-run --mode hls (csim/synth/cosim).
# Kept as one layer to reduce image size; all are --no-install-recommends.
RUN apt-get update && apt-get install -y --no-install-recommends \
      gawk gcc g++ make cmake automake autoconf libtool texinfo \
      zlib1g-dev libssl-dev openssl libncurses-dev libncurses5-dev \
      libncursesw5-dev flex bison diffstat chrpath socat \
      python3 python3-pip python3-git python3-jinja2 python3-pexpect \
      xz-utils unzip gzip tar cpio gnupg perl xvfb \
      iproute2 net-tools iputils-ping lsb-release \
      libftdi1 libftdi1-2 util-linux sysvinit-utils \
      libegl1-mesa libsdl1.2-dev \
      liberror-perl xtrans-dev \
      libxcb-randr0-dev libxcb-xtest0-dev libxcb-xinerama0-dev \
      libxcb-shape0-dev libxcb-xkb-dev \
      ocl-icd-libopencl1 opencl-headers ocl-icd-opencl-dev \
    && dpkg --add-architecture i386 && apt-get update \
    && apt-get install -y --no-install-recommends \
      lib32stdc++6 libstdc++6:i386 zlib1g:i386 \
      libgtk2.0-0:i386 libfontconfig1:i386 libx11-6:i386 \
      libxext6:i386 libxrender1:i386 libsm6:i386 libtinfo5 \
      gcc-multilib \
    && echo "dash dash/sh boolean false" | debconf-set-selections \
    && dpkg-reconfigure -f noninteractive dash \
    && rm -rf /var/lib/apt/lists/*

# ---- 3. Python 3.12 + TUI deps (textual, rich) -----------------------------
# The agent/harness core is pure stdlib, but the TUI dashboard needs
# textual + rich. We install Python 3.12 from deadsnakes (tomllib stdlib
# requires 3.11+; project targets 3.12), then create a venv at /opt/venv.
# A venv is used instead of system pip because Python 3.12 removed distutils
# (PEP 632), which breaks the distro-shipped python3-pip. The venv ships its
# own pip that works with 3.12. /opt/venv/bin is prepended to PATH so
# `python3` resolves to 3.12 everywhere.
RUN apt-get update && apt-get install -y --no-install-recommends \
      software-properties-common \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
      python3.12 python3.12-venv python3.12-dev \
    && rm -rf /var/lib/apt/lists/* \
    && python3.12 -m venv /opt/venv \
    && /opt/venv/bin/python3 --version

ENV PATH=/opt/venv/bin:$PATH

RUN python3 -m pip install --no-cache-dir --upgrade pip \
      -i https://pypi.tuna.tsinghua.edu.cn/simple \
    && python3 -m pip install --no-cache-dir \
      -i https://pypi.tuna.tsinghua.edu.cn/simple \
      textual==0.86.2 \
      rich==13.9.4

# ---- 4. Non-root user (agent) with passwordless sudo -----------------------
RUN useradd -m -s /bin/bash -u 1000 agent \
    && echo "agent ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# ---- 5. Project layout -----------------------------------------------------
# /opt/fpga-agent is the project root inside the image. The harness lives
# under contest/fpt26-harness/ and is found via sys.path injection in the
# entry scripts (fpga-agent.py / scripts/run_agent.py already do this).
WORKDIR /opt/fpga-agent

# Copy everything (filtered by .dockerignore), then fix ownership.
COPY --chown=agent:agent . /opt/fpga-agent/

# Ensure runs/ exists and is writable by the agent user (outputs are
# bind-mounted over this at run time, but create it so --help / dry runs
# don't fail on a missing dir).
RUN mkdir -p /opt/fpga-agent/runs && chown agent:agent /opt/fpga-agent/runs

# Vitis root: the host-installed Vitis 2025.2 is mounted at run time to the
# same host path (e.g. /home/admin/Xilinx/2025.2/Vitis). settings64.sh
# hardcodes absolute paths to sibling dirs, so the mount must preserve the
# host path -- docker-run.sh passes LLM4HLS_VITIS_HLS_ROOT accordingly.
ENV LLM4HLS_VITIS_HLS_ROOT=/home/admin/Xilinx/2025.2/Vitis
# Tasks dir is mounted from host so the same image can run any task.
ENV LLM4HLS_TASKS_ROOT=/opt/fpga-agent/contest/fpt26-harness/tasks

USER agent

# Default entry: CLI driver on a task dir. Override with docker-run.sh
# (which also handles the Vitis mount + .env). TUI mode needs a TTY, so
# for interactive use run with `docker run -it ...`.
ENTRYPOINT ["python3", "scripts/run_agent.py"]
CMD ["--help"]
