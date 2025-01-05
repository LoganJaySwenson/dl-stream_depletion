# 03. Get streamflow and estimated baseflow using Eckhardt method for watersheds
library(tidyverse)

gauges <- file.path("data", "gauges.csv") |>
  read_csv(show_col_types = F) 

# Get flows
gauge_ids <- gauges$gauge_id
flows <- tibble()

for (i in seq_along(gauge_ids)) {
  flows <- bind_rows(flows,
                    as_tibble(dataRetrieval::readNWISdv(siteNumber = gauge_ids[i], 
                                                        parameterCd = "00060", 
                                                        startDate = "1979-10-01")) |>
                      dataRetrieval::renameNWISColumns() |>
                      rename_with(.cols = everything(), tolower) |>
                      rename(gauge_id = site_no)
  )
}

flows <- flows |>
  left_join(gauges |> select(gauge_id, area_km), by = c("gauge_id")) |>
  mutate(
    flow_cfs = flow,
    flow_cfd = flow_cfs * 86400 
  ) |>
  # mutate(
  #   flow_m3s = flow * 0.0283, # ft3/s --> m3/s 
  #   flow_m3d = flow_m3s * 86400,
  #   flow_mmd = (flow_m3d * 1e9) / (area_km * 1e12)
  # ) |>
  mutate_if(is.numeric, round, digits=2) |>
  select(gauge_id, date, flow_cfs, flow_cfd)
  #select(gauge_id, date, flow_m3s, flow_m3d, flow_mmd)



# Estimate baseflow using Eckhardt (2005) baseflow separation algorithm
# Code modified from https://github.com/samzipper 

baseflow_separation <- function(Q, BFImax, k){
  # Eckhardt (2005) baseflow separation method 
  #
  # Inputs:
  #   Q = discharge timeseries (no missing data; any units are OK)
  #   BFImax = maximum allowed value of baseflow index
  #   k = recession constant; this can be estimated with the function estimate_recession_constant.
  #       
  # Output:
  #   bf = baseflow timeseries, same length and units as Q
  
  # empty output vector
  bf <- rep(NaN, length(Q))
  
  # fill in initial value
  bf[1] <- Q[1]*BFImax*0.9  # from Barlow 'Digital Filters' document
  
  # scroll through remaining values
  for (i in 2:length(Q)){
    # calculate bf using digital filter
    bf[i] <- (((1-BFImax)*k*bf[i-1]) + ((1-k)*BFImax*Q[i]))/(1-k*BFImax)
    
    # make sure 0 <= bf <= Q
    if (bf[i]<0)    bf[i] <- Q[i]*BFImax*0.9  # from Barlow 'Digital Filters' document
    if (bf[i]>Q[i]) bf[i] <- Q[i]
  }
  
  return(bf)
  
}

