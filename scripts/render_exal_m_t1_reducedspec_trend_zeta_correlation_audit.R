suppressPackageStartupMessages({
  library(ggplot2)
  library(readr)
  library(dplyr)
})
outdir <- '/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_exal_m_t1_reducedspec_trend_zeta_correlation_audit_20260519'
dir.create(outdir, recursive=TRUE, showWarnings=FALSE)
ts_path <- file.path(outdir, 'trend_zeta_correlation_timeseries.csv')
summary_path <- file.path(outdir, 'trend_zeta_correlation_summary.csv')
if (!file.exists(ts_path) || !file.exists(summary_path)) stop('required CSV inputs missing')
ts <- read_csv(ts_path, show_col_types = FALSE) %>%
  mutate(quantile = factor(quantile, levels = c('q05','q20','q35','q50','q65','q80','q95')),
         idx = row_number())
summary_df <- read_csv(summary_path, show_col_types = FALSE)
TT <- max(ts$t, na.rm = TRUE)
windows <- c(2000, 1000, 500)
for (w in windows) {
  sub <- ts %>% filter(t >= TT - w + 1)
  p <- ggplot(sub, aes(x = t, y = corr, color = quantile)) +
    geom_hline(yintercept = 0, color = 'grey70', linewidth = 0.4) +
    geom_line(linewidth = 0.7) +
    labs(
      title = paste0('Trend-Zeta Posterior Correlation, Last ', w, ' Observations'),
      x = 'Historical index',
      y = 'corr(trend, zeta)'
    ) +
    theme_minimal(base_size = 12)
  ggsave(file.path(outdir, paste0('last', w, '_trend_zeta_correlation.png')), p, width = 10, height = 5, dpi = 150)
}
p_full <- ggplot(ts, aes(x = t, y = corr, color = quantile)) +
  geom_hline(yintercept = 0, color = 'grey70', linewidth = 0.4) +
  geom_line(linewidth = 0.6) +
  labs(title = 'Trend-Zeta Posterior Correlation, Full History', x = 'Historical index', y = 'corr(trend, zeta)') +
  theme_minimal(base_size = 12)
ggsave(file.path(outdir, 'full_history_trend_zeta_correlation.png'), p_full, width = 11, height = 5, dpi = 150)
readme <- c(
  '# Trend-Zeta Correlation Audit',
  '',
  'This bundle summarizes posterior dependence between the reduced-model USGS trend state and transfer zeta state from the retained reduced iter300 seed root.',
  '',
  'Key interpretation:',
  '- Strong persistent negative posterior correlation implies identifiability pressure between these two additive state components.',
  '- This does not prove an implementation bug by itself, but it does show the filter/smoother is repeatedly trading one component off against the other.',
  '',
  'Files:',
  '- trend_zeta_correlation_summary.csv',
  '- trend_zeta_correlation_timeseries.csv',
  '- full_history_trend_zeta_correlation.png',
  '- last2000_trend_zeta_correlation.png',
  '- last1000_trend_zeta_correlation.png',
  '- last500_trend_zeta_correlation.png'
)
writeLines(readme, file.path(outdir, 'README.md'))
