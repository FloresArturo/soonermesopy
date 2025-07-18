# ---------------
# Mesonet data download tools
# author: Arturo J. Flores (artuflo@okstate.edu)
# date : 08Jul2025
# ---------------

# Libraries
from typing import Optional
from datetime import datetime, timedelta
import pandas as pd
import calendar
from tqdm import tqdm
import time

from ._internal import (
    _verify_date,
    _retrieve_soil_moisture_data,
    _retrieve_soil_temperature_data,
    _retrieve_weather_data
)

from ._mesosoil_v2_1 import data as mesosoil_data


# Functions
def generate_date(year: int, month: int, day: Optional[int]=None, hour: Optional[int]=None, minute: Optional[int]=None) -> datetime:
    """
    Generate a datetime object from given inputs.
    
    Parameters
    ----------
    year, month : int
        Mandatory
    day         : int
        Optional. Set to first day of the month if not given. 
    hour, minute : int
        Optional. If not given, 0 is used as default.
    Returns
    -------
    datetime
        Datetime object required in the API retrieval functions.

    Raise
    -----
    TypeError
        If any of the given inputs is not an integer.
    ValueError
        If any of the given inputs is not a valid date.
    """
    if day is None:
        day = 1
    if hour is None:
        hour = 0
    if minute is None:
        minute = 0

    if all([isinstance(x, int) for x in [year, month, day, hour, minute]]):
        try:
            return datetime(year, month, day, hour, minute)
        except Exception as e:
            raise ValueError(f'Input not valid!\nError received: {e}')
    else:
        raise TypeError('Input type not valid!')

def retrieve_geoinfo(station_id: Optional[str]=None, default: Optional[bool]=True) -> pd.DataFrame:
    """
    Retrieves geographical information for Mesonet stations.

    Parameters
    ----------
    station_id  : str
        4 letter station identifier. If no ID is given, all stations are included.
    default     : bool (default=True)
        - True    = nlat, elon, elev, City, County, textures
        - False   = all variables

    Raise
    -----
    ImportError
        If an error occurs when loading geoinfo. Usually due to connection problems.
    ValueError
        If station is given but not existant.
    """
    try:
        geoinfo = pd.read_csv("https://api.mesonet.org/index.php/export/station_location_soil_information")
        geoinfo = geoinfo.rename(columns={'stnm':'Number', 'stid':'Site', 'name':'Name',
                                          'city':'City', 'cnty':'County',
                                          'nlat':'nLat', 'elon':'eLon', 'elev':'Elev',
                                          'cdiv':'Division',
                                          'rang':'Range', 'cdir':'Direction', 'clas':'Class',
                                          'datc':'Commission', 'datd':'Decommission'})
    except Exception as e:
        raise ImportError(f'Error loading geoinfo! Check connection.\nDetails: {e}')
    
    if default:
        keep = ['Number', 'Site', 'Name', 'City', 'County', 'nLat', 'eLon', 'Elev', 'TEXT5', 'TEXT10', 'TEXT25', 'TEXT60', 'TEXT75', 'Commission', 'Decommission']
        geoinfo = geoinfo[keep]
    
    if station_id:
        station_id = station_id.upper()
        if station_id not in geoinfo['Site'].values:
            raise ValueError('Station not valid!')
        return geoinfo[geoinfo['Site'] == station_id]
    
    return geoinfo

def retrieve_hydraulic_params(station_id: Optional[str]=None, depth: Optional[int]=None):
    """
    Retrieves hydraulic parameters required to compute VWC from MP.
    Ref: Zhang et al, 2019; Illston et al, 2007. [Eq. 5]
    """
    # Load MesoSoil database
    try:
        mesoinfo = pd.DataFrame(mesosoil_data)
        mesoinfo = mesoinfo[['Site', 'Depth', 'Sand', 'Silt', 'Clay', 'BulkD',
                             'Th33', 'Th1500', 'Theta_r', 'Theta_s', 'Alpha', 'N', 'Ks']]
    except Exception as e:
        raise ImportError(f'Error loading database!\nDetails: {e}')

    # No station given
    if station_id is None:
        # Depth given and valid
        if depth in mesoinfo['Depth'].values:
            return mesoinfo[mesoinfo['Depth'] ==  depth]
        # No depth given or invalid depth
        else:
            return mesoinfo
    
    # Station given and valid
    elif station_id.upper() in mesoinfo['Site'].values:
        # filter for station only
        station_mesoinfo = mesoinfo[mesoinfo['Site'] == station_id.upper()]
        
        # depth given and valid
        if depth in station_mesoinfo['Depth'].values:
            return station_mesoinfo[station_mesoinfo['Depth'] == depth]
        # no depth given or invalid depth
        else:
            return station_mesoinfo
        
    # Invalid station given
    else:
        raise ValueError('Invalid inputs')