estimate_recession_constant <- function(Q, UB_prc=0.95, method="Brutsaert", min_pairs=50){
  # Estimate baseflow recession constant
  #
  # Inputs:
  #   Q = discharge timeseries (no missing data; any units are OK)
  #   UB_prc = percentile to use for upper bound of regression
  #   method = method to use to calculate recession coefficient
  #     "Langbein" = Langbein (1938) as described in Eckhardt (2008)
  #     "Brutsaert" = Brutsaert (2008) WRR
  #   min_pairs = minimum number of date pairs retained after filtering out 
  #     quickflow events; 50 is from van Dijk (2010) HESS
  #       
  # Output:
  #   k = recession constant
  
  require(quantreg)  # quantile regression
  
  if (method=="Langbein"){
    # calculate difference
    dQ_dt = c(NaN, diff(Q))
    
    # find days of five consecutive negative values
    which_negative <- which(dQ_dt < 0 & Q > 0)
    which_positive <- which(dQ_dt >= 0)
    which_positive_with_buffer <- unique(c(which_positive-2, which_positive-1,
                                           which_positive, 
                                           which_positive+1, which_positive+2))  # 2 days before and 2 days after a positive or 0 value
    which_positive_with_buffer <- which_positive_with_buffer[which_positive_with_buffer > 0]  # get rid of negative indices
    which_keep <- which_negative[!(which_negative %in% which_positive_with_buffer)]  # get rid of points within buffer around flow increases
    which_keep <- which_keep[(which_keep-1) %in% which_keep]  # trim to dates with both the current and previous day retained
    
    # any data exist to fit?
    if (length(which_keep) >= min_pairs){
      
      # fit regression
      fit.qr <- rq(Q[which_keep] ~ 0+Q[which_keep-1], tau=UB_prc)  # force intercept to go through origin
      
      # extract constant
      k <- as.numeric(coef(fit.qr)[1])
      
    } else {
      k <- NaN
    }
    return(k)
  }
  
  if (method=="Brutsaert"){
    # calculate lagged difference (dQ/dt) based on before/after point
    dQ_dt <- c(NaN, diff(Q, lag=2)/2, NaN)
    dQ_dt_left <- c(NaN, diff(Q))
    
    # screen data for which dQ_dt to calculate recession, based on rules in Brutsaert (2008) WRR Section 3.2
    which_negative <- which(dQ_dt < 0 & dQ_dt_left < 0 & Q > 0)
    which_positive <- which(dQ_dt >= 0)
    which_positive_with_buffer <- unique(c(which_positive-2, which_positive-1, which_positive,
                                           which_positive+1, which_positive+2, which_positive+3))  # 2 days before and 3 days after a positive or 0 value
    which_positive_with_buffer <- which_positive_with_buffer[which_positive_with_buffer > 0]  # get rid of negative indices; possible because of 2 days before
    which_keep <- which_negative[!(which_negative %in% which_positive_with_buffer)]  # get rid of points within buffer around flow increases
    which_keep <- which_keep[(which_keep-1) %in% which_keep]  # trim to dates with both the current and previous day retained
    
    # any data exist to fit?
    if (length(which_keep) >= min_pairs){
      
      # fit regression
      fit.qr <- rq(Q[which_keep] ~ 0+Q[which_keep-1], tau=UB_prc)  # force intercept to go through origin
      
      # extract constant
      k <- as.numeric(coef(fit.qr)[1])
      
    } else {
      k <- NaN
    }
    return(k)
  }
  
  
}

estimate_BFImax_parameter <- function(Q, k){
  # Estimate BFImax parameter for Eckhardt baseflow separation filter using a backwards-looking filter, based on Collischonn & Fan (2013)
  #
  # Inputs:
  #   Q = discharge timeseries (no missing data) (any units are OK)
  #   k = recession constant; this can be estimated with the function estimate_recession_constant.
  #
  # Outputs:
  #   BFImax = maximum allowed value of baseflow index; Eckhardt estimates values of:
  #      0.8 for perennial stream with porous aquifer
  #      0.5 for ephemeral stream with porous aquifer
  #      0.25 for perennial stream with hardrock aquifer
  
  # start from end of timeseries
  bf <- rep(NaN, length(Q))
  bf[length(Q)] <- Q[length(Q)]
  for (i in (length(Q)-1):1){
    if (bf[i+1]==0){
      bf[i] <- Q[i]
    } else {
      bf[i] <- bf[i+1]/k
    }
    
    # make sure bf isn't > Q
    if (bf[i]>Q[i]) bf[i] <- Q[i]
  }
  
  BFImax <- sum(bf)/sum(Q)
  return(BFImax)
  
}

baseflows <- tibble()
parameters <- tibble()

for (i in seq_along(gauge_ids)){
  
  Q <- filter(flows, gauge_id == gauge_ids[i])
  
  if (sum(is.na(Q$flow_cfs)) != 0){
    print("Q cannot contain missing values.")
  } else {
    
    k <- estimate_recession_constant(Q$flow_cfs, method = "Langbein")
    BFImax <- estimate_BFImax_parameter(Q$flow_cfs, k = k)
    Q$baseflow_cfs <- round(baseflow_separation(Q$flow_cfs, BFImax = BFImax, k = k), digits = 2)
    
    parameters <- bind_rows(parameters, 
                            tibble(gauge_id = gauge_ids[i],
                                   k = k, 
                                   BFImax = BFImax)
                            )
    
  }
  
  baseflows <- bind_rows(baseflows, Q)
  
}

baseflows <- filter(baseflows, date >= as.Date("1979-10-01") & date <= as.Date("2024-09-30")) 

baseflows <- baseflows |>
  rename(
    baseflow = baseflow_cfs
  )

write_csv(baseflows, file.path("data", "flow.csv"))

