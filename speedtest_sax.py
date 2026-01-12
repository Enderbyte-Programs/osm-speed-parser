import xml.sax
import json
import io
import sys
import os
import random
FILE = sys.argv[1]
TEMPID = str(random.randint(1111,9999))

if not FILE.endswith("osm"):
    print("Converting")
    os.system(f"osmconvert.exe {FILE} --out-osm -o=\"temp{TEMPID}.osm\"")
    print("Filtering")
    os.system(f"osmfilter.exe temp{TEMPID}.osm --keep=\"maxspeed\" -o=\"{TEMPID}ready.osm\"")
    FILE = f"{TEMPID}ready.osm"

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

def coordinate_to_bytes(coord:float) -> bytes:
    return int(coord * 10 ** 7).to_bytes(signed=True,length=4)

def bytes_to_coordinate(coord:bytes) -> float:
    return int.from_bytes(coord,signed=True) / 10 ** 7

class SpeedWay:
    def __init__(self):
        self.nodes:list[list[int]] = []
        self.maxspeed:int = -1
        self.conditional_speed = -1
        self.advisory_speed = -1
        self.name:str = "Unnamed Way"

all_ways:list[SpeedWay] = []
node_id_index:list[int] = []

class OSMHandler(xml.sax.ContentHandler):
    def __init__(self):
        self.current_element = ""
        self.current_way = SpeedWay()
        self.is_on_way_mode = False
        self.current_way_is_hwy = False
        self.node_file = io.BytesIO()
        self.nodeincrement = 0
        self.found_ways = 0

    # Called when an element starts
    def startElement(self, tag, attrib):
        global node_id_index
        global all_ways
        self.current_element = tag
        
        if tag == "node":
            nodeid = int(attrib["id"])
            node_id_index.append(nodeid)
            notelat = float(attrib["lat"])
            notelon = float(attrib["lon"])
            self.node_file.write(coordinate_to_bytes(notelat))
            self.node_file.write(coordinate_to_bytes(notelon))

        if tag == "way":
            self.current_way = SpeedWay()
            self.is_on_way_mode = True
            self.current_way_is_hwy = False
        if tag == "nd":
            nl = [0,0]
            seekid = int(attrib["ref"])
            location = node_id_index.index(seekid)
            self.node_file.seek(location*8,0)
            nl[0] = bytes_to_coordinate(self.node_file.read(4))
            nl[1] = bytes_to_coordinate(self.node_file.read(4))
            self.current_way.nodes.append(nl)
        if tag == "tag":
            if attrib["k"] == "name":
                self.current_way.name = attrib["v"]
            elif attrib["k"] == "maxspeed":
                self.current_way.maxspeed = parse_speed(attrib["v"])
            elif attrib["k"] == "maxspeed:conditional":
                self.current_way.conditional_speed = parse_speed(attrib["v"])
            elif attrib["k"] == "maxspeed:advisory":
                self.current_way.advisory_speed = parse_speed(attrib["v"])
            elif attrib["k"] == "highway":
                self.current_way_is_hwy = True
            

    # Called when an element ends
    def endElement(self, tag):
        global all_ways
        if self.current_way.maxspeed != -1 and self.is_on_way_mode and tag == "way" and self.current_way_is_hwy:
            sys.stdout.write(self.current_way.name+" ")
            sys.stdout.flush()
            self.found_ways += 1
            #print(self.found_ways,end="\r")
            all_ways.append(self.current_way)

parser = xml.sax.make_parser()
parser.setContentHandler(OSMHandler())
print("Parsing data")
parser.parse(FILE)

final_list = []

for way in all_ways:
    final_list.append({
        "name" : way.name,
        "speed" : way.maxspeed,
        "conditional_speed" : way.conditional_speed,
        "advisory_speed" : way.advisory_speed,
        "nodes" : way.nodes
    })

with open(sys.argv[2],"w+") as f:
    f.write(json.dumps(final_list))