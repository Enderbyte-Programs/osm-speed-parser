function getSpeedColour(speed) {

    if (speed == -2) {
        return 'white'
    }

    if (speed >= 120) {return 'darkred'

    } else if (speed >= 110) {return 'red'

    } else if (speed >= 100) {return 'orange'

    } else if (speed >= 90) {return 'olive'

    } else if (speed >= 80) {return 'lime'

    } else if (speed >= 70) {return 'green'

    } else if (speed >= 60) {return 'royalblue'

    } else if (speed >= 50) {return 'blue'

    } else if (speed >= 40) {return 'navy'

    } else if (speed >= 30) {return 'purple'

    } else if (speed >= 20) {

        return 'gray'

    } else {
        return 'black'
    }

}

var files = ["vancouver.json","victoria.json"]
var totalways = 0
var map = L.map('map').setView([49.3,-123.1], 12);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
}).addTo(map);

files.forEach(file => {

    fetch("/apps/speed/data/"+file).then(function(r) {
        r.text().then(function(t) {
            var items = JSON.parse(t)
            items.forEach(element => {
                totalways += 1;
                var pointList = [];
                var currentName = element.name
                var maxSpeed = element.speed
                element.nodes.forEach(node => {
                    pointList.push(new L.LatLng(node[0],node[1]))
                });

                var firstpolyline = new L.polyline(pointList, {
                    color: getSpeedColour(maxSpeed),
                    weight: 5,
                    opacity: 1,
                    smoothFactor: 1

                });
                var overtop;

                if (element.conditional_speed != -1) {
                    overtop =  new L.polyline(pointList, {
                    color: getSpeedColour(element.conditional_speed),
                    weight: 3,
                    opacity: 1,
                    smoothFactor: 1

                    })
                    firstpolyline.bindPopup(currentName + " " + maxSpeed + " km/h\n Conditional Speed: " + element.conditional_speed + " km/h")
                    overtop.bindPopup(currentName + " " + maxSpeed + " km/h\n Conditional Speed: " + element.conditional_speed + " km/h")


                } else {
                    firstpolyline.bindPopup(currentName + " " + maxSpeed + " km/h")

                }

                firstpolyline.addTo(map)

                if (overtop != undefined) {
                    overtop.addTo(map)
                }
            });

            document.getElementById("info").innerHTML = `${totalways} ways`
        })
    })
});

function showlegend() {

}