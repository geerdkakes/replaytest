#!/usr/bin/env bash

#############################################
# fixed variables
#
# Note that basename_a and basename_c should be present! Alternatively an
# inbetween measuring point can be given using basename_b
#############################################
source variables.sh
basename_a="device"
basename_b="upfgnb"
basename_c="server"
scriptname=$0
#############################################
# interpret command line flags
#############################################
while [ -n "$1" ]
do
    case "$1" in
        -s) session_id="$2"
            echo "${scriptname} session id: $session_id"
            shift ;;
        -d) dev_id="$2"
            echo "${scriptname} device id: $dev_id"
            shift ;;
        --) shift
            break ;;
        *) echo "${scriptname} $1 is not an option";;
    esac
    shift
done


#############################################
# dynamic variables
#############################################
if [ "${session_id}" = "" ]; then
  pcap_dir="${data_dir_server}"
else
  pcap_dir="${data_dir_server}/${session_id}"
fi

if [ ! -d "${pcap_dir}" ] ; then
    echo "${scriptname}: Directory ${pcap_dir} does not exist"
fi
devs=($(ls ${pcap_dir} | grep .pcap | sed 's/\(.*\)_\(.*\)_.*_.*.pcap/\2/' | sort | uniq))


#############################################
# find and convert server csv files
#############################################
echo "decoding pcap files"
for dev in ${devs[@]}; do
    if [ ! -z $dev_id ] && [[ "${dev_id}" != "${dev}" ]]; then
        echo "${scriptname}: device id ${dev_id} specified to analyse but not matched to ${dev}, continuing"
        continue
    fi
    echo "${scriptname}: processing dev: ${dev}"
    echo "${scriptname}: ...............processing ${basename_c} side pcaps"
    echo ""
    for filename in ${pcap_dir}/${basename_c}_${dev}*.pcap; do
        [ -e "$filename" ] || continue
        echo ${scriptname}: decoding $filename
        echo node --max-old-space-size=14000 "${pcap_analysis_app}" -c ${pcap_analysis_config_file} -i ${filename} -s true -b ${basename_c}${dev}
        node --max-old-space-size=14000 "${pcap_analysis_app}" -c ${pcap_analysis_config_file} -i ${filename} -s true -b ${basename_c}${dev}
    done
    echo "${scriptname}: ...............processing ${basename_b} side pcaps"
    echo ""
    for filename in ${pcap_dir}/${basename_b}_${dev}*.pcap; do
        [ -e "$filename" ] || continue
        echo ${scriptname}: decoding $filename
        echo node --max-old-space-size=14000 "${pcap_analysis_app}" -c ${pcap_analysis_config_file} -i ${filename} -s true -b ${basename_b}${dev}
        node --max-old-space-size=14000 "${pcap_analysis_app}" -c ${pcap_analysis_config_file} -i ${filename} -s true -b ${basename_b}${dev}
    done
    echo "${scriptname}: ...............processing device side pcaps"
    echo ""
    for filename in ${pcap_dir}/${basename_a}_${dev}*.pcap; do
        [ -e "$filename" ] || continue
        echo ${scriptname}: decoding $filename
        echo node --max-old-space-size=14000 "${pcap_analysis_app}" -c ${pcap_analysis_config_file} -i ${filename} -s true -b ${basename_a}${dev}
        node --max-old-space-size=14000 "${pcap_analysis_app}" -c ${pcap_analysis_config_file} -i ${filename} -s true -b ${basename_a}${dev}
    done
done

#############################################
# matching csv files and comparing them
#############################################
echo "matching decoded files"
for dev in ${devs[@]}; do
    if [ ! -z $dev_id ] && [[ "${dev_id}" != "${dev}" ]]; then
        echo "${scriptname}: device id ${dev_id} specified to analyse but not matched to ${dev}, continuing"
        continue
    fi
    echo "${scriptname}: processing dev: ${dev}"
    for filename in ${pcap_dir}/*${basename_a}${dev}.csv; do
        echo "${scriptname}: for file: $filename:"
        if [ ! -e "$filename" ]; then
            echo "does not exist"
            continue
        fi
        date_str="`/usr/bin/basename $filename | sed 's/\(.*\..*\..*\)_\(.*\..*\..*\)-\(.*..*..*\)_\(.*\)\.\(.*\)/\1/'`" # 2021.2.3
        echo data_str: $date_str
        time_lower="`/usr/bin/basename $filename | sed 's/\(.*\..*\..*\)_\(.*\..*\..*\)-\(.*..*..*\)_\(.*\)\.\(.*\)/\2/'`" # 10.20.0
        echo time_lower: $time_lower
        time_upper="`/usr/bin/basename $filename | sed 's/\(.*\..*\..*\)_\(.*\..*\..*\)-\(.*..*..*\)_\(.*\)\.\(.*\)/\3/'`" # 10.25.0
        echo time_upper: $time_upper
        filename_a="${pcap_dir}/${date_str}_${time_lower}-${time_upper}_${basename_a}${dev}.csv"
        filename_b="${pcap_dir}/${date_str}_${time_lower}-${time_upper}_${basename_b}${dev}.csv"
        filename_c="${pcap_dir}/${date_str}_${time_lower}-${time_upper}_${basename_c}${dev}.csv"
        filename_result_a_c="${pcap_dir}/compare_${dev}_${date_str}_${time_lower}-${time_upper}_${basename_a}-${basename_c}.csv"
        filename_result_b_c="${pcap_dir}/compare_${dev}_${date_str}_${time_lower}-${time_upper}_${basename_b}-${basename_c}.csv"
        filename_result_a_b="${pcap_dir}/compare_${dev}_${date_str}_${time_lower}-${time_upper}_${basename_a}-${basename_b}.csv"
        # checking if filenames exist, if not continue to next file
        [ -e "$filename_a" ] || continue
        [ -e "$filename_c" ] || continue
        echo "found matching filename: $filename_c"
        echo  "comparing files and storing result in: ${filename_result_a_c}"
        echo node --max-old-space-size=12000 "${pcap_analysis_app}" -c ${pcap_analysis_config_file} -r ${filename_result_a_c} --compare=${filename_a},${filename_c}
        node --max-old-space-size=12000 "${pcap_analysis_app}" -c ${pcap_analysis_config_file} -r ${filename_result_a_c} --compare=${filename_a},${filename_c}
        [ -e "$filename_b" ] || continue
        echo "found matching filename: $filename_b"
        echo  "comparing files and storing result in: ${filename_result_b_c}"
        echo node --max-old-space-size=12000 "${pcap_analysis_app}" -c ${pcap_analysis_config_file} -r ${filename_result_b_c} --compare=${filename_b},${filename_c}
        node --max-old-space-size=12000 "${pcap_analysis_app}" -c ${pcap_analysis_config_file} -r ${filename_result_b_c} --compare=${filename_b},${filename_c}
        echo
        echo  "comparing files and storing result in: ${filename_result_a_b}"
        echo node --max-old-space-size=12000 "${pcap_analysis_app}" -c ${pcap_analysis_config_file} -r ${filename_result_a_b} --compare=${filename_a},${filename_b}
        node --max-old-space-size=12000 "${pcap_analysis_app}" -c ${pcap_analysis_config_file} -r ${filename_result_a_b} --compare=${filename_a},${filename_b}
        echo
    done
done
poclab@fr52_mps:~/latencytests  $