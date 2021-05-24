#!/bin/sh
docker build -t plan_ngs_prep .
mkdir -p $HOME/bin
grep -qxF 'export "PATH=$PATH:$HOME/bin"' ~/.bash_profile || echo 'export "PATH=$PATH:$HOME/bin"' >> ~/.bash_profile
install -m 0755 plan-ngs-prep-wrapper $HOME/bin/plan-ngs-prep
