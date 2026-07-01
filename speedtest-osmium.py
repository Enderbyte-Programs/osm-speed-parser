#type:ignore
import sys
import os
import threading
import osmium
import osmium.osm
import osmium.index
import osmium.filter
import time
import argparse
import datetime
import copy

parser = argparse.ArgumentParser("speedtest-osmium.py")
parser.add_argument("-a","--append",action="store_true",help="Add to way lists instead of overwriting them",required=False)
parser.add_argument("-d","--diskcache",action="store_true",help="Cache nodes on the disk instead of in memory",required=False)
parser.add_argument("-q","--quiet",action="store_true",help="If enabled, the program will produce no output except for errors",required=False)
parser.add_argument("-f","--frequency",action="store",type=float,default=1.0,required=False,help="The frequency to receive status updates at in Hz")
parser.add_argument("-g","--graph",action="store_true",required=False,help="Use ncurses to display a detailed graph about the throughput of the application")
parser.add_argument("filename",action="store",type=str)
args = parser.parse_args(sys.argv[1:])

FILE:str = args.filename
ISFINISHED = False
start_time = time.time()
ways_found = 0
append_to_file:bool = args.append
quiet:bool = args.quiet
updatefrequency:float = args.frequency
location_storage_implementation = "sparse_file_array,nodes.db" if args.diskcache else "flex_mem"
use_ncurses:bool = args.graph

if use_ncurses:
    import curses

if (use_ncurses and quiet):
    raise ValueError("Quiet was requested, but so was detailed status. Make up your mind.")

oneminute_tracker:list[int] = [1] * int(60 * updatefrequency)
fiveminute_tracker:list[int] = [1] * int(60 * 5 * updatefrequency)
fifteenminute_tracker:list[int] = [1] * int(60 * 15 * updatefrequency)

if not FILE.endswith("osm") and not FILE.endswith("pbf"):
    print("bad filetype")
    sys.exit(-1)

os.makedirs("output",exist_ok=True)

def parse_speed(i:str) -> int:
    try:
        return int(i)
    except:
        #Try  mph or  kph
        try:
            if "kmh" in i or "kph" in i:
                if " " in i.strip():
                    return round(float(i.split(" ")[0]))
                else:
                    return round(float(i.strip().replace("kph","").replace("kmh","")))
            
            elif "mih" in i or "mph" in i:
                if " " in i.strip():
                    return round(float(i.split(" ")[0]) * 1.6,-1)
                else:
                    return round(float(i.strip().replace("mph","").replace("mih","")) * 1.6,-1)
            
            else:
                try:
                    return round(float(i.split(" ")[0]))
                except:
                    return -2#Unparseable
        except:
            return -2#Other formatting error

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
node_id_index:list[int] = [0] * 1000

def demand_write(way:SpeedWay):
    filepath = way.get_filestring()

    if not filepath in files:
        files[filepath] = ""

    files[filepath] += way.format_for_output()

