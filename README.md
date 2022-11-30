# replaytest

First prepare data file by rewriting source ip, destination ip, source mac and destination mac of first hop. For this the utilities `tcpprep` and `tcprewrite` can be used. To help with this the script `rewrite.sh` can be used.

```
./rewrite.sh <interface> <dest_ip> <infile.pcap> <outfile.pcap>
```
Please note this script will only work on linux based systems.

To start a data replay you can use the script to replay and analysis:
```
./replay.sh -s <session_id>
```


## install tools

Install tcpreplay.

```
brew install tcpreplay
```

Install tcpdump:
```
sudo apt update && sudo apt install tcpdump
```

## run test

Record data with tcpdump:
```
sudo tcpdump -i <interface> -w outfile.pcap
```

Before sending the data make sure the destination mac address machtes the first hop. You can rewrite the mac address using:
```
tcprewrite --infile=sample-car-file2.pcap --outfile=outfile-netgear.pcap --enet-dmac=00:a0:c6:00:00:01 --fixcsum
```

To replay the data use:
```
sudo tcpreplay --intf1=en5 outfile-netgear.pcap
```

## other options

please refer to: https://gist.github.com/niranjan-nagaraju/4532037 for more rewrite options.
