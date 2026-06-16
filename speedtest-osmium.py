#type:ignore
import sys
import os
import threading
import osmium
import osmium.osm
import osmium.index
import typing
import time
import argparse
import platform

parser = argparse.ArgumentParser("speedtest-osmium.py")
parser.add_argument("-a","--append",action="store_true",help="Add to way lists instead of overwriting them",required=False)
parser.add_argument("-d","--diskcache",action="store_true",help="Cache nodes on the disk instead of in memory")
parser.add_argument("filename",action="store",type=str)
args = parser.parse_args(sys.argv[1:])

FILE = args.filename
ISFINISHED = False
start_time = time.time()
ways_found = 0
append_to_file = args.append
location_storage_implementation = "sparse_file_array,nodes.db" if args.diskcache else "flex_mem"

if not FILE.endswith("osm") and not FILE.endswith("pbf"):
    print("bad filetype")
    sys.exit(-1)

os.makedirs("output",exist_ok=True)

def parse_speed(i:str) -> int:
    try:
        return int(i)
    except:
        #Try  mph or  kph
        if "kmh" in i or "kph" in i:
            return int(i.split(" ")[0])
        
        elif "mih" in i or "mph" in i:
            return round(int(i.split(" ")[0]) * 1.6,-1)
        
        else:
            try:
                return int(i.split(" ")[0])
            except:
                return -2#Unparseable

class SpeedWay:
    def __init__(self):
        self.nodes:list[list[int]] = []
        self.maxspeed:int = -1
        self.conditional_speed = -1
        self.advisory_speed = -1
        self.name:str = "Unnamed Way"

    def get_filestring(self):
        return f"{round(self.nodes[0][0],1)}_{round(self.nodes[0][1],1)}.txt"
    
    def _nodelist_tostr(self):
        return "&".join([f"{z[0]}*{z[1]}" for z in self.nodes])
    
    def format_for_output(self):
        return f"{self.name},{self.maxspeed},{self.conditional_speed},{self.advisory_speed},{self._nodelist_tostr()}\n"

files:dict[str,""] = {}
node_id_index:list[int] = []

def demand_write(way:SpeedWay):
    filepath = way.get_filestring()

    if not filepath in files:
        files[filepath] = ""

    files[filepath] += way.format_for_output()

def progress_thread():
    time.sleep(1)
    while not ISFINISHED:
        tdelta = time.time() - start_time
        print(f"{ways_found} in {round(tdelta)}s ({round(ways_found/tdelta)} ways/s)",end="\r")
        time.sleep(1)
class WayHandler(osmium.SimpleHandler):
    def way(self,available:osmium.osm.Way):
        global ways_found
        if not "maxspeed" in available.tags:
            return
        way = SpeedWay()
        way.nodes = [[p.location.lat,p.location.lon] for p in available.nodes]
        way.maxspeed = parse_speed(available.tags.get("maxspeed"))
        if "maxspeed:conditional" in available.tags:
            way.conditional_speed = parse_speed(available.tags.get("maxspeed:conditional"))
        if "maxspeed:advisory" in available.tags:
            way.advisory_speed_speed = parse_speed(available.tags.get("maxspeed:advisory"))
        if "name" in available.tags:
            way.name = available.tags.get("name").replace(",","")
        ways_found += 1
        demand_write(way)

#fp = osmium.FileProcessor(FILE).with_filter(osmium.filter.EntityFilter(osmium.osm.WAY)).with_filter(osmium.filter.KeyFilter("maxspeed"))
location_cache = osmium.index.create_map(location_storage_implementation)
reader_wrapper = osmium.NodeLocationsForWays(location_cache)
print("Loading nodes. Please wait...")
threading.Thread(target=progress_thread).start()
osmium.apply(FILE,reader_wrapper,WayHandler())

print("\n\nWriting out...")
ISFINISHED = True

wocount = 0
for file in files:
    if append_to_file:
        with open("output/"+file,"a+") as f:
            f.write(files[file])
    else:
        with open("output/"+file,"w+") as f:
            f.write(files[file])

    wocount += 1

print(f"Wrote {wocount} files out.")
print("Completed")