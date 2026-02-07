#!/usr/bin/env Rscript

library(testthat)

test_dir("tests/testthat", reporter = "summary")
