# variables used by script.

# rename variabes.skel.sh to variables.sh and change the variable values


# Directories to store data files
data_dir_device="/home/fieldlabs/datadir"
data_dir_server="/home/poclab/datadir"

# Path with configuration file pcap analysis
pcap_analysis_config_file="/home/poclab/latencytests/config_pcap_analysis.js"

# Path to pcap analysis tool
pcap_analysis_app="/usr/local/pcap-analysis/index.js"

# server address
server="172.16.7.6"

# server userid
server_user="poclab"

# default replay data pcap
replay_pcap="./testdata/rewritten_data.pcap"

# default device interface
device_interface="wwan0"

# default server interface
server_interface="bond0.3501"

# default portrange
port_range="5000-5014"

# default protocol
protocol="udp"
