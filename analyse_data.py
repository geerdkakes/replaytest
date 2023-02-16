#!/usr/bin/env python3
from time import time
from numpy.lib.shape_base import column_stack
import pandas as pd
import json
import numpy as np
import matplotlib.pyplot as plt
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import sys
import os
from datetime import datetime
import re


# run using: ./analyse_data.py -rb ../datadir/Low_Latency_Test_Eindhoven_20211129_042742_Eindhoven_BIC_Usage_of_Radio_Resource_Monitoring_20211129_144832.csv ../datadir/20211129_02*/*.json

i=1
data_files = []
rb_blocks_file = None
while  i < len(sys.argv):
    if sys.argv[i] == '-rb':
        if (i+1) < len(sys.argv):
            rb_blocks_file = sys.argv[i+1]
            i += 1
        i += 1
        continue
    data_files.append(sys.argv[i])
    i += 1


#############################################################################################
# Load json output data from iperf
# For each interval the sumbits_per_second is used to calculate the bytes, kbytes and Mbytes per second
# timestamp is added to each interval record with microseond accuracy
# a pandas dataframe is returned with the data
#
# this function is tested with iperf tcp
#############################################################################################
def load_iperf_json(filename):

    deviceid = re.findall(r'([a-z0-9]*)_[a-z0-9]*_[0-9]*-[0-9]*-[0-9]*_[0-9]*\.[0-9]*\.json$', filename)[0]

    data = {}

    with open(filename,'r') as f:
        try:
            data = json.loads(f.read())
        except ValueError:
            print('Decoding JSON for file failed: ' + filename)
    
    # check if dataset contains basic information
    if "start" in data and "test_start" in data['start']: 

        # check if TCP. if so change dataset such that it is smilar as when doing a UDP test
        if data['start']['test_start']['protocol'] == 'TCP':
            print("found tcp ")
            if "end" in data:
                if "sum" in data['end']:
                    data['end']['sum'] = data['end']['sum_received']
                    data['end']['sum']['packets'] = data['end']['sum_sent']['bytes'] / data['start']['test_start']['blksize']
                    data['end']['sum']['lost_bytes'] = data['end']['sum_sent']['bytes'] - data['end']['sum_received']['bytes']
                    data['end']['sum']['lost_packets'] = data['end']['sum']['lost_bytes'] / data['start']['test_start']['blksize']
                    data['end']['sum']['lost_percent'] = data['end']['sum']['lost_packets'] / data['end']['sum']['packets']
            
        df = pd.json_normalize(data, record_path =['intervals'], 
            meta=[
                ['title']
            ], errors='ignore')

        # find static variables and add to dataset
        if 'end' in data and 'sum' in data['end']:
            if 'seconds' in data['end']['sum']:
                df['total_seconds'] = data['end']['sum']['seconds']
            if 'bytes' in data['end']['sum']:
                df['total_bytes'] = data['end']['sum']['bytes']
            if 'seconds' in data['end']['sum']:
                df['total_seconds'] = data['end']['sum']['seconds']
            if 'lost_packets' in data['end']['sum']:
                df['total_lost_packets'] = data['end']['sum']['lost_packets']
            if 'packets' in data['end']['sum']:
                df['total_packets'] = data['end']['sum']['packets']
            if 'bits_per_second' in data['end']['sum']:
                df['total_bits_per_second'] = data['end']['sum']['bits_per_second']
            if 'lost_percent' in data['end']['sum']:
                df['total_lost_percent'] = data['end']['sum']['lost_percent']
        if 'start' in data and 'test_start' in data['start']:
            if 'protocol' in data['start']['test_start']:
                df['protocol'] = data['start']['test_start']['protocol']
            if 'blksize' in data['start']['test_start']:
                df['blksize'] = data['start']['test_start']['blksize']
        if "start" in data and "timestamp" in data['start']:
            starttimestamp = data['start']['timestamp']['timesecs']
        else:
            starttimestamp = 0
            print("starttime missing")
        df['timestamp_microsec'] = (starttimestamp + df['sum.start'])*1000000
        # add an hour to align with resource block data
        df['timestamp_milisec'] = df['timestamp_microsec'] / 1000 + 7200000
        df['timestamp'] = df['timestamp_milisec'].apply(np.int64)
        df['kbit_per_second'] = df['sum.bits_per_second'] / 1000
        if data['start']['test_start']['reverse'] == 0:
            # upload of data. we record the send data rate
            df['up_Mbit_per_second'] = df['kbit_per_second'] / 1000
            df['down_Mbit_per_second'] = 0
            df['direction'] = 'up'
        else:
            # download of data
            df['down_Mbit_per_second'] = df['kbit_per_second'] / 1000
            df['up_Mbit_per_second'] = 0
            df['direction'] = 'down'
        df.columns = df.columns.str.replace('sum.', '')
        df['device'] = deviceid
        # drop columns not needed
        df = df.drop(columns=[ 'timestamp_microsec', 'timestamp_milisec', 'streams'])
        df.set_index('timestamp')
    else:
        # no data found in file. Populating empty datafile for 60 seconds
        timestamp = int(os.path.getmtime(filename))*1000 + 7200000
        if 'title' in data:
            title = data['title']
        else:
            title = ""
        empty_array = {
            'timestamp': [x*1000 + timestamp for x in range(60)],
            'up_Mbit_per_second': [0 for x in range(60)],
            'down_Mbit_per_second': [0 for x in range(60)],
            'title': [title for x in range(60)],
            'packets_lost': [0 for x in range(60)],
            'packets_send': [0 for x in range(60)],
            'percentage_lost': [100 for x in range(60)],
            'direction': ['' for x in range(60)],
            'device': [deviceid for x in range(60)],
            'total_lost_percent': [100 for x in range(60)],
            'total_bits_per_second': [0 for x in range(60)]
        }

        df = pd.DataFrame.from_dict(empty_array)
        df.set_index('timestamp')
        print("returning empty array for file: " + filename)

    return df
