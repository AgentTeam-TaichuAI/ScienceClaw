#!/usr/bin/env bash
set -euo pipefail

export DOCKER_BUILDKIT=1
VERSION="v0.0.4"

# 构建 ScienceClaw 下所有带 Dockerfile 的子目录镜像
# 镜像标签 = release-${VERSION}
# 支持多平台: linux/amd64, linux/arm64
#
# 用法:
#   ./release.sh                    # 构建全部模块
#   ./release.sh backend frontend   # 只构建指定模块

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCIENCECLAW="${SCRIPT_DIR}/ScienceClaw"
PLATFORMS="linux/amd64,linux/arm64"
REGISTRY="${REGISTRY:-swr.cn-north-4.myhuaweicloud.com/claw}"
COMPOSE_RELEASE="${SCRIPT_DIR}/docker-compose-release.yml"

if [[ ! -d "$SCIENCECLAW" ]]; then
  echo "Error: ScienceClaw directory not found: $SCIENCECLAW"
  exit 1
fi

targets=("$@")
modules=()

if [[ ${#targets[@]} -gt 0 ]]; then
  for target in "${targets[@]}"; do
    dir="${SCIENCECLAW}/${target}"
    if [[ ! -d "$dir" ]]; then
      echo "Error: module not found: $target"
      exit 1
    fi
    modules+=("$dir")
  done
else
  for dir in "$SCIENCECLAW"/*; do
    [[ -d "$dir" ]] && modules+=("$dir")
  done
fi

for dir in "${modules[@]}"; do
  name="scienceclaw-$(basename "$dir")"
  dockerfile="${dir}/Dockerfile"
  if [[ ! -f "$dockerfile" ]]; then
    echo "Skip (no Dockerfile): $name"
    continue
  fi

  if [[ -n "$REGISTRY" ]]; then
    image="${REGISTRY}/${name}:release-${VERSION}"
    push_flag=(--push)
    cache_flags=(
      --cache-from "type=registry,ref=${REGISTRY}/${name}:buildcache"
      --cache-to "type=registry,ref=${REGISTRY}/${name}:buildcache,mode=max"
    )
  else
    image="${name}:release-${VERSION}"
    push_flag=()
    cache_flags=()
  fi

  extra_contexts=()
  if grep -q '\-\-from=websearch' "$dockerfile" 2>/dev/null; then
    extra_contexts=(--build-context "websearch=${SCIENCECLAW}/websearch")
  fi

  echo "Building: $image (platforms: $PLATFORMS)"
  docker buildx build \
    --builder scienceclaw-builder \
    --platform "$PLATFORMS" \
    --provenance=false \
    "${cache_flags[@]}" \
    -t "$image" \
    -f "$dockerfile" \
    "${extra_contexts[@]}" \
    "${push_flag[@]}" \
    "$dir"

  if [[ -f "$COMPOSE_RELEASE" ]]; then
    module_name="$(basename "$dir")"
    sed -i.bak -E "s|(^[[:space:]]*image:[[:space:]]*).*/scienceclaw-${module_name}:release-v[^[:space:]]+|\\1${image}|g" "$COMPOSE_RELEASE"
    rm -f "${COMPOSE_RELEASE}.bak"
  fi
done

echo "Done. Version: $VERSION"
