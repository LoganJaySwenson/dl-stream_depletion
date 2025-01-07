# Post-process sensitivity analysis experiment
library(tidyverse)

source("code/Theme+Settings.R")

gauges <- file.path("data", "gauges.csv") |>
  read_csv(show_col_types = F) 

gauge_ids <- gauges$gauge_id

save_dir <- file.path("models", "DL", "outputs")


pumping_fracs <- seq(0, 1.0, 0.1) 
experiments <- paste("sensitivity", "experiment", format(pumping_fracs, nsmall = 1), sep = "_")

res_list <- map(experiments, ~{
  read_csv(file.path(save_dir, paste(.x, "timeseries.csv", sep = "_")),
           show_col_types = F)
})

for (i in seq_along(experiments)){
  
  if (i == 1){
    
    res <- left_join(gauges["gauge_id"], res_list[[i]], by = c("gauge_id")) |> 
      rename(!!paste("baseflow", "sim", pumping_fracs[i], sep = "_") := paste("baseflow", "sim", experiments[i], sep = "_")) |>
      mutate(!!paste("baseflow", "sim", pumping_fracs[i], sep = "_") := if_else(.data[[paste("baseflow", "sim", pumping_fracs[i], sep = "_")]] < 0, 
                                                                                0, 
                                                                                .data[[paste("baseflow", "sim", pumping_fracs[i], sep = "_")]]))
    
  } else{
    res <- left_join(res, res_list[[i]], by = c("gauge_id", "date", "baseflow_obs")) |>
      rename(!!paste("baseflow", "sim", pumping_fracs[i], sep = "_") := paste("baseflow", "sim", experiments[i], sep = "_")) |>
      mutate(!!paste("baseflow", "sim", pumping_fracs[i], sep = "_") := if_else(.data[[paste("baseflow", "sim", pumping_fracs[i], sep = "_")]] < 0, 
                                                                                0, 
                                                                                .data[[paste("baseflow", "sim", pumping_fracs[i], sep = "_")]]))
  }
  
}

rm(experiments, res_list)


experiments <- paste("baseflow", "sim", pumping_fracs, sep = "_")

# for (i in 2:(length(experiments))){
#   
#   print(experiments[i])
#   
# }

for (i in 2:(length(experiments))){
  
  res <- res |>
    mutate(
      !!paste("stream_depletion", pumping_fracs[i], sep = "_") := .data[[experiments[i]]] - baseflow_sim_0,
      !!paste("stream_depletion", pumping_fracs[i], sep = "_") := if_else(.data[[paste("stream_depletion", pumping_fracs[i], sep = "_")]] > 0,
                                                                          0, 
                                                                          .data[[paste("stream_depletion", pumping_fracs[i], sep = "_")]])
    )
}

stream_depletion <- 
  res |>
  select(gauge_id, date, all_of(paste("stream_depletion", pumping_fracs[2:length(pumping_fracs)], sep = "_"))) |>
  pivot_longer(cols = -c(gauge_id, date), values_to = "stream_depletion") |>
  mutate(
    pumping_frac = str_extract(name, "(\\d+\\.\\d+|1)") |> as.numeric(),
    year = year(date),
    season = if_else(month(date) >= 4 & month(date) <= 9, "S", "W")
    ) |>
  group_by(gauge_id, year, season, pumping_frac) |>
  summarise(
    stream_depletion = mean(stream_depletion, na.rm = T)
  ) |>
  ungroup() |>
  group_by(gauge_id, year, pumping_frac) |>
  summarise(
    stream_depletion = mean(stream_depletion, na.rm = T)
  ) |>
  ungroup() |>
  filter(year > 1980) |>
  left_join(file.path("data", "water_use.csv") |> read_csv(show_col_types = F) 
            |> select(gauge_id, year, precip_mm, irrigation, other_water_use, combined_water_use),
            by = c("gauge_id", "year")
            ) |>
  mutate(
    depletion_frac = abs( (stream_depletion * 723.96695) / ((irrigation * 182.5) + (other_water_use * 365.25)) ),
  ) |>
  select(gauge_id, year, precip_mm, irrigation, other_water_use, pumping_frac, stream_depletion, depletion_frac)
            
range(stream_depletion$depletion_frac)


ggplot()+
  geom_boxplot(data = stream_depletion, aes(as.factor(pumping_frac), depletion_frac), fill = "#999999", width = 0.5, outlier.shape = 21, outlier.size = 3)+
  labs(
    x = "Pumping multiplier",
    y = "Annual depletion fraction",
    fill = "Pumping frac"
    )+
  scale_y_continuous(
    breaks = scales::pretty_breaks(n = 4)
  )+
  theme(
    axis.title.x = element_text(size = 12),
    axis.title.y = element_text(size = 12),
  )
ggsave(file.path("figures", "S1.png"), dpi=300, width = 190, height = 90, units = "mm")


library(patchwork)

pp <- list()

for (i in 1:2){
  
  if (i == 1){
    
    gauge.ids = gauges |> filter(area_km < 1e4) |> _$gauge_id
    
    p = 
      ggplot()+
      geom_point(data = stream_depletion |> filter(gauge_id %in% gauge.ids), aes((irrigation  * 1233) + (other_water_use * 1233), depletion_frac, fill = pumping_frac), 
                 color = "#000000", pch = 21, size = 3.5, alpha = 0.6)+
      viridis::scale_fill_viridis(option="magma")+
      labs(
        x = "Annual water use [m\U00B3]",
        y = "Depletion fraction",
        fill = "Pumping frac"
      )+
      scale_x_continuous(
        labels = scales::label_comma()
      )+
      scale_y_continuous(
        labels = scales::label_comma()
      )+
      theme(
        axis.title.x = element_text(size = 12),
        axis.title.y = element_text(size = 12),
        plot.margin = unit(c(5,5,5,5), "mm")
      )
    
  } else{
    
    gauge.ids = gauges |> filter(area_km >= 1e4) |> _$gauge_id
    
    p =
      ggplot()+
      geom_point(data = stream_depletion |> filter(gauge_id %in% gauge.ids), aes((irrigation  * 1233) + (other_water_use * 1233), depletion_frac, fill = pumping_frac), 
                 color = "#000000", pch = 21, size = 3.5, alpha = 0.6)+
      viridis::scale_fill_viridis(option="magma")+
      labs(
        x = "Annual water use [m\U00B3]",
        y = "Depletion fraction",
        fill = "Pumping frac"
      )+
      scale_x_continuous(
        labels = scales::label_comma()
      )+
      scale_y_continuous(
        labels = scales::label_comma()
      )+
      theme(
        axis.title.x = element_text(size = 12),
        axis.title.y = element_text(size = 12),
        plot.margin = unit(c(5,5,5,5), "mm")
      )
    
  }
  
  pp[[i]] <- p
  
}

pp_combined <- wrap_plots(pp, ncol = 2, nrow = 1)+
  plot_layout(axis_titles = "collect", guides = "collect") & theme(legend.position = "bottom")

pp_combined

ggsave(file.path("figures", "S2.png"), dpi=300, width = 220, height = 220/2, units = "mm")




