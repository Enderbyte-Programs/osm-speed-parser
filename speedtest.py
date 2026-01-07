import xml.etree.ElementTree
import json
FILE = "Vancouver.osm"

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

print("Loading data")
tree = xml.etree.ElementTree.parse(FILE)

root = tree.getroot()
print("Parsing data")

nodes:dict[int,list] = {}
all_ways:list[SpeedWay] = []

for child in root:
    if child.tag == "node":
        nodes[child.attrib["id"]] = [child.attrib["lat"],child.attrib["lon"]]

    if child.tag == "way":

        tw = SpeedWay()
        for subitem in child:
            if subitem.tag == "nd":
                tw.nodes.append(nodes[subitem.attrib["ref"]])
            if subitem.tag == "tag":
                if subitem.attrib["k"] == "name":
                    tw.name = subitem.attrib["v"]
                elif subitem.attrib["k"] == "maxspeed":
                    tw.maxspeed = parse_speed(subitem.attrib["v"])
                elif subitem.attrib["k"] == "maxspeed:conditional":
                    tw.conditional_speed = parse_speed(subitem.attrib["v"])
        if tw.maxspeed != -1:
            all_ways.append(tw)

final_list = []

for way in all_ways:
    final_list.append({
        "name" : way.name,
        "speed" : way.maxspeed,
        "conditional_speed" : way.conditional_speed,
        "nodes" : way.nodes
    })

with open("speedout.json","w+") as f:
    f.write(json.dumps(final_list))