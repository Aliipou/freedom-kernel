# Benchmark Analysis

## Setup

Criterion benchmark: `freedom-kernel/benches/verify_throughput.rs`
Measures: `verify()` on a 100-claim registry with a single read action.

## Results

Status: PENDING — run `cd freedom-kernel && cargo bench` to populate.

## Target

< 1µs mean for 100-claim registry (Rust backend, reference machine).

## How to read results

Criterion outputs mean, standard deviation, and confidence intervals.
The "verify 100-claim registry" benchmark is the primary metric.

Last reviewed: 2026-05-16.
