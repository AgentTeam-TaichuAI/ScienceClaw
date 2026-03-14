#!/usr/bin/env bash
set -euo pipefail

# 构建 ScienceClaw 下所有带 Dockerfile 的子目录镜像
# 镜像名 = 文件夹名，版本 = 当前日期
# 支持多平台: linux/amd64, linux/arm64
#
# 用法:
#   ./new_release.sh                    # 构建全部模块
#   ./new_release.sh backend frontend   # 只构建指定模块

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCIENCECLAW="${SCRIPT_DIR}/ScienceClaw"
DATE="$(date +%Y%m%d)"
PLATFORMS="linux/amd64,linux/arm64"

# 本地 buildx 缓存目录，加速后续构建（可复用各层）
BUILDX_CACHE="${SCRIPT_DIR}/.buildx-cache"
mkdir -p "$BUILDX_CACHE"

# 可选: 设置 REGISTRY 后镜像名为 $REGISTRY/目录名:日期，并执行 push
# 例如: REGISTRY=myregistry.io/myuser ./new_release.sh
REGISTRY="${REGISTRY:-swr.cn-north-4.myhuaweicloud.com/claw}"
COMPOSE_RELEASE="${SCRIPT_DIR}/docker-compose-release.yml"

if [[ ! -d "$SCIENCECLAW" ]]; then
  echo "Error: ScienceClaw directory not found: $SCIENCECLAW"
  exit 1
fi

# 收集待构建模块列表
TARGETS=("$@")

modules=()
if [[ ${#TARGETS[@]} -gt 0 ]]; then
  for t in "${TARGETS[@]}"; do
    dir="${SCIENCECLAW}/${t}"
    if [[ ! -d "$dir" ]]; then
      echo "Error: module not found: $t"
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
    image="${REGISTRY}/${name}:release-${DATE}"
    push_flag="--push"
  else
    image="${name}:release-${DATE}"
    push_flag=""
  fi

  extra_contexts=""
  if grep -q '\-\-from=websearch' "$dockerfile" 2>/dev/null; then
    extra_contexts="--build-context websearch=${SCIENCECLAW}/websearch"
  fi
  echo "Building: $image (platforms: $PLATFORMS)"
  docker buildx build \
    --platform "$PLATFORMS" \
    --cache-from "type=local,src=${BUILDX_CACHE}" \
    --cache-to "type=local,dest=${BUILDX_CACHE},mode=max" \
    --provenance=false \
    -t "$image" \
    -f "$dockerfile" \
    $extra_contexts \
    $push_flag \
    "$dir"

  # 构建成功后更新 docker-compose-release.yml 中对应 image 标签
  if [[ -f "$COMPOSE_RELEASE" ]]; then
    basename_dir="$(basename "$dir")"
    sed -i '' "s|^\([[:space:]]*\)image:.*${basename_dir}:.*|\1image: ${image}|g" "$COMPOSE_RELEASE"
    echo "Updated compose-release: ${basename_dir} -> ${image}"
  fi
done

echo "Done. Date tag: $DATE"
