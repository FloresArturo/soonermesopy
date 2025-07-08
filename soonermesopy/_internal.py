# ---------------
# Utility tools for internal use
# author: Arturo J. Flores (artuflo@okstate.edu)
# date : 08Jul2025
# ---------------

# Libraries
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import numpy as np


# Functions

# soil-water calculations
def _calculate_matric_potential(delta_T: float) -> float:
    """
    Calculates matric potential from delta T value.
    Ref: Zhang et al, 2019; Illston et al, 2007. [Eq. 5]

    Parameters
    ----------
    delta_T : float
        Calibrated Delta-T [°C].

    Returns
    -------
    float
        Matric potential
    """
    if not isinstance(delta_T, (int, float)):
        return None
    
    mp = -2083 / (1 + np.exp(-3.35 * (delta_T - 3.17)))
    return mp

def _calculate_vwc_from_MP(matric_p: float, theta_r: float, theta_s: float, alpha: float, n: float) -> float:
    """
    Calculates VWC from MP using hydraulic parameters.
    Ref: Ref: Zhang et al, 2019; Illston et al, 2007.

    Parameters
    ----------
    matric_p    : float [kPa]
    theta_r     : float [0-1]
    theta_s     : float [0-1]
    alpha       : float 
    n           : float

    Returns
    -------
    float
        Volumetric Water Content [cm3 cm-3]
    """
    if all(isinstance(x, (int, float)) for x in [matric_p, theta_r, theta_s, alpha, n]):
        vwc = theta_r + (theta_s - theta_r) / (1 + (-alpha * matric_p)**n)**(1 - 1/n)
        return vwc
    else:
        return np.nan

def _calculate_faw(theta: float, theta_wp: float, theta_fc: float) -> float:
    """
    Calculates Fraction of Available Water.
    FAW = (theta - theta_WP) / (theta_FC - theta_WP)

    Parameters
    ----------
    theta   : float
        Actual water content [cm3/cm3]
    theta_wp: float
        Water content at wilting point [cm3/cm3]
    theta_fc: float
        Water content at field capacity [cm3/cm3]
    
    Returns
    ------- 
    float
        Fraction of available water [cm3/cm3]
    """
    if all(isinstance(x, float) for x in [theta, theta_wp, theta_fc]):
        try:
            faw = (theta - theta_wp) / (theta_fc - theta_wp)
            return faw
        except:
            return np.nan
    else:
        return np.nan

def _calculate_whc(theta_wp: float, theta_fc: float) -> float:
    """
    Calculates Water Holding Capacity.
    WHC = theta_FC - theta_WP

    Parameters
    ----------
    theta_wp    : float
        Water content at wilting point [cm3/cm3]
    theta_fc    : float
        Water content at field capacity [cm3/cm3]
    
    Returns
    -------
    float
        Water holding capacity [cm3/cm3]
    """
    if all(isinstance(x, float) for x in [theta_wp, theta_fc]):
        try:
            whc = theta_fc - theta_wp
            return whc
        except:
            return np.nan
    else:
        return np.nan



# functionality

def _verify_date(date: datetime) -> bool:
    """
    Verifies date is valid type and logical for Mesonet data retrieval.
    - Be no later than current date and time.
    - Be no earlier than 1994.
    
    Parameters
    ----------
    date : datetime
    
    Returns
    -------
    bool
        True if date is valid, False otherwise.
    """
    if not isinstance(date, datetime):
        return False
    
    if date > datetime.now() or date.year < 1994:
        return False
    
    return True

def _verify_station(station_id: str) -> bool:
    """
    Verifies given station exists.

    Parameters
    ----------
    station_id : str
        4 letter station identifier.

    Returns
    -------
    bool
        True if station exists, False otherwise.

    Raise
    -----
    ImportError
        If an error occurs while loading reference information. Usually due to connection problems.
    """
    if not isinstance(station_id, str) or len(station_id) != 4:
        return False
    
    station_id = station_id.upper()
    try:
        ref = pd.read_csv("https://api.mesonet.org/index.php/export/station_location_soil_information")
        valid_stations = ref.stid.to_list()
        return station_id in valid_stations
    except Exception as e:
        raise ImportError(f'Error loading reference information! Check connection.\nDetails: {e}')
    
    return False

