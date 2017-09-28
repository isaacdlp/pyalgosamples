/**
 * <script src="plotlyext.js"></script>
 */

var plotId = '557d871f-57ef-4da9-8cb1-7c94b309d886';

var toggleNote = false;
var toggleDraw = false;
var drawPoints = [];

var plotDiv = document.getElementById(plotId);
var plotData = plotDiv.data;
var plotLayout = plotDiv.layout;
var plotConfig = {
    showLink: false,
    displaylogo: false,
    editable: true,
    modeBarButtonsToRemove: [
        "toggleSpikelines"
    ],
    modeBarButtonsToAdd: [
        {
            name: 'Add Annotations',
            icon: {
                width: 1600,
                path: "M1152 1248v416h-928q-40 0-68-28t-28-68v-1344q0-40 28-68t68-28h1344q40 0 68 28t28 68v928h-416q-40 0-68 28t-28 68zm128 32h381q-15 82-65 132l-184 184q-50 50-132 65v-381z",
                ascent: 1900,
                descent: 250
            },
            attr: 'notemode',
            val: "note",
            toggle: false,
            click: function(gd, ev) {
                toggleNote = !toggleNote;
                ev.currentTarget.setAttribute("data-toggle", toggleNote);
                if (toggleNote) {
                    doToggleDraw();
                }
            }
        }, {
            name: 'Add Lines',
            icon: {
                width: 1600,
                path: "M491 1536l91-91-235-235-91 91v107h128v128h107zm523-928q0-22-22-22-10 0-17 7l-542 542q-7 7-7 17 0 22 22 22 10 0 17-7l542-542q7-7 7-17zm-54-192l416 416-832 832h-416v-416zm683 96q0 53-37 90l-166 166-416-416 166-165q36-38 90-38 53 0 91 38l235 234q37 39 37 91z",
                ascent: 1900,
                descent: 250
            },
            attr: 'linemode',
            val: 'line',
            toggle: false,
            click: function(gd, ev) {
                drawPoints = [];
                toggleDraw = !toggleDraw;
                ev.currentTarget.setAttribute("data-toggle", toggleDraw);
                if (toggleDraw) {
                    doToggleNote();
                }
            }
        }, {
            name: 'Erase Additions',
            icon: {
                width: 2000,
                path: "M960 1408l336-384h-768l-336 384h768zm1013-1077q15 34 9.5 71.5t-30.5 65.5l-896 1024q-38 44-96 44h-768q-38 0-69.5-20.5t-47.5-54.5q-15-34-9.5-71.5t30.5-65.5l896-1024q38-44 96-44h768q38 0 69.5 20.5t47.5 54.5z",
                ascent: 1900,
                descent: 250
            },
            attr: 'erasemode',
            val: 'erase',
            click: function(gd, ev) {
                doToggleNote();
                doToggleDraw();
                delete plotLayout["annotations"];
                delete plotLayout["shapes"];
                Plotly.update(plotId, plotData, plotLayout);
            }
        }
    ]
};

function doToggleNote() {
    toggleNote = false;
    other = document.querySelectorAll('[data-attr="notemode"]');
    other[0].setAttribute("data-toggle", false);
}

function doToggleDraw() {
    toggleDraw = false;
    other = document.querySelectorAll('[data-attr="linemode"]');
    other[0].setAttribute("data-toggle", false);
}

Plotly.newPlot(plotId, plotData, plotLayout, plotConfig);
plotDiv.on('plotly_click', function(data){
    if (toggleNote) {
        if (!("annotations" in plotLayout)) {
            plotLayout["annotations"] = [];
        }
        dt = data.points[0];
        plotLayout["annotations"].push({
            text: 'Click to edit. Drag the text <br> or the arrow to move around.',
            x: dt.x,
            y: dt.y,
            xref: dt.xaxis._id,
            yref: dt.yaxis._id,
            showarrow: true,
            color: 'rgb(255, 0, 0)'
        });

        Plotly.update(plotId, plotData, plotLayout);
    } else if(toggleDraw) {
        dt = data.points[0];
        drawPoints.push([dt.x, dt.y, dt.xaxis._id, dt.yaxis._id]);
        if (drawPoints.length > 1) {
            if (drawPoints[0][2] == drawPoints[1][2] && drawPoints[0][3] == drawPoints[1][3]) {
                if (!("shapes" in plotLayout)) {
                    plotLayout["shapes"] = [];
                }
                plotLayout["shapes"].push({
                    type: 'line',
                    xfref: dt.xaxis._id,
                    yref: dt.yaxis._id,
                    x0: drawPoints[0][0],
                    y0: drawPoints[0][1],
                    x1: drawPoints[1][0],
                    y1: drawPoints[1][1],
                    line: {
                        width: 2,
                        opacity: 0.75,
                        dash: "dot"
                    }
                });
                Plotly.update(plotId, plotData, plotLayout);
            }
            drawPoints = [];
        }
    }
});