def retrieve_daily_summary(station_id: Optional[str]=None, date: Optional[datetime]=None, variables: Optional[str]=None) -> pd.DataFrame:
    """
    Retrieves a daily summary for a given date and station.

    Parameters
    ----------
    station_id  : str (default=None)
        4 letter station identifier. If no ID is given, all stations are included.
    date        : datetime (default=yesterday)
        Date for which to retrieve data. If no date is given, yesterday's summary is retrieved.
    variables   : str (default='all')
        Variables to include in the download. Options:
        - 'weather'         = temperature, humidity, precipitation, radiation, wind speed
        - 'soil_moist'      = FC, WP, WHC, VWC, FAW, MP and Ks at 05, 25, and 60
        - 'soil_temp'       = temperatures under bare soil and native vegetation
        - 'all'             = all available variables
    
    Returns
    -------
    pd.DataFrame
        Requested data with stations as rows and variables and columns
        
    Raise
    -----
    ImportError
        If an error occurs when retrieving data.
    ValueError
        If a given input is not valid.
    """
    # --- Verify ---
    if date is None:
        date = datetime.now() - timedelta(days=1)
    if not _verify_date(date):
        raise ValueError('Date is not valid!')


    # --- Depending on desired variables retrieve data ---
    if variables == 'weather':
        try:
            data = _retrieve_weather_data(date)
        except Exception as e:
            raise ImportError(f'Error retrieving data!\nDetails: {e}')

    elif variables == 'soil_moist':
        try:
            data = _retrieve_soil_moisture_data(date)
        except Exception as e:
            raise ImportError(f'Error retrieving data!\nDetails: {e}')
        
    elif variables == 'soil_temp':
        try:
            data = _retrieve_soil_temperature_data(date)
        except Exception as e:
            raise ImportError(f'Error retrieving data!\nDetails: {e}')

    elif variables is None or variables == 'all':
        try:
            soil_moist = _retrieve_soil_moisture_data(date)
            soil_temp = _retrieve_soil_temperature_data(date)
            weather = _retrieve_weather_data(date)
            data = weather.merge(soil_moist, on='Site').merge(soil_temp, on='Site')
        except Exception as e:
            raise ImportError(f'Error retrieving data!\nDetails: {e}')
        
    else:
        raise ValueError('Invalid variables selected!')
    
    # --- Filter for station if given ---
    data.insert(1, 'Date', date.date())
    if station_id is not None and station_id.upper() in data.Site.values:
        return data[data['Site']==station_id.upper()]
    else:
        return data

def retrieve_monthly_summary(station_id: Optional[str]=None, month: Optional[int]=None, year: Optional[int]=None, variables: Optional[str]=None) -> pd.DataFrame: # type: ignore
    """
    Retrieves a monthly summary for a specific or all Mesonet stations.

    Parameters
    ----------
    station_id  : str
        4 letter station identifier.
    month, year : int
        Default current month up until yesterday.
    variables   : str
        Variables to include in the download. Options:
        - 'weather'         = temperature, humidity, precipitation, radiation, wind speed
        - 'soil_moist'   = matric potential, vwc and faw at 5, 25, 60cm depths
        - 'soil_temp'       = temperatures under bare soil and native vegetation
        - 'all'             = all variables
    
    Returns
    -------
    pd.DataFrame
        Contains requested data with daily values as rows and variables as columns.

    Raise
    -----
    ValueError
        If a given value is not valid.
    ImportError
        If an error occurs while retrieving data. Usually due to connection problems.
    """
    # --- Verify ---
    if year is None:
        year = datetime.now().year
    if month is None:
        month = datetime.now().month
    if not all(isinstance(x, int) for x in [year, month]):
        raise ValueError('Invalid date!')
    try:
        date = datetime(year, month, 1)
    except Exception as e:
        raise ValueError(f'Invalid date given!\nDetails: {e}')
    
    # --- Create sequence of dates for data retrieval ---
    num_days = calendar.monthrange(date.year, date.month)[1]
    limit_date = datetime.now()-timedelta(days=1)
    dates = [
        date+timedelta(days=i) 
        for i in range(num_days) 
        if (date+timedelta(days=i) <= limit_date)
    ]
    
    # --- Retrieve data depending on variables input ---
    interval_time = 1   # 1 request per second
    if variables in [None, 'all', 'soil_moist', 'soil_temp', 'weather']:
        try:
            retrieved_data = pd.DataFrame()
            for d in tqdm(dates, f'Retrieving {month}/{year} ... '):
                start_time = time.time()        # initial time

                data = retrieve_daily_summary(date=d, variables=variables)
                retrieved_data = pd.concat([retrieved_data, data])

                elapsed_time = time.time()-start_time
                if elapsed_time < interval_time:
                    time.sleep(interval_time - elapsed_time)
        
        except Exception as e:
            raise ImportError(f'Error retrieving data!\nDetails: {e}')
    else:
        raise ValueError('Invalid variables selected!')
    
    # --- Filter for station if given ---
    if station_id is not None and station_id.upper() in retrieved_data.Site.values:
        return retrieved_data[retrieved_data.Site==station_id.upper()]
    else:
        return retrieved_data