def ncurses_progress_thread(stdscr):
    last_wayvalue = 0
    time.sleep(1/updatefrequency)
    minutes = [1] * 1000
    tick = 0
    curses.start_color()
    curses.init_pair(1,curses.COLOR_RED,curses.COLOR_BLACK)
    curses.init_pair(2,curses.COLOR_GREEN,curses.COLOR_BLACK)
    while not ISFINISHED:
        try:
            tick += 1
            if tick == 60:
                minutes.append(sum(oneminute_tracker))
                minutes.pop(0)
                tick = 0

            stdscr.clear()
            tdelta = datetime.timedelta(seconds=(int(time.time()) - int(start_time)))
            delta = ways_found - last_wayvalue
            oneminute_tracker.pop(0)
            oneminute_tracker.append(delta)
            fiveminute_tracker.pop(0)
            fiveminute_tracker.append(delta)
            fifteenminute_tracker.pop(0)
            fifteenminute_tracker.append(delta)

            oneminute_throughput = round(sum(oneminute_tracker)/60)
            fiveminute_throughput = round(sum(fiveminute_tracker)/(60 * 5))
            fifteenminute_throughput = round(sum(fifteenminute_tracker )/ (60 * 15))
            overall_throughput = round(ways_found / tdelta.total_seconds())

            #mx,my = os.get_terminal_size()
            my,mx = stdscr.getmaxyx()
            mx -= 1
            my -= 1
            available_rows_for_writing = my - 3
            graph_y_space = available_rows_for_writing // 2
            secondly_graph_y_start = 3
            minutely_graph_y_start = 3 + graph_y_space
            
            selected_secondly_data = fifteenminute_tracker[-mx:]
            selected_minutely_data = minutes[-mx:]
            secondly_yincrement = max(selected_secondly_data) / graph_y_space
            minutely_yincrement = max(selected_minutely_data) / graph_y_space
            secondly_average_block_limit = int((overall_throughput) / max(selected_secondly_data) * graph_y_space)
            minutely_average_block_limit = int((overall_throughput * 60) / max(selected_minutely_data) * graph_y_space)

            stdscr.addstr(0,0,f"{str(tdelta)} - Found a total of {ways_found} ways. All average: {overall_throughput} w/s. Last tick: {delta} processed")
            stdscr.addstr(1,0,f"1m: {oneminute_throughput} w/s | 5m: {fiveminute_throughput} w/s | 15m: {fifteenminute_throughput} w/s")
            stdscr.addstr(2,0,"─"*mx)
            stdscr.addstr(2,0,"Top: secondly throughput. Bottom: Minutely throughput")

            wtick = 0

            while wtick < mx:

                selsec = selected_secondly_data[wtick]
                btick = 0
                remaining_blocks = selsec / max(selected_secondly_data) * graph_y_space
                while remaining_blocks > 0:
                    if btick <= secondly_average_block_limit:
                        stdscr.addstr((secondly_graph_y_start + graph_y_space) - btick,wtick,"█",curses.color_pair(1))
                    else:
                        stdscr.addstr((secondly_graph_y_start + graph_y_space) - btick,wtick,"█",curses.color_pair(2))
                    remaining_blocks -= 1
                    btick += 1

                selmin = selected_minutely_data[wtick]
                btick = 0
                remaining_blocks = selmin / max(selected_minutely_data) * graph_y_space
                while remaining_blocks > 0:
                    if btick <= minutely_average_block_limit:
                        stdscr.addstr((minutely_graph_y_start + graph_y_space) - btick,wtick,"█",curses.color_pair(1))
                    else:
                        stdscr.addstr((minutely_graph_y_start + graph_y_space) - btick,wtick,"█",curses.color_pair(2))
                    remaining_blocks -= 1
                    btick += 1

                wtick += 1

            stdscr.refresh()
        except:
            pass#Ignore curses error
        last_wayvalue = copy.copy(ways_found)
        time.sleep(1/updatefrequency)

def progress_thread():
    time.sleep(1/updatefrequency)
    if use_ncurses:
        curses.wrapper(ncurses_progress_thread)
    else:
        time.sleep(1/updatefrequency)
        last_wayvalue = 0
        while not ISFINISHED:
            tdelta = datetime.timedelta(seconds=(int(time.time()) - int(start_time)))
            delta = ways_found - last_wayvalue
            oneminute_tracker.pop(0)
            oneminute_tracker.append(delta)
            fiveminute_tracker.pop(0)
            fiveminute_tracker.append(delta)
            fifteenminute_tracker.pop(0)
            fifteenminute_tracker.append(delta)

            print(f"{str(tdelta)} | Total: {ways_found} | Δ = {delta} | 1m: {round(sum(oneminute_tracker)/len(oneminute_tracker))} w/s | 5m: {round(sum(fiveminute_tracker)/len(fiveminute_tracker))} w/s | 15m: {round(sum(fifteenminute_tracker)/len(fifteenminute_tracker))} w/s | All: {round(ways_found/tdelta.total_seconds())} w/s",end="\r")

            last_wayvalue = copy.copy(ways_found)
            time.sleep(1/updatefrequency)

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
            way.advisory_speed = parse_speed(available.tags.get("maxspeed:advisory"))
        if "name" in available.tags:
            way.name = available.tags.get("name").replace(",","")
        ways_found += 1
        demand_write(way)

#fp = osmium.FileProcessor(FILE).with_filter(osmium.filter.EntityFilter(osmium.osm.WAY)).with_filter(osmium.filter.KeyFilter("maxspeed"))
location_cache = osmium.index.create_map(location_storage_implementation)
reader_wrapper = osmium.NodeLocationsForWays(location_cache)

if not quiet:
    print("Loading nodes. Please wait...")
    threading.Thread(target=progress_thread).start()


try:
    osmium.apply(FILE,osmium.filter.KeyFilter("maxspeed").enable_for(osmium.osm.WAY),reader_wrapper,WayHandler())
except Exception as e:
    ISFINISHED = True
    print("Processing aborted due to error")
    raise
if not quiet:
    print("\n\nWriting out...")
ISFINISHED = True

wocount = 0
for file in files:
    if append_to_file:
        with open("output/"+file,"a+",encoding="utf-8") as f:
            f.write(files[file])
    else:
        with open("output/"+file,"w+",encoding="utf-8") as f:
            f.write(files[file])

    wocount += 1

if not quiet:
    print(f"Wrote {wocount} files out.")
    print("Completed")
