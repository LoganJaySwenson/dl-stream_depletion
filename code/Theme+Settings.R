#Publication theme
theme_LJS <- function(...){
  theme_bw(base_size=10)+ 
    theme(
      text=element_text(color='black'),
      #plot.title=element_text(face="bold", size=rel(1)),
      #axis.title=element_text(face="bold", size=rel(1)),
      axis.text=element_text(size=rel(1)),
      strip.text=element_text(size=rel(1)),
      legend.title=element_text(size=rel(1)),
      legend.text=element_text(size=rel(0.9)),
      legend.position = 'right',
      panel.grid=element_blank(),
      panel.grid.major = element_blank(),
      panel.grid.minor = element_blank(),
      plot.margin=unit(c(1,1,1,1), "mm"),
      strip.background=element_blank())
}
theme_set(theme_LJS())