#!/usr/bin/env bash


scriptname="$0"

if [ "$#" -lt 2 ]; then
    echo "Usage:"
    echo "$scriptname -s <session_id>"
    exit 1
fi

#############################################
# load default variables
#############################################
source variables.sh
duration="210"

#############################################
# interpret command line flags
#############################################
while [ -n "$1" ]
do
    case "$1" in
        -s) session_id="$2"
            echo "${scriptname} session id: $session_id"
            shift ;;
        --) shift
            break ;;
        --server) server="$2"
            echo "${scriptname} server to use: ${server}"
            shift ;;
        -t) duration="${2}"
            echo "${scriptname} duration is: $duration"
            shift ;;
        *) echo "${scriptname} $1 is not an option";;
    esac
    shift
done


# parameters
device_pcap_capture="${data_dir_device}/${session_id}/device_dev1"
server_pcap_capture="${data_dir_server}/${session_id}/pcaps/server_dev1"

# displaying settings for future reference
echo "${scriptname}: the following variables are used for this script"
echo "${scriptname}: session_id: $session_id"
echo "${scriptname}: server: ${server}"
echo "${scriptname}: server_user: ${server_user}"
echo "${scriptname}: duration: $duration"
echo "${scriptname}: device_pcap_capture: ${device_pcap_capture}"
echo "${scriptname}: server_pcap_capture: ${server_pcap_capture}"
echo "${scriptname}: protocol: ${server_user}"
echo "${scriptname}: port_range: ${port_range}"
echo "${scriptname}: device_interface: ${device_interface}"
echo "${scriptname}: server_interface: ${server_interface}"
echo "${scriptname}: replay_pcap: ${replay_pcap}"
echo ""

echo "${scriptname}: checking pcap duration"
pcap_duration=$(capinfos  -u ${replay_pcap} | sed -n 2p | awk '{print $3}' |  xargs printf "%1.0f")
(( pcap_duration++ ))
tcpdump_duration=$(( pcap_duration + 10 ))
echo "${scriptname}: pcap duration is: ${pcap_duration} seconds"

# prepare directories
echo "${scriptname}: creating device and server directories"
mkdir -p ${data_dir_device}/${session_id}
ssh ${server_user}@${server} mkdir -p ${data_dir_server}/${session_id}/pcaps

# before the replay, start capture on client
echo "${scriptname}: starting tcpdump on device"
echo "${scriptname}: sudo tcpdump -i ${device_interface} ${protocol} portrange ${port_range} -B 4096 -G ${tcpdump_duration} -W 1 -w ${device_pcap_capture}_%Y-%m-%d_%H.%M.%S.pcap &"
sudo tcpdump -i ${device_interface} ${protocol} portrange ${port_range} -B 4096 -G ${tcpdump_duration} -W 1 -w ${device_pcap_capture}_%Y-%m-%d_%H.%M.%S.pcap &

# and start capture on server
echo "${scriptname}: starting tcpdump on server"
echo "${scriptname}: ssh ${server_user}@${server} sudo tcpdump -i ${server_interface} ${protocol} portrange ${port_range} -B 4096 -G ${tcpdump_duration} -W 1 -w ${server_pcap_capture}_%Y-%m-%d_%H.%M.%S.pcap &"
ssh ${server_user}@${server} sudo tcpdump -i ${server_interface} ${protocol} portrange ${port_range} -B 4096 -G ${tcpdump_duration} -W 1 -w ${server_pcap_capture}_%Y-%m-%d_%H.%M.%S.pcap &

echo "${scriptname}: waiting 10 seconds for tcpdump to start correct"
sleep 10

# start replay
echo "${scriptname}: starting tcpreplay"
echo "${scriptname}: sudo tcpreplay --intf1=${device_interface} ${replay_pcap}"
sudo tcpreplay --intf1=${device_interface} ${replay_pcap}

echo "${scriptname}: finished tcpreplay, waiting 30 seconds before downloading pcaps"
sleep 30

# retrieve data from server
echo "${scriptname}: retrieving pcaps from server ...."
scp ${server_user}@${server}:${server_pcap_capture}\*  ${data_dir_device}/${session_id}/
if [ "$?" = "0" ]; then
  echo "${scriptname}: stored pcap output server at ${data_dir_device}/${session_id}"
else
  echo "${scriptname}: error retrieving ${server_user}@${server}:${server_pcap_capture}\*"
  exit 1
fi

# analyse data
echo "${scriptname}: starting pcap analysis .... skipping takes to long"
# ./run_pcap_analysis.sh -s ${session_id}
