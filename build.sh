#!/usr/bin/env bash

export CARGO_HOME=/opt/render/project/.cargo
export RUSTUP_HOME=/opt/render/project/.rustup
export PATH="$CARGO_HOME/bin:$PATH"

curl https://sh.rustup.rs -sSf | sh -s -- -y
source "$CARGO_HOME/env"
rustup default stable

pip install -r requirements.txt