#############################################################################################
# Load csv output data from iperf2
# For each interval the bitrate and packet loss is determined
# 
# a pandas dataframe is returned with the data
#
# this function is tested with iperf2 using udp
#############################################################################################
def load_iperf_csv(filename):
    names= [
        "datetime_str",
        "source_ip",
        "source_port",
        "dest_ip",
        "dest_port",
        "iperf_proc_num",
        "time_interval",
        "data_transferred_bytes",
        "bits_per_second",
        "jitter_ms",
        "num_lost_pckts",
        "packets_send",
        "perc_lost",
        "num_out_of_order"
    ]

    # convert datetime string to timestamp
    # 20220315120825
    def date_time_str_to_timestamp(number):
        year = int(str(number)[:4])
        month = int(str(number)[4:6])
        day = int(str(number)[6:8])
        hour = int(str(number)[8:10])
        minute = int(str(number)[10:12])
        seconds = int(str(number)[12:])
        found_datetime = datetime(year, month, day, hour, minute, seconds)
        return datetime.timestamp(found_datetime)
    

    df = pd.read_csv(filename,names=names)
    df['direction'] = "down"
    df.loc[df['source_port'] > 10000, 'direction'] = "up"
    df['timestamp']  = df['datetime_str'].apply(date_time_str_to_timestamp)
    df['timestamp'] = (df['timestamp'] * 1000  + 7200000 ).apply(np.int64)
    df['kbit_per_second'] = df['bits_per_second'] / 1000
    df['down_Mbit_per_second'] = 0
    df['up_Mbit_per_second'] = 0
    df.loc[df['direction'] == 'down', 'down_Mbit_per_second'] = df.loc[df['direction'] == 'down', 'kbit_per_second']/1000
    df.loc[df['direction'] == 'up', 'up_Mbit_per_second'] = df.loc[df['direction'] == 'up', 'kbit_per_second']/1000
    df = df.drop(columns=[ 'source_ip', 'source_port', 'dest_ip', 'dest_port', 'iperf_proc_num', 'time_interval'])
    df.set_index('timestamp')
    return df

