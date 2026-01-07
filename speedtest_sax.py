import xml.sax
import json
FILE = r"ingress.osm"

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
        self.name:str = "Unnamed Way"

nodes:dict[int,list] = {}
all_ways:list[SpeedWay] = []

class OSMHandler(xml.sax.ContentHandler):
    def __init__(self):
        self.current_element = ""
        self.current_way = SpeedWay()
        self.is_on_way_mode = False
        self.current_way_is_hwy = False

    # Called when an element starts
    def startElement(self, tag, attrib):
        global nodes
        global all_ways
        self.current_element = tag
        if tag == "node":
            nodes[attrib["id"]] = [attrib["lat"],attrib["lon"]]

        if tag == "way":
            self.current_way = SpeedWay()
            self.is_on_way_mode = True
            self.current_way_is_hwy = False
        if tag == "nd":
            self.current_way.nodes.append(nodes[attrib["ref"]])
        if tag == "tag":
            if attrib["k"] == "name":
                self.current_way.name = attrib["v"]
            elif attrib["k"] == "maxspeed":
                self.current_way.maxspeed = parse_speed(attrib["v"])
            elif attrib["k"] == "maxspeed:conditional":
                self.current_way.conditional_speed = parse_speed(attrib["v"])
            elif attrib["k"] == "highway":
                self.current_way_is_hwy = True
            

    # Called when an element ends
    def endElement(self, tag):
        global all_ways
        if self.current_way.maxspeed != -1 and self.is_on_way_mode and tag == "way" and self.current_way_is_hwy:
            print(self.current_way.name,end=" ")
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
        "nodes" : way.nodes
    })

with open("output.json","w+") as f:

    f.write(json.dumps(final_list))
