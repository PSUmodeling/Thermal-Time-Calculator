#!/usr/bin/env python3

import argparse
import numpy as np
import os
import pandas
import sys

T_THLD = 10.0   # Threshold temperature indicating start of growing season
T_BASE = 6.0    # Base temperature for phenological development
T_OPT = 100.0   # Optimum temperature for phenological development
T_MAX = 100.0   # Maximum temperature for phenological development

def thermal_time(t_base, t_opt, tmax, tmp):
    '''Calculate thermal time following Cycles method'''
    if tmp <= t_base or tmp >= tmax:
        thermal_time = 0.0
    elif tmp < t_opt:
        thermal_time = tmp - t_base
    else:
        thermal_time = (tmax - tmp) / (tmax - t_opt) * (t_opt - t_base)

    return thermal_time


def read_weather(file, hlines, latline):
    '''Read weather file to Pandas dataframe'''
    # Read latitude
    with open(file, 'r') as fp:
        lines = fp.readlines()
        latitude = float(lines[latline - 1].split()[1])

    # Read temperatures
    df = pandas.read_csv(file,
                         sep=' ',
                         header=None,
                         skipinitialspace=True,
                         skiprows=list(range(hlines)),
                         usecols=[0, 1, 3, 4],
                         na_values=[-999])

    df.columns = ['year', 'doy', 'tmax', 'tmin']

    # Calculate daily average temperature
    df['tavg'] = 0.5 * df['tmax'] + 0.5 * df['tmin']

    return latitude, df


def cum_thermal_time(latitude, doy, tmp, tavg, gs, tt0):
    '''Calculate cumulative thermal time'''
    # Determine on/off of growing season
    if latitude >= 0.0:
        # Switch to growing season when moving average temperature in spring
        # becomes higher than threshold
        gs = 1 if doy < 152 and tmp >= T_THLD else gs

        # Switch to dormant season when air temperature (or moving average) in
        # fall becomes lower than threshold
        gs = 0 if doy >= 245 and tmp < T_THLD else gs

    # Cumulate thermal time during growing season
    tt = thermal_time(T_BASE, T_OPT, T_MAX, tavg) + tt0 if gs == 1 else 0.0

    return gs, tt


def write_header_line(all_days, window, fp):
    '''Write thermal time file header line'''
    if all_days:
        fp.write('%-8s%-8s%-8s%-8s%-8s%s\n' % (
            'YEAR', 'DOY', 'TAVG',
            'TMA%d' % (window), 'TT', 'GROWING'))
    else:
        fp.write('%-8s%-8s%-8s%s\n' % ('DOY', 'TAVG', 'TT', 'GROWING'))


def write_tt_line(all_days, df, tt, gs, fp):
    '''Write one line of thermal time file'''
    if all_days:
        fp.write('%-8d%-8d%-8.2f%-8.2f%-8.1f%d\n' % (
            df['year'], df['doy'], df['tavg'], df['tma'], tt, gs
        ))
    else:
        fp.write('%-8d%-8.2f%-8.1f%d\n' % (df['doy'], df['tavg'], tt, gs))


def parse_arguments():
    '''Parse command line arguments'''
    parser = argparse.ArgumentParser(description='Calculate thermal time given '
                                     'Cycles weather files')
    parser.add_argument(
        '-p',
        '--path',
        type=str,
        required=True,
        help='Path',
    )
    parser.add_argument(
        '-e',
        '--extension',
        type=str,
        required=True,
        help='File extension',
    )
    parser.add_argument(
        '-n',
        '--hlines',
        type=int,
        required=True,
        help='Number of header lines',
    )
    parser.add_argument(
        '-l',
        '--latline',
        type=int,
        required=True,
        help='Line number for latitude',
    )
    parser.add_argument(
        '-w',
        '--window',
        type=int,
        default=14,
        help='Averaging window',
    )
    parser.add_argument(
        '-a',
        '--all_days',
        action='store_true',
    )

    args = parser.parse_args()

    return (args.path, args.extension, args.hlines, args.latline, args.window,
        args.all_days)


def main():
    '''Calculate thermal time given Cycles weather files
    '''
    # Get parameters from command line
    path, extension, hlines, latline, window, all_days = parse_arguments()

    for file in os.listdir(path):
        # Skip those files without matching extension
        if not file.endswith('.' + extension):
            continue

        print('Processing %s...' % (file))

        # Read weather files
        latitude, df = read_weather(os.path.join(path, file), hlines, latline)

        if all_days:
            # When calculate thermal time for all days, calculate moving average
            # air temperature to determine start and end of growing seasons
            df['tma'] = df.rolling(window, min_periods=1).mean()['tavg']
        else:
            # Remove DOY 366
            df = df.groupby('doy').mean().drop(366)
            df = df.reset_index()

        # Open thermal time files
        dirn = 'thermal_time'
        if not os.path.exists(dirn):
                os.makedirs(dirn)
        fn = dirn + '/' + file[0:-len(extension)] + 'tt.txt'

        with open(fn, 'w') as fp:
            # Write header line
            write_header_line(all_days, window, fp)

            # Initial values of cumulative thermal time and growing season flag
            tt = 0.0
            gs = 0

            for ind in range(len(df)):
                gs, tt = cum_thermal_time(
                    latitude,
                    df.iloc[ind]['doy'],
                    df.iloc[ind]['tma'] if all_days else df.iloc[ind]['tavg'],
                    df.iloc[ind]['tavg'],
                    gs,
                    tt,
                )

                write_tt_line(all_days, df.iloc[ind], tt, gs, fp)


if __name__ == '__main__':
    main()
