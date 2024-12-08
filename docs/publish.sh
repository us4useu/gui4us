#!/bin/bash

set -e

rm -rf /tmp/gh-pages
git clone git@github.com:us4useu/gui4us.git --branch gh-pages --single-branch /tmp/gh-pages
make clean html
cp -r _build/html/* /tmp/gh-pages/
cd /tmp/gh-pages
touch .nojekyll
git add .
git commit -m "Updated GH pages." -a || true
git push