#############################################################################################
# Load csv file exported by U2020 from Huawei
# the file contains per second the amound of resource blocks used for uplink and downlink
# output: dataframe containing:
#     timestamp:                microsecond timestamp, also the index
#     Downlink Used RB Num:     Resouce blocks used in downlink
#     Uplink Used RB Num:       Resource blocks used in uplink
#     NR DU Cell ID:            cell id
#     DateTime:                 date time field with second accuracy
#############################################################################################
def load_resource_blocks(filename):
    df = pd.read_csv(filename, skiprows=9)

    # DateTime format in file: '2021-11-25 09:10:25 (4)'
    # Convert to: '2021-11-25 09:10:25' and store miliseconds in separate column
    df['DateTime'] = df['Time'].replace({r'(.*)\s\((\d+)\)' : r'\g<1>'}, regex=True)
    
   
    df['miliseconds'] = df['Time'].replace({r'(.*)\s\((\d+)\)' : r'\g<2>'}, regex=True).astype(np.int64)
    
    # create datetime field with second accuracy
    # df['DateTime'] = pd.to_datetime(df['DateTime'],format='%Y-%m-%d %H:%M:%S DST')
    df['DateTime'] = pd.to_datetime(df['DateTime'],format='%Y-%m-%d %H:%M:%S')
    # current data format 2023-02-09 11:32:44 (570)
    # create timestamp in miliseconds:
    df['nanoseconds'] = df['miliseconds'] * 1000000
    df['timestamp_nanoseconds'] = df.DateTime.values.astype(np.int64) + df['nanoseconds']
    df['timestamp_miliseconds'] = df['timestamp_nanoseconds'] / 1000000
    df['timestamp'] = df['timestamp_miliseconds'].apply(np.int64)
    df.set_index('timestamp')
    df['uplink_percentage'] = df['Uplink Used RB Num'] / 33000 * 100
    df['downlink_percentage'] = df['Downlink Used RB Num'] / 169000 * 100
    print(df)
    # drop columns not needed
    df = df.drop(columns=['Time', 'miliseconds', 'nanoseconds', 'timestamp_nanoseconds', 
                        'timestamp_miliseconds', 'CN Operator Index', 'PLMN Downlink Used RB Num', 
                        'PLMN Uplink Used RB Num', 'NR DU Cell TRP ID'])

    # return dataframe
    return df
#############################################################################################
# Load modem output, generated by script generating the data
# data should be of csv format, containing the correct headers:
#
#  timestamp,lat,lon,cell_type,state,technology,duplex_mode,mcc,mnc,cell_id,pc_id,tac,arfcn,band,nr_dl_bandwidth,rsrp,rsrq,sinr,scs,srxlev 
#
# a pandas dataframe is returned with the data
#############################################################################################

def load_modem_csv(filename):
    try:
        df = pd.read_csv(filename)
    except FileNotFoundError:
        print("File Doesn't Exist: " + filename)
    else:
        df.set_index('timestamp')
        return df


