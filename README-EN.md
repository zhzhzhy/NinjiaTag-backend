# FindMy-tracks
Query Apple's Find My network,write into sqlite database,convert to tracks(KML/GPX etc.)

# FindMy
Query Apple's Find My network, based on all the hard work of https://github.com/seemoo-lab/openhaystack/ and @hatomist and @JJTech0130 and @Dadoum.

This is version 2, which does not require a Mac anymore thanks to the awesome work in https://github.com/JJTech0130/pypush.
Version 1 that can be run on Macs can still be found in the catalina (python2) and monterey (python3) branches.

## Installation and initial setup
Only a free Apple ID is required, with SMS 2FA properly setup. If you don't have any, follow one of the many guides found on the internet.

1. Clone this repository and `anisette-v3-server`:
```bash
git clone https://github.com/biemster/FindMy
git clone https://github.com/Dadoum/anisette-v3-server
```
2. Follow the installation instructions for `anisette-v3-server` and make sure it works.
3. Create the database where the reports will be stored:
   
```bash
 sqlite3 reports.db 'CREATE TABLE reports_detail (id_short TEXT, timestamp INTEGER,isodatetime TEXT,datePublished INTEGER,latitude REAL,longitude REAL,payload TEXT, id TEXT, statusCode INTEGER, PRIMARY KEY(id_short,timestamp))'

sqlite3 reports.db 'CREATE TABLE reports (id_short TEXT, timestamp INTEGER, datePublished INTEGER, payload TEXT, id TEXT, statusCode INTEGER, PRIMARY KEY(id_short,timestamp))'
```

## Run
1. `cd` into the `FindMy` directory and generate keys using `./generate_keys.py`.
2. Deploy your advertisement keys on devices supported by OpenHaystack. The ESP32 firmware is a mirror of the OpenHaystack binary, the Lenze 17H66 is found in many 1$ tags obtained from Ali.
An nRF51 firmware can be found here: https://github.com/dakhnod/FakeTag
3. run
```bash
../anisette-v3-server/anisette-v3-server & ./request_reports.py ; killall anisette-v3-server
```
in the same directory as your `.keys` files.

Alternatively to step 3 you could install `https://github.com/Dadoum/pyprovision` (first install `anisette-v3-server` though to get a nice D environment and the required android libs),
make a folder `anisette` in your working directory and just run
```bash
./request_reports.py
```
The script should pick up the python bindings to provision and use that instead.

This command will print json like texts include *timestamp*,*isodatetime*,*latitude*,*longitude* etc.
## convert the data to KML

*KML stands for Keyhole Markup Language. It's a file format used to display geographic data in an Earth browser, such as Google Earth, Google Maps, and various other mapping applications.*

```bash

./request_reports.py > input.txt

```
It will generate a json like file include main data of coordinate & date & time.

```bash

python3 make_kml.py

```
this script reads input.txt generated with request_reports.py and writes for each key a *.kml file

This current non-Mac workflow is not optimal yet, mainly because the anisette server is a bit of a workaround. A python solution for retrieving this is being
developed in the pypush discord, please join there if you want to contribute!