def _retrieve_hydraulic_params(station_id: Optional[str]=None, depth: Optional[int]=None):
    """
    Retrieves hydraulic parameters required to compute VWC from MP.
    Ref: Zhang et al, 2019; Illston et al, 2007. [Eq. 5]
    """
    # Load MesoSoil database
    try:
        mesoinfo = pd.read_excel('files/MesoSoilv2_1.xlsx', na_values="-9.9")
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

def _retrieve_soil_moisture_data(date: Optional[datetime]=None, station_id: Optional[str]=None) -> pd.DataFrame:
    """
    Retrieves soil moisture for a single or all stations.
    Default: yesterday, all stations.

    Parameters
    ----------
    date    : datetime
        Date of interest.
    station_id  : str
        4 letter station ID (optional, by default all stations are included)

    Returns
    -------
    pd.DataFrame
        DF including soil moisture data.

    Raises
    ------
    ValueError
        If any of the inputs is not valid.
    ImportError
        When an error occurrs retrieving the data.
    """
    
    # --- Verify date ---
    if date is None:
        date = datetime.now()-timedelta(days=1)
    if not _verify_date(date):
        raise ValueError('Invalid date!')
    
    # --- Generate URL ---
    base_url = 'https://data.mesonet.org/data/public/mesonet/mdf'                # ending = YYYY/mm/dd/YYYYmmddHHMM.mdf
    y = date.strftime("%Y")
    m = date.strftime("%m")
    d = date.strftime("%d")
    url = f'{base_url}/{y}/{m}/{d}/{y}{m}{d}0000.mdf'

    # --- Make request and retrieve data ---
    try:
        data = pd.read_csv(url, skiprows=2, skipinitialspace=True, sep=" ",
                           na_values=['-999','-998','-997','-996','-995','-994'])
        data = data[['STID','TR05','TR25','TR60']]
        data.columns = ['Site', 5, 25, 60]          # available depths
    
    except Exception as e:
        raise ImportError(f'Error retrieving data!\nDetails: {e}')
    
    # --- Calculate VWC from deltaT
    hyparams = _retrieve_hydraulic_params()      # hydraulic parameters used for calibration
    stations_data = data.melt(id_vars='Site', var_name='Depth', value_name='Delta_T').merge(hyparams, on=['Site', 'Depth'])

    # compute MP, VWC, WHC, and FAW
    stations_data['MP'] = stations_data.apply(
        lambda row: _calculate_matric_potential(row['Delta_T']),
        axis=1)

    stations_data['VWC'] = stations_data.apply(
        lambda row: _calculate_vwc_from_MP(row['MP'], row['Theta_r'], row['Theta_s'], row['Alpha'], row['N']),
        axis=1)

    stations_data['FAW'] = stations_data.apply(
        lambda row: _calculate_faw(row['VWC'], row['Th1500'], row['Th33']),
        axis=1)
    
    stations_data['WHC'] = stations_data.apply(
        lambda row: _calculate_whc(row['Th1500'], row['Th33']),
        axis=1)

    # clean DF
    clean_data = stations_data[['Site', 'Depth', 'Th33', 'Th1500', 'Ks', 'MP', 'VWC', 'FAW', 'WHC']]
    fc_data = clean_data.pivot(index='Site', columns='Depth', values='Th33').reset_index()
    fc_data.columns = ['Site', 'FC05', 'FC25', 'FC60']
    wp_data = clean_data.pivot(index='Site', columns='Depth', values='Th1500').reset_index()
    wp_data.columns = ['Site', 'WP05', 'WP25', 'WP60']
    ks_data = clean_data.pivot(index='Site', columns='Depth', values='Ks').reset_index()
    ks_data.columns = ['Site', 'Ks05', 'Ks25', 'Ks60']
    mp_data = clean_data.pivot(index='Site', columns='Depth', values='MP').reset_index()
    mp_data.columns = ['Site', 'MP05', 'MP25', 'MP60']
    vwc_data = clean_data.pivot(index='Site', columns='Depth', values='VWC').reset_index()
    vwc_data.columns = ['Site', 'VWC05', 'VWC25', 'VWC60']
    faw_data = clean_data.pivot(index='Site', columns='Depth', values='FAW').reset_index()
    faw_data.columns = ['Site', 'FAW05', 'FAW25', 'FAW60']
    whc_data = clean_data.pivot(index='Site', columns='Depth', values='WHC').reset_index()
    whc_data.columns = ['Site', 'WHC05', 'WHC25', 'WHC60']
    moist_data = fc_data.merge(wp_data, on='Site').merge(whc_data, on='Site').merge(vwc_data, on='Site').merge(faw_data, on='Site').merge(mp_data, on='Site').merge(ks_data, on='Site')

    # --- Filter station if given ---
    if station_id is None:
        return moist_data
    elif station_id.upper() in moist_data['Site'].values.tolist():
        return moist_data[moist_data.Site==station_id]
    else:
        raise ValueError('Station ID not valid!')

