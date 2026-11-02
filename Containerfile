FROM docker.io/library/ubuntu:24.04

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential clang flex bison g++ gawk gcc-multilib g++-multilib \
    gettext git libncurses-dev libssl-dev libelf-dev python3 python3-setuptools \
    python3-pyelftools rsync swig unzip zlib1g-dev file wget curl \
    ca-certificates patch perl time zstd xz-utils jq device-tree-compiler \
    u-boot-tools squashfs-tools cpio bash bc bzip2 diffutils findutils \
    && rm -rf /var/lib/apt/lists/*

USER 1000:1000
WORKDIR /work
ENV LC_ALL=C.UTF-8 LANG=C.UTF-8
