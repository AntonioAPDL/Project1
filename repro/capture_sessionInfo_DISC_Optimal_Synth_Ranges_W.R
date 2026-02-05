#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
out_path <- if (length(args) >= 1) args[[1]] else "sessionInfo.txt"

sink(out_path)
cat("Timestamp: ", format(Sys.time(), "%Y-%m-%d %H:%M:%S %Z"), "\n", sep = "")
cat("R.version.string: ", R.version.string, "\n", sep = "")
cat("Sys.info:\n")
print(Sys.info())
cat("\nLibPaths:\n")
print(.libPaths())

cat("\nSession info:\n")
print(sessionInfo())
sink()