#############################################################################################
# merge dataframes. df_sub is merged in df_data
# merging is done based on timestamp
#
# a pandas dataframe is returned with the data
#
#############################################################################################
def merge_dataframes(df_sub, df_data):
    
    length_sub = df_sub.shape[0]
    length_main = df_data.shape[0]
    
    i_s = 0
    i_d = 0
    
    start_s = 0
    start_d = 0
    
    end_s = 0
    end_d = 0
    
    # loop over data array to find start and end
    while i_s < length_sub and i_d < length_main:
        if abs(df_sub.iloc[i_s]['timestamp'] - df_data.iloc[i_d]['timestamp']) <= 1500:
            start_s = i_s
            start_d = i_d
            break
        if df_sub.iloc[i_s]['timestamp'] < df_data.iloc[i_d]['timestamp']:
            i_s += 1
        else:
            i_d += 1
    
    i_s = length_sub - 1
    i_d = length_main - 1

    while i_s >=0 and i_d >= 0:
        if abs(df_sub.iloc[i_s]['timestamp'] - df_data.iloc[i_d]['timestamp']) <= 1500:
            end_s = i_s
            end_d = i_d
            break
        if df_sub.iloc[i_s]['timestamp'] < df_data.iloc[i_d]['timestamp']:
            i_d -= 1
        else:
            i_s -= 1


    df_sub = df_sub.iloc[start_s:end_s]
    df_data = df_data.iloc[start_d:end_d]
    rows_sub = df_sub.shape[0]

    columns_to_copy = []
    matched_array = []
    for col in df_sub.columns:
        if col != "timestamp" and col != "DateTime":
            columns_to_copy.append(col)
            matched_array.append([])

    # find the matching timestaps in df_sub and copy the columns of interest in a seperate array
    for index, row in df_data.iterrows():
        index_sub = np.searchsorted(df_sub['timestamp'], row['timestamp'], side='left', sorter=None)
        if index_sub >= rows_sub:
            index_sub=index_sub -1
        for i_s, column in enumerate(columns_to_copy):
            matched_array[i_s].append(df_sub.iloc[index_sub][column])
    # stop warning before copying the found values to df_data
    pd.options.mode.chained_assignment = None
    for index, column in enumerate(columns_to_copy):
        df_data.loc[:, column]= matched_array[index]
    pd.options.mode.chained_assignment = 'warn'

    return df_data

#############################################################################################
# classify rsrp
# input: pandas dataframe with rsrp column
# output: pandas dataframe with extra column containing a five scale rsrp quality indicator
#
#############################################################################################
def classify_rsrp_signal_strength(df):
    conditions = [
        (df['rsrp'] >= -116),
        (df['rsrp'] >= -119) & (df['rsrp'] < -116),
        (df['rsrp'] >= -123) & (df['rsrp'] < -119),
        (df['rsrp'] >= -124) & (df['rsrp'] < -123),
        (df['rsrp'] < -124)
        ]

    values = ['0', '1', '2', '3', '4']
    df['rsrp_quality'] = np.select(conditions, values)
    return df
#############################################################################################
# classify  sinr
# input: pandas dataframe with sinr column
# output: pandas dataframe with extra column containing a four scale sinr quality indicator
#
#############################################################################################
def classify_sinr_signal_strength(df):
    conditions = [
        (df['sinr'] >= 4),
        (df['sinr'] >= 0) & (df['sinr'] < 4),
        (df['sinr'] >= -5) & (df['sinr'] < 0),
        (df['sinr'] < -5)
        ]

    values = ['0', '1', '2', '3']
    df['sinr_quality'] = np.select(conditions, values)
    return df
#############################################################################################
# add five scale color indicator
# input: pandas dataframe with quality indocator column
# output: pandas dataframe with extra column containing a five scale color
#
#############################################################################################
def add_five_color_scale(df, column_to_map, color_column):
    five_color_scale = ['#2ca02c','#d8e305','#fcf260','#fa8f2a','#f50707']

    length_df = df.shape[0]
    i = 0
    tmp_arr = []

    while i < length_df:
        tmp_arr.append(five_color_scale[int(df.iloc[i][column_to_map])])
        i += 1
    tmp_df = pd.DataFrame(
    {
        color_column: tmp_arr
    })
    df = pd.concat([df.reset_index(drop=True), tmp_df.reset_index(drop=True)], axis=1, join='outer')
    return df
