require(dplyr)
require(magrittr)
require(tidyverse)
require(extrafont)
loadfonts(device = "win")

f <- partial(factor,
             levels = c("<50%", "50-59%", "60-69%", "70-79%", "80-89%", "90-99%", "100%"),
             ordered=TRUE,
             )

survey <- read.csv(
  "survey_data.csv",
  stringsAsFactors = T,
  col.names = c(
    "CommonDisease",
    "CommonNeoplasms",
    "CommonNeoplastic",
    "DetCommNeoplas",
    "SubtNonNeoplastic",
    "MvBrareNeoplast",
    "SubtypeRareNeoplastic",
    "DxRareNonNeoplastic"
  )
) %>% modify(f)


data <- survey %>%
  modify(f) %>%
  pivot_longer(cols = colnames(survey)) %>%
  group_by(name, value)

n <- count(data) %>%
  filter(value == "<50%")

ggplot(data, aes(
  y = factor(
    name,
    levels = c(
      "CommonDisease",
      "CommonNeoplasms",
      "CommonNeoplastic",
      "DetCommNeoplas",
      "SubtNonNeoplastic",
      "MvBrareNeoplast",
      "SubtypeRareNeoplastic",
      "DxRareNonNeoplastic"
    ),
    labels = c(
      "Common disease, neoplastic vs. non-neoplastic",
      "Common neoplastic, malignant vs. benign",
      "Common neoplastic, broad subtyping",
      "Common neoplastic, detailed subtyping",
      "Common non-neoplastic, broad subtyping",
      "Rare neoplastic, malignant vs. benign",
      "Rare neoplastic, subtyping",
      "Rare non-neoplastic, diagnosis"
    )
  ),
  fill = fct_rev(value)
)) +
  geom_bar(position = "fill", width = 0.8) +
  scale_x_continuous(breaks = seq(0, 1, by = 0.1), expand = c(0, 0)) +
  coord_cartesian(xlim = c(1, 0)) +
  scale_y_discrete(limits = rev, expand = c(0, 0)) +
  paletteer::scale_fill_paletteer_d("rcartocolor::Temps") +
  guides(fill = guide_legend(nrow = 1, reverse = TRUE)) +
  theme_minimal() +
  theme(
    legend.position = "bottom",
    legend.location = "plot",
    legend.title = element_blank(),
    legend.text = element_text(family = "Arial Narrow", size = 10),
    axis.ticks = element_blank(),
    axis.text.x.bottom = element_blank(),
    axis.text.y = element_text(
      hjust = 0,
      family = "Arial Narrow",
      face = "bold",
      size = 12
    ),
    axis.title = element_blank(),
    panel.spacing = element_blank(),
    panel.ontop = T,
    panel.grid.major.x = element_line(color = scales::alpha("black", 0.25)),
    panel.grid.minor = element_blank(),
    panel.grid.major.y = element_blank(),
    panel.border = element_rect(color = "grey30"),
    axis.line = element_line(color = "grey30"),
  )
ggsave(
  "fig1_v2.png",
  dpi = 320,
  units = "in",
  width = 7.5,
  height = 3
)

### 95% CI for survey results
prop.test(sum(survey$CommonNeoplasms > "70-79%"), 81)
prop.test(sum(survey$MvBrareNeoplast > "70-79%"), 81)

