#!/usr/bin/env bash
# 下载源数据到 data/，供 scripts/build.py 使用。在仓库根目录运行：bash scripts/prepare.sh
set -euo pipefail
mkdir -p data/ne

# 1912 年以前的政权轮廓（GPL-3.0）
if [ ! -d data/historical-basemaps ]; then
  git clone --depth 1 https://github.com/aourednik/historical-basemaps.git data/historical-basemaps
fi

# Natural Earth 河流、湖泊（公有领域）
NE=https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson
curl -sSL -o data/ne/rivers.geojson "$NE/ne_50m_rivers_lake_centerlines.geojson"
curl -sSL -o data/ne/lakes.geojson  "$NE/ne_50m_lakes.geojson"

# 陆地与今日国界（world-atlas，取自 Natural Earth 1:50m）
npm install --silent
node -e '
const t=require("topojson-client"),fs=require("fs");
const land=JSON.parse(fs.readFileSync("node_modules/world-atlas/land-50m.json"));
fs.writeFileSync("data/ne/land.geojson",JSON.stringify(t.feature(land,land.objects.land)));
const c=JSON.parse(fs.readFileSync("node_modules/world-atlas/countries-50m.json"));
fs.writeFileSync("data/ne/countries.geojson",JSON.stringify(t.feature(c,c.objects.countries)));
'
echo "源数据已就绪：data/"