#############################################################################################
# combine sinr and rsrp quality indicator
# input: pandas dataframe with sinr - and rsrp quality indocator columns
# output: pandas dataframe with extra column containing a four scale  quality indicator
#
#############################################################################################
def classify_signal_quality(df):
    print(df.shape)
    df = classify_rsrp_signal_strength(df)
    df = classify_sinr_signal_strength(df)
    df['signal_quality_value'] = df[['rsrp_quality','sinr_quality']].max(axis=1).apply(np.int32)
    print(df.shape)
    df = add_five_color_scale(df, 'signal_quality_value', 'signal_quality_color')
    print(df.shape)
    return df
#############################################################################################
# add a five scale quality indicator based on min and max value in a column
# input: pandas dataframe 
# output: pandas dataframe with extra column containing a five scale  quality indicator
#
#############################################################################################
def classify_number_quality(df,column_to_classify,column_to_add ):
    print(df.shape)
    minvalue = df[column_to_classify].min()
    maxvalue = df[column_to_classify].max()
    conditions = [
        (df[column_to_classify] < (maxvalue-minvalue)*1/5),
        (df[column_to_classify] >= (maxvalue-minvalue)*1/5) & (df[column_to_classify] < (maxvalue-minvalue)*2/5),
        (df[column_to_classify] >= (maxvalue-minvalue)*2/5) & (df[column_to_classify] < (maxvalue-minvalue)*3/5),
        (df[column_to_classify] >= (maxvalue-minvalue)*3/5) & (df[column_to_classify] < (maxvalue-minvalue)*4/5),
        (df[column_to_classify] >= (maxvalue-minvalue)*4/5)
        ]

    values = ['4', '3', '2', '1', '0']
    df[column_to_add] = np.select(conditions, values)
    return df
#############################################################################################
# load csv matching file, generated by pcap_analysis
# input: csv filename
# output: pandas dataframe with aggregated per second the dataloss, datarate and data direction
#
#############################################################################################
def read_pcap_analysis_csv_datarate(filename):
    df = pd.read_csv(filename)

    patternelements = []
    patterns = [r'compare_total_([a-z0-9]*)\.csv$',
                r'compare_([a-z0-9]*)_(?:.*)_(?:.*)-(?:.*)\.csv$']
    index = 0
    while len(patternelements) == 0 and index < len(patterns):
        patternelements = re.findall(patterns[index], filename)
        index +=1

    if len(patternelements) > 0:
        deviceid = patternelements[0]
    else:
        deviceid = 'unknown'

    df['timestamp_microseconds'] = df['source_pcapPacketHeader.ts_sec'] * 1000000 + df['source_pcapPacketHeader.ts_usec']
    df['timestamp'] = df['timestamp_microseconds'].apply(np.int64)
    df['DateTime'] = pd.to_datetime(df['timestamp'], unit='us')
    df = df.set_index('DateTime')
    # below is a hack to prevent re run of big dataset. We should always use the actual direction per rule
    up_count = df[df['direction'] == 'up'].shape[0]
    down_count = df[df['direction'] == 'down'].shape[0]
    if up_count > down_count:
        direction = 'up'
    else:
        direction = 'down'
    # df_up = df[df['direction'] == 'up']
    # df_down = df[df['direction'] == 'down']
    def aggregate(df_to_aggregate):
        bandwidth_kbps = df_to_aggregate['pcapPacketHeader.orig_len'].sum() * 8 / 1024
        bandwidth_Mbps = bandwidth_kbps / 1024
        packets_lost = df_to_aggregate[df_to_aggregate['lost'] == True].shape[0]
        total_packets = df_to_aggregate.shape[0]
        percentage_lost = packets_lost / total_packets
        # add an hour to align with resource block data
        timestamp = int(df_to_aggregate['timestamp_microseconds'].iloc[0]/1000 + 7200000)
        aggregated_array = {
            'bandwidth_kbps': [bandwidth_kbps],
            'bandwidth_Mbps': [bandwidth_Mbps],
            'packets_lost': [packets_lost],
            'packets_send': [total_packets],
            'percentage_lost': [percentage_lost],
            'timestamp': [timestamp],
            'direction': direction,
            'device': deviceid
        }

        return pd.DataFrame.from_dict(aggregated_array)

    df = df.resample('1S').apply(aggregate)

    # do not set index to timestamp else we can not reference it anymore as df['timestamp']
    # df = df.set_index('timestamp')
    # df = df.drop(columns=[ 'DateTime' ])

    return df