def _retrieve_soil_temperature_data(date: Optional[datetime]=None, station_id: Optional[str]=None) -> pd.DataFrame:
    """
    Retrieves soil temperature for all or a single station.
    Default: yesterday, all stations.

    Parameters
    ----------
    date    : datetime
        Date of interest.
    station_id  : str
        4 letter station ID (optional, by default all stations are included)

    Returns
    -------
    pd.DataFrame
        DF including soil temperature data.

    Raises
    ------
    ValueError
        If any of the inputs is not valid.
    ImportError
        When an error occurrs retrieving the data.
    """
    # --- Verify date ---
    if date is None:
        date = datetime.now()-timedelta(days=1)
    if not _verify_date(date):
        raise ValueError('Invalid date!')
    
    # --- Generate URL ---
    base_url = 'https://data.mesonet.org/data/public/mesonet/summaries/daily/mdf'    # ending = YYYY/mm/YYYYmmdd.daily.mdf
    y = date.strftime("%Y")
    m = date.strftime("%m")
    d = date.strftime("%d")
    url = f'{base_url}/{y}/{m}/{y}{m}{d}.daily.mdf'

    # --- Make request and retrieve data ---
    try:
        data = pd.read_csv(url, skiprows=2, skipinitialspace=True, sep=" ",
                           na_values=['-999','-998','-997','-996','-995','-994'])
        data = data[['STID', 'BMIN', 'BMAX', 'SMAX', 'SMIN','S5MN', 'S5MX']]                                                 # columns to keep
    
    except Exception as e:
        raise ImportError(f'Error retrieving data!\nDetails: {e}')
    
    # --- Filter station if given ---
    if station_id is None:
        return data.rename(columns={'STID':'Site'})
    elif _verify_station(station_id):
        return data[data['STID']==station_id].rename(columns={'STID':'Site'})
    else:
        raise ValueError('Station ID not valid!')
    
def _retrieve_weather_data(date: Optional[datetime]=None, station_id: Optional[str]=None) -> pd.DataFrame:
    """
    Retrieves weather data for all or a single station.
    Default: yesterday, all stations.

    Parameters
    ----------
    date    : datetime
        Date of interest.
    station_id  : str
        4 letter station ID (optional, by default all stations are included)

    Returns
    -------
    pd.DataFrame
        DF including climatic data. 

    Raises
    ------
    ValueError
        If any of the inputs is not valid.
    ImportError
        When an error occurrs retrieving the data. 
    """
    # --- Verify date ---
    if date is None:
        date = datetime.now()-timedelta(days=1)
    if not _verify_date(date):
        raise ValueError('Invalid date!')
    
    # --- Generate URL ---
    base_url = 'https://data.mesonet.org/data/public/mesonet/summaries/daily/mdf'    # ending = YYYY/mm/YYYYmmdd.daily.mdf
    y = date.strftime("%Y")
    m = date.strftime("%m")
    d = date.strftime("%d")
    url = f'{base_url}/{y}/{m}/{y}{m}{d}.daily.mdf'
    
    # --- Make request and retrieve data ---
    try:
        data = pd.read_csv(url, skiprows=2, skipinitialspace=True, sep=" ",
                           na_values=['-999','-998','-997','-996','-995','-994'])
        data = data[['STID','TMAX','TMIN','TAVG','HMAX','HMIN','HAVG','RAIN','ATOT','WSPD']]                                                 # columns to keep
    
    except Exception as e:
        raise ImportError(f'Error retrieving data!\nDetails: {e}')
    
    # --- Filter station if given ---
    if station_id is None:
        return data.rename(columns={'STID':'Site'})
    elif _verify_station(station_id):
        return data[data['STID']==station_id].rename(columns={'STID':'Site'})
    else:
        raise ValueError('Station ID not valid!')

