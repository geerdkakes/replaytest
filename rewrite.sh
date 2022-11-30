#!/usr/bin/env bash

if [ "$#" -ne 4 ]; then
    echo "Usage:"
    echo "$0 <interface> <dest_ip> <infile> <outfile>"
    exit 1
fi


interface="$1"
dest_ip="$2"
infile="$3"
outfile="$4"

# source address
source_ip="$(ifconfig | grep ${interface} -A6 | grep "inet " | awk '{print $2}')"

# source mac address
source_mac="$(ifconfig | grep ${interface} -A6 | grep ether | awk '{print $2}')"

# gateway address
gateway_address="$(route -n | grep ${interface} | grep -m1 UG | awk '{print $2}')"

# get destination hardware address
arp_out="$(arp -i ${interface} ${gateway_address} | grep ${interface})"

if [ "${?}" = "0" ]; then
  dest_mac="$(echo ${arp_out} |  awk '{print $3}')"
else
  dest_mac="${source_mac}"
fi

echo "interface: ${interface}"
echo "source_ip: ${source_ip}"
echo "source_mac: ${source_mac}"
echo "gateway_address: ${gateway_address}"
echo "dest_mac: ${dest_mac}"
echo "dest_ip: ${dest_ip}"
echo "infile: ${infile}"
echo "outfile: ${outfile}"
echo

read -p "Continue to rewrite? (y/N) " yn

case $yn in
	y ) echo "rewriting..."
      echo "preparing cache file ${infile}.cache"
      echo "# tcpprep --auto=first --pcap=${infile} --cachefile=${infile}.cache"
      tcpprep --auto=first --pcap=${infile} --cachefile=${infile}.cache
      echo ""
      echo "rewriting to ${outfile}"
      echo "# tcprewrite --endpoints=${source_ip}:${dest_ip} --enet-smac=${source_mac} --enet-dmac=${dest_mac} -i ${infile} -o ${outfile} --cachefile=${infile}.cache"
      tcprewrite --endpoints=${source_ip}:${dest_ip} --enet-smac=${source_mac} --enet-dmac=${dest_mac} -i ${infile} -o ${outfile} --cachefile=${infile}.cache
      echo "done"
      ;;
	n ) echo "stopping...."
		  ;;
esac