#############################################################################################
# load csv matching file, generated by pcap_analysis
# input: csv filename
# output: pandas dataframe including
# - delay_usec
# - timestamp
# - lost
#############################################################################################
def read_pcap_analysis_csv_latency(filename):
    df = pd.read_csv(filename)
    patternelements = []
    patterns = [r'compare_total_([a-z0-9]*)\.csv$',
                r'compare_([a-z0-9]*)_(?:.*)_(?:.*)-(?:.*)\.csv$']
    index = 0
    while len(patternelements) == 0 and index < len(patterns):
        patternelements = re.findall(patterns[index], filename)
        index +=1

    if len(patternelements) > 0:
        deviceid = patternelements[0]
    else:
        deviceid = 'unknown'

    df['timestamp_microseconds'] = df['source_pcapPacketHeader.ts_sec'] * 1000000 + df['source_pcapPacketHeader.ts_usec']
    df['timestamp'] = (df['timestamp_microseconds'] / 1000 + 7200000).apply(np.int64)
    df['device'] = deviceid

    df.loc[df['direction'] == 'down', 'down_latency'] = df.loc[df['direction'] == 'down', 'delay_usec']/1000
    df.loc[df['direction'] == 'up', 'up_latency'] = df.loc[df['direction'] == 'up', 'delay_usec']/1000

    df.set_index('timestamp')
    return df

#############################################################################################
# load ping log
# input: ping log file with extra fields at the start of the log
# output: pandas dataframe
#
#############################################################################################
def load_ping_log(filename):
    deviceid = re.findall(r'([a-z0-9]*)_ping_[0-9]*-[0-9]*-[0-9]*_[0-9]*\.[0-9]*\.log$', filename)[0]
    fields = ['text']
    df = pd.read_csv(filename, names=fields, skiprows=4)

    df = df[df["text"].str.contains(r'\[([0-9.]*)\]\s([0-9]*)\sbytes\sfrom\s[0-9.]*:\sicmp_seq=([0-9]*)\sttl=[0-9]*\stime=([0-9.]*)\sms')]

    df[["timestamp", "bytes", "sequence_nr", "time"]] = df["text"].str.extract(r'\[([0-9.]*)\]\s([0-9]*)\sbytes\sfrom\s[0-9.]*:\sicmp_seq=([0-9]*)\sttl=[0-9]*\stime=([0-9.]*)\sms')
    df = df.drop(columns=[ 'text'])

    # read file to get start time (should be on first line)
    s = open(filename, 'r')                            
    contents = s.read()     
    title = re.findall(r'title:([a-z0-9_]*)', contents)[0]
    size = re.findall(r'size:([a-z0-9_]*)', contents)[0]
    intervalmsec = re.findall(r'intervalmsec:([a-z0-9_]*)', contents)[0]
    print("title found: " + title)
    df['title'] = title
    df['size'] = size
    df['intervalmsec'] = intervalmsec
    df['timestamp'] = (df['timestamp'].apply(np.float64)*1000 + 7200000).apply(np.int64)
    df['time'] = df['time'].apply(np.float64)
    df['device'] = deviceid

    # devicedev1_ping_04-26-22_09.46.log

    return df

#############################################################################################
# main program
# Loop through data files 
#
# possible data types:
# iperf3 dev1
# iperf3 dev2
# nuttcp devicedev1
# nuttcp devicedev2
# pingtest dev1
# pingtest dev2
# udptest up dev1
# udptest up dev2
# udptest down dev 1
# udptest down dev 2
# resource blocks
#############################################################################################

