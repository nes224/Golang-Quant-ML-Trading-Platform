@echo off
echo Starting Rust Analysis Service...
cd Trading_Api\rust_analysis
set PATH=%USERPROFILE%\.cargo\bin;%PATH%
cargo run --release
