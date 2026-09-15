options(scipen = 999)

# 1. Input the Data -----------------
# (Case1-Path1, Case1-Path2, Case1-Path3, Case2-Path1, Case2-Path2, Case2-Path3)
count_annotation <- c(340, 287, 279, 256, 262, 109)
count_sortit     <- c(567, 818, 445, 534, 516, 214)

time_anno <- c(1131, 1380, 895, 1012, 1200, 1214)
time_sort <- c(1258, 1800, 861, 1154, 2100, 567)

# 2. Paired T-Test (Parametric) ------------------------------
# We use paired = TRUE because the same evaluators measured both methods.
t_result <- t.test(count_sortit,
                   count_annotation,
                   paired = TRUE,
                   conf.level = 0.95)

# 3. Wilcoxon Signed-Rank Test (Non-Parametric) ---------------------------------------------
# Note: 'conf.int = TRUE' in Wilcoxon gives the "Pseudomedian" (Hodges-Lehmann estimate)
# which is the non-parametric equivalent of the CI for the difference.
wilcox_result <- wilcox.test(
  count_sortit,
  count_annotation,
  paired = TRUE,
  conf.int = TRUE,
  conf.level = 0.95
)

# 4. Quick Summary Table for Comparison -------------------------------------
summary_df <- data.frame(
  Metric = c("Mean/Median Diff", "P-Value", "CI Lower", "CI Upper"),
  T_Test = c(
    mean(count_sortit - count_annotation),
    t_result$p.value,
    t_result$conf.int[1],
    t_result$conf.int[2]
  ),
  Wilcoxon = c(
    wilcox_result$estimate,
    wilcox_result$p.value,
    wilcox_result$conf.int[1],
    wilcox_result$conf.int[2]
  )
)

cat("\n--- COUNT ANALYSIS RESULTS ---\n")
print(summary_df)

#### Statistical Tests for Time ------------
t_time <- t.test(time_sort, time_anno, paired = TRUE)
w_time <- wilcox.test(time_sort, time_anno, paired = TRUE, conf.int = TRUE)

cat("\n--- TIME ANALYSIS RESULTS ---\n")
cat("Paired T-Test P-value:", round(t_time$p.value, 4), "\n")
cat("T-Test 95% CI:",
    round(t_time$conf.int[1], 2),
    "to",
    round(t_time$conf.int[2], 2),
    "\n\n")

cat("Wilcoxon P-value:", round(w_time$p.value, 4), "\n")
cat("Wilcoxon 95% CI:",
    round(w_time$conf.int[1], 2),
    "to",
    round(w_time$conf.int[2], 2),
    "\n")


#### Plotting --------------
library(ggplot2)
library(dplyr)
library(tidyr)

# 1. Prepare the Data Frame
plot_data <- data.frame(
  Case = rep(c("Case 1", "Case 2"), each = 3),
  Evaluator = rep(c("P1", "P2", "P3"), 2),
  Count = c(count_annotation, count_sortit),
  # Assuming long format logic
  Time = c(time_anno, time_sort),
  Method = rep(c("Annotation", "SortIT"), each = 6) # Adjusted for your vector order
)

# Create a combined grouping variable for the 4 bars
# We reorder levels so Case 1 bars stay together and Case 2 bars stay together
plot_data$Group <- factor(
  interaction(plot_data$Method, plot_data$Case),
  levels = c(
    "Annotation.Case 1",
    "SortIT.Case 1",
    "Annotation.Case 2",
    "SortIT.Case 2"
  )
)

# Define a Colorblind Friendly Palette (2 shades of Blue/Purple for C1, 2 shades of Yellow/Green for C2)
# These colors are high-contrast and distinguishable for most types of colorblindness
cb_palette <- c(
  "Annotation.Case 1" = "#F2E3B6",
  "SortIT.Case 1" = "#007DF5",
  "Annotation.Case 2" = "#F59642",
  "SortIT.Case 2" = "#3B5875"
)

# 2. The Plot (Example for Count - Repeat for Time by changing y = Time)
p_count <- ggplot(plot_data, aes(
  x = interaction(Case, Evaluator),
  y = Count,
  fill = Group
)) +
  geom_col(position = position_dodge2(padding = 0), width = 0.7) +
  scale_x_discrete(
    labels = c(
      "Case 1\n(P1)",
      "Case 2\n(P1)",
      "Case 1\n(P2)",
      "Case 2\n(P2)",
      "Case 1\n(P3)",
      "Case 2\n(P3)"
    )
  ) +
  scale_fill_manual(values = cb_palette, name = "Method & Case") +
  guides(fill = guide_legend(nrow = 2, byrow = FALSE)) +
  labs(title = "Patches Generated", y = "Number of Patches", x = "") +
  theme_minimal() +
  theme(legend.position = "bottom", panel.grid.major.x = element_blank())

# 2. Update the Time Pposition_dodge2()# 2. Update the Time Plot with the same legend guide
p_time <- ggplot(plot_data, aes(
  x = interaction(Case, Evaluator),
  y = Time,
  fill = Group
)) +
  geom_col(position = position_dodge2(padding = 0), width = 0.7) +
  scale_x_discrete(
    labels = c(
      "Case 1\n(P1)",
      "Case 2\n(P1)",
      "Case 1\n(P2)",
      "Case 2\n(P2)",
      "Case 1\n(P3)",
      "Case 2\n(P3)"
    )
  ) +
  scale_fill_manual(values = cb_palette, name = "Method & Case") +
  guides(fill = guide_legend(nrow = 2, byrow = FALSE)) +
  labs(title = "Time Spent", y = "Seconds", x = "Case (Evaluator)") +
  theme_minimal() +
  theme(legend.position = "bottom", panel.grid.major.x = element_blank())

# 3. Combine with ggpubr
# Note: common.legend = TRUE will pick up the 'nrow = 2' guide from the plots
combined_plot <- ggpubr::ggarrange(
  p_count,
  p_time,
  labels = c("A", "B"),
  ncol = 1,
  nrow = 2,
  common.legend = TRUE,
  legend = "bottom",
  font.label = list(
    size = 14,
    face = "bold",
    color = "black"
  )
)

print(combined_plot)

ggsave(
  "Figure_4.png",
  combined_plot,
  dpi = 320,
  height = 6,
  width = 7,
  units = "in"
)
