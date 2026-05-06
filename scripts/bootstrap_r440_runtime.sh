#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-/data/muscat_data/jaguir26/project1_ucsc_phd/repro/runtime/r-4.4.0}"
JOBS="${JOBS:-4}"

SRC_DIR="${ROOT}/src"
BUILD_DIR="${ROOT}/build"
INSTALL_DIR="${ROOT}/install"
TARBALL="${SRC_DIR}/R-4.4.0.tar.gz"
SRC_TREE="${SRC_DIR}/R-4.4.0"

mkdir -p "${SRC_DIR}" "${BUILD_DIR}" "${INSTALL_DIR}"

if [[ ! -f "${TARBALL}" ]]; then
  curl -L -o "${TARBALL}" https://cran.r-project.org/src/base/R-4/R-4.4.0.tar.gz
fi

if [[ ! -d "${SRC_TREE}" ]]; then
  tar -xzf "${TARBALL}" -C "${SRC_DIR}"
fi

cd "${BUILD_DIR}"
rm -f Makefile
"${SRC_TREE}/configure" \
  --prefix="${INSTALL_DIR}" \
  --enable-R-shlib \
  --with-blas \
  --with-lapack \
  --with-readline=no \
  > configure.log 2>&1

make -j"${JOBS}" > build.log 2>&1
make install > install.log 2>&1

echo "Built R 4.4.0 at:"
echo "  ${INSTALL_DIR}/bin/R"
"${INSTALL_DIR}/bin/R" --version | sed -n '1,3p'
