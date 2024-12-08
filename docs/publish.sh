#!/bin/bash

rm -rf /tmp/gh-pages
git clone https://github.com/us4useu/gui4us.git --branch gh-pages --single-branch /tmp/gh-pages
make clean html
cp -r docs/_build/html/* /tmp/gh-pages/
cd gh-pages
touch .nojekyll
git add .
git commit -m "Updated GH pages." -a || true
git push