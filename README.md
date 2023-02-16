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

or download and compile by hand, e.g.:
```
wget https://github.com/appneta/tcpreplay/releases/download/v4.4.2/tcpreplay-4.4.2.tar.xz
tar -xf tcpreplay-4.4.2.tar.xz
cd tcpreplay-4.4.2
./configure
make
sudo make install
```

Install tcpdump:
```
sudo apt update && sudo apt install tcpdump
```

Install wireshark tools:
```
sudo apt install wireshark-common
```

Install pcap-analysis
```
git clone https://github.com/geerdkakes/pcap-analysis.git
cd pcap-analysis
npm install
```

Copy the file `variables.sh.skel` to `variables.sh` and change the values (e.g. file paths, server address, userid's, etc). Also if using the `replay.sh` script this tries to login to the server via ssh and perform sudo commands. You should enable login via ssh public key and enable sudo without the need of a passwd.


## run test

Before doing a replaytest the source ip, destination ip and source mac and destination mac address need to be changed. This can be done using the script `rewrite.sh`

```
./rewrite.sh <interface> <dest_ip> <infile.pcap> <outfile.pcap>
```

After this a test can be done via the script included. Make sure to update the `variables.sh` file so the pcap data filename is correct.
```
./replay.sh -s <session_id>
```

Another way to run the test is doing it wihout the `replay.sh` script:



Record data with tcpdump:
```
sudo tcpdump -i <interface> -w outfile.pcap
```

Before sending the data make sure the destination mac address machtes the first hop. You can rewrite the mac address using:
```
tcprewrite --endpoints=<sourceip>:<destinationip> --enet-smac=<sourcemac> --enet-dmac=<destinationmac> -i <inpcapfile> -o <outpcapfile> --cachefile=<cachefilename>
```
The cache filename can be anything, will be created by tcprewrite and can be removed after the output pcap file is created.


To replay the data use:
```
sudo tcpreplay --intf1=<network interface> <pcap filename>
```

In order to analysis latencies between source and destination system, the time must be synchronized between the systems and pcap's recorded on both systems. After they can be compared using the `pcap-analysis` tool.

To record pcaps:

```
sudo tcpdump -i <networkinterface> <protocol> port <port> -w <filename>
```


## other options

please refer to: https://gist.github.com/niranjan-nagaraju/4532037 for more rewrite options.