# load data files
index_iperfdev1 = 0
index_iperfdev2 = 0
index_iperfdev3 = 0
index_pingdev1 = 0
index_pingdev2 = 0
index_pcaplatencydev1 = 0
index_pcaplatencydev2 = 0
index_pcapdataratedev1 = 0
index_pcapdataratedev2 = 0
index_pcap = 0

# initialize empty frames
df_all = {}
df_all['df_iperfdev1'] = pd.DataFrame()
df_all['df_iperfdev2'] = pd.DataFrame()
df_all['df_iperfdev3'] = pd.DataFrame()
df_all['df_pingdev1'] = pd.DataFrame()
df_all['df_pingdev2'] = pd.DataFrame()
df_all['df_pcaplatencydev1'] = pd.DataFrame()
df_all['df_pcaplatencydev2'] = pd.DataFrame()
df_all['df_pcapdataratedev1'] = pd.DataFrame()
df_all['df_pcapdataratedev2'] = pd.DataFrame()
df_all['df_resourceblocks'] = pd.DataFrame()

for index, file in enumerate(data_files):

    # this operation is very compute intensive, better to first concatenate and then build dataframe:
    print("loading file: " + file)
    filename, file_extension = os.path.splitext(file)

    if file_extension == '.json':
        df = load_iperf_json(file)
        if df.iloc[0]['device'] == 'devicedev1' or df.iloc[0]['device'] == 'serverdev1':
            if index_iperfdev1 == 0:
                df_all['df_iperfdev1'] = df
            else:
                df_all['df_iperfdev1'] = df_all['df_iperfdev1'].append(df,ignore_index=False)
            index_iperfdev1 = index_iperfdev1 + 1
        elif df.iloc[0]['device'] == 'devicedev2' or df.iloc[0]['device'] == 'serverdev2':
            if index_iperfdev2 == 0:
                df_all['df_iperfdev2'] = df
            else:
                df_all['df_iperfdev2'] = df_all['df_iperfdev2'].append(df,ignore_index=False)
            index_iperfdev2 = index_iperfdev2 + 1
        elif df.iloc[0]['device'] == 'devicedev3' or df.iloc[0]['device'] == 'serverdev3':
            if index_iperfdev2 == 0:
                df_all['df_iperfdev3'] = df
            else:
                df_all['df_iperfdev3'] = df_all['df_iperfdev3'].append(df,ignore_index=False)
            index_iperfdev3 = index_iperfdev3 + 1
    if file_extension == '.log':
        df = load_ping_log(file)
        if df.iloc[0]['device'] == 'devicedev1':
            if index_pingdev1 == 0:
                df_all['df_pingdev1'] = df
            else:
                df_all['df_pingdev1'] = df_all['df_pingdev1'].append(df,ignore_index=False)
            index_pingdev1 = index_pingdev1 + 1
        elif df.iloc[0]['device'] == 'devicedev2':
            if index_pingdev2 == 0:
                df_all['df_pingdev2'] = df
            else:
                df_all['df_pingdev2'] = df_all['df_pingdev2'].append(df,ignore_index=False)
            index_pingdev2 = index_pingdev2 + 1

    if file_extension == '.csv':
        df = read_pcap_analysis_csv_latency(file)
        if df.iloc[0]['device'] == 'dev1':
            if index_pcaplatencydev1 == 0:
                df_all['df_pcaplatencydev1'] = df
            else:
                df_all['df_pcaplatencydev1'] = df_all['df_pcaplatencydev1'].append(df,ignore_index=False)
            index_pcaplatencydev1 = index_pcaplatencydev1 + 1
        elif df.iloc[0]['device'] == 'dev2':
            if index_pcaplatencydev2 == 0:
                df_all['df_pcaplatencydev2'] = df
            else:
                df_all['df_pcaplatencydev2'] = df_all['df_pcaplatencydev2'].append(df,ignore_index=False)
            index_pcaplatencydev2 = index_pcaplatencydev2 + 1

    if file_extension == '.csv':
        df = read_pcap_analysis_csv_datarate(file)
        if df.iloc[0]['device'] == 'dev1':
            if index_pcapdataratedev1 == 0:
                df_all['df_pcapdataratedev1'] = df
            else:
                df_all['df_pcapdataratedev1'] = df_all['df_pcapdataratedev1'].append(df,ignore_index=False)
            index_pcapdataratedev1 = index_pcapdataratedev1 + 1
        elif df.iloc[0]['device'] == 'dev2':
            if index_pcapdataratedev2 == 0:
                df_all['df_pcapdataratedev2'] = df
            else:
                df_all['df_pcapdataratedev2'] = df_all['df_pcapdataratedev2'].append(df,ignore_index=False)
            index_pcapdataratedev2 = index_pcapdataratedev2 + 1

