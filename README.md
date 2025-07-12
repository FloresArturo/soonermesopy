# soonermesopy
Tools to download data from the Oklahoma Mesonet. The downloaded data are in the original units reported by Mesonet. The Pandas library (https://pandas.pydata.org/) is used to download, store, and manipulate the data. Visit the *Tutorial soonermesopy.ipynb* for some examples of how to utilize this library.

Before downloading any data, please visit https://www.mesonet.org/about/terms-of-use and make sure you comply with the terms of use.

## Quickstart
This library contains the following functions:

- **generate_date**(year, month, day, hour, minute)

Generates a ```datetime``` object required when retrieving daily data.

- **retrieve_geoinfo**(station_id, default)

Retrieves geographical information for a given station or if not indicated, for all available. If default set to false, all variables from the geoinfo database are included.

- **retrieve_hydraulic_params**(station_id, depth)

Retrieves the soil hydraulic parameters that are required to compute Volumetric Water Content from Matric Potential. These data may be used for other purposes as well. By default, all stations are included unless otherwise specified. The depths include 5, 25, and 60 cm.

- **retrieve_daily_summary**(station_id, date, variables)

Retrieves a daily summary for a single station (4 letter identifier required) or for all available. If no date is given, by default yesterday's data is downloaded. For the available variables see below.

- **retrieve_monthly_summary**(station_id, month, year, variables)

Retrieves a monthly summary for a single station (4 letter identifier required) or for all available. If no month or year is given, by default data for the current month up until yesterday is downloaded. For the available variables see below.

### variables
The available set of variables to be included in the download are:
- 'weather'        = temperature, humidity, precipitation, radiation, wind speed
- 'soil_moist'     = matric potential, vwc and faw at 5, 25, 60cm depths
- 'soil_temp'      = temperatures under bare soil and native vegetation
- 'all'            = all variables from above.
