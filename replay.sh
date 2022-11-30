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

# prepare directories
mkdir -p ${data_dir_device}/${session_id}
ssh ${server_user}@${server} mkdir -p ${data_dir_server}/${session_id}/pcaps

# before the replay, start capture on client
sudo tcpdump -i ${device_interface} ${protocol} portrange ${port_range} -B 4096 -G ${duration} -W 1 -w ${device_pcap_capture}_%Y-%m-%d_%H.%M.%S.pcap &

# and start capture on server
ssh ${server_user}@${server} sudo tcpdump -i ${server_interface} ${protocol} portrange ${port_range} -B 4096 -G ${duration} -W 1 -w ${server_pcap_capture}_%Y-%m-%d_%H.%M.%S.pcap &

sleep 5

# start replay
sudo tcpreplay --intf1=${device_interface} ${replay_pcap}

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
