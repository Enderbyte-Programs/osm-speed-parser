import sys
import os
import random
import osmium
import osmium.osm
import hashlib
import osmium.index
import typing

FILE = sys.argv[1]
TEMPID = str(random.randint(1111,9999))

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
        return f"{self.name},{self.maxspeed},{self.conditional_speed},{self.advisory_speed},{self._nodelist_tostr()}"
    
    def get_hash(self):
        return hashlib.sha256(self.format_for_output().encode("utf-8")).hexdigest()

files:dict[str,typing.TextIO] = {}
node_id_index:list[int] = []

def demand_write(way:SpeedWay):
    filepath = way.get_filestring()

    if not filepath in files:
        files[filepath] = open("output/"+filepath,"a+",encoding="utf-8")

    files[filepath].write(way.format_for_output() + "," + way.get_hash() + ",\n")

class WayHandler(osmium.SimpleHandler):
    def way(self,available:osmium.osm.Way):
        if not "maxspeed" in available.tags:
            return
        way = SpeedWay()
        way.nodes = [[p.location.lon,p.location.lat] for p in available.nodes]
        way.maxspeed = parse_speed(available.tags.get("maxspeed"))
        if "maxspeed:conditional" in available.tags:
            way.conditional_speed = parse_speed(available.tags.get("maxspeed:conditional"))
        if "maxspeed:advisory" in available.tags:
            way.conditional_speed = parse_speed(available.tags.get("maxspeed:advisory"))
        if "name" in available.tags:
            way.name = available.tags.get("name").replace(",","")
        demand_write(way)

#fp = osmium.FileProcessor(FILE).with_filter(osmium.filter.EntityFilter(osmium.osm.WAY)).with_filter(osmium.filter.KeyFilter("maxspeed"))
location_cache = osmium.index.create_map("flex_mem")
reader_wrapper = osmium.NodeLocationsForWays(location_cache)
osmium.apply(FILE,reader_wrapper,WayHandler())

for file in files.values():
    file.close()