# sort dataframes and find min and max timestamps
min_timestamp = 0
max_timestamp = 0

for  df_name in df_all:
    if 'timestamp' in df_all[df_name]:
        df_all[df_name] = df_all[df_name].sort_values(by=['timestamp'])
        if min_timestamp == 0 or df_all[df_name].iloc[0]['timestamp'] < min_timestamp:
            min_timestamp = df_all[df_name].iloc[0]['timestamp']
        if df_all[df_name].iloc[-1]['timestamp'] > max_timestamp:
            max_timestamp = df_all[df_name].iloc[-1]['timestamp']

for  df_name in df_all:
    if 'timestamp' in df_all[df_name]:
        df_all[df_name]['minutes'] = (df_all[df_name]['timestamp'] - min_timestamp) / (1000 * 60)

# load resource block file from U2020 tool
df_resourceblocks = pd.DataFrame()
if rb_blocks_file:
    df_all['df_resourceblocks'] = load_resource_blocks(rb_blocks_file)
    df_all['df_resourceblocks'] = df_resourceblocks[df_resourceblocks['timestamp'].between(min_timestamp,max_timestamp)]
    df_all['df_resourceblocks']['minutes'] = (df_resourceblocks['timestamp'] - min_timestamp) / (1000 * 60)

plots = []
plottypes = ['Uplink Used RB Num', 'Downlink Used RB Num', 'down_Mbit_per_second', 'up_Mbit_per_second', 'down_latency', 'up_latency', 'time', 'bandwidth_Mbps']
plotunits = ['# blocks', '# blocks', 'Mbps', 'Mbps', 'ms', 'ms', 'ms', 'Mbps']
plottitles = []
unitstoplot = []

for  df_name in df_all:
    for index, plottype in enumerate(plottypes):
        if plottype in df_all[df_name]:
            plotname = df_name[3:] + '_' + plottype
            plots.append({
                'name': plotname,
                'x': df_all[df_name]['minutes'],
                'y': df_all[df_name][plottype],
                'unit': plotunits[index]
            })
            print("adding to plots: " + plotname + " (" + plotunits[index] + ")")
            plottitles.append(plotname)
            unitstoplot.append(plotunits[index])

row = 1
if len(plottitles) == 0:
    print("nothing to plot")
    sys.exit(1)


fig = make_subplots(rows=len(plottitles), cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.09, 
                    subplot_titles=plottitles)

for plot in plots:
    fig.add_trace(go.Scatter(x=plot['x'], y=plot['y'], name=plot['name']),
                row=row, col=1)
    row +=1
height = int(300 * row)


fig.update_layout(height=height, width=1200,
                  title_text="time plot measured data")
fig.update_xaxes(title_text="minutes")
fig.update_xaxes(showticklabels=True)

row = 1
for plotunit in unitstoplot:
    fig.update_yaxes(title_text=plotunit, row=row, col=1)
    row +=1

fig.show()
