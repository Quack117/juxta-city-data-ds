import os
import pathlib
import re

import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import numpy as np
from dash.dependencies import Input, Output, State
import requests, base64
import cufflinks as cf
from datetime import date
from datetime import timedelta

import json

# Initialize app

app = dash.Dash(
    __name__,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1.0"}
    ],
)
server = app.server

# Load data

APP_PATH = str(pathlib.Path(__file__).parent.resolve())

df_lat_lon = pd.read_csv(
    os.path.join(APP_PATH, os.path.join("data", "lat_lon_counties.csv"))
)
df_lat_lon["FIPS "] = df_lat_lon["FIPS "].apply(lambda x: str(x).zfill(5))

yesterday = (date.today() - timedelta(days=1)).strftime("%m-%d-%Y")

jhu_filepath = f'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_daily_reports/{yesterday}.csv'

df_covid_data = pd.read_csv(jhu_filepath)

df_covid_data["FIPS"] = df_covid_data["FIPS"].apply(
    lambda x: str(x).zfill(5)
)

df_covid_data = df_covid_data.rename(
    columns={'Admin2': 'County', 'Last_Update': 'Year', 'Confirmed': 'Confirmed_cases'})

df_covid_data["County"] = (
        df_covid_data["County"].map(str) + ", " + df_covid_data.County.map(str)
)


def remove_last_num(num):
    return num.strip('"')[:-15]


def remove_last2_num(num):
    return num.strip('"')[:-2]


df_covid_data["Year"] = df_covid_data["Year"].apply(remove_last_num)
df_covid_data['Year'] = df_covid_data['Year'].astype(int)
df_covid_data["County Code"] = df_covid_data["FIPS"].apply(remove_last2_num)
df_covid_data["County Code"] = df_covid_data["County Code"].replace({'00n': '0'})
df_covid_data["County Code"] = df_covid_data["County Code"].apply(
    lambda x: str(x).zfill(5)
)

YEARS = [2020]

COVID_BINS = [
    "0-100",
    "101-150",
    "151-300",
    "301-500",
    "501-1000",
    "1001-1500",
    "1501-2000",
    "2001-2500",
    "2501-5000",
    "5001-7500",
    "7501-10000",
    "10001-20000",
    "20001-30000",
    "30001-40000",
    "40001-50000",
    ">50001",
]

# COVID
DEFAULT_COLORSCALE = [
    "#ffcccc",
    "#ffb2b2",
    "#ff9999",
    "#ff7f7f",
    "#ff6666",
    "#ff4c4c",
    "#ff3232",
    "#ff1919",
    "#ff0000",
    "#ff0000",
    "#e50000",
    "#cc0000",
    "#b20000",
    "#990000",
    "#7f0000",
    "#660000",
]

DEFAULT_OPACITY = 0.8

mapbox_access_token = "pk.eyJ1IjoicGVkcm9lc2NvYmVkb2IiLCJhIjoiY2tibG4yeTMyMDlxNzJzbjhtNWRxdnR4MSJ9.Oldsna3sT8yMl8u8QK7xaQ"
# mapbox_style = "mapbox://styles/pedroescobedob/ckblnkcbo0lv81ipamqba19yr"
mapbox_style = "mapbox://styles/plotlymapbox/cjvprkf3t1kns1cqjxuxmwixz"

# App layout

app.layout = html.Div(
    id="root",
    children=[

        html.Div(
            id="header",
            children=[
                html.Img(id="logo", src="https://i.ibb.co/cXgFrRR/find-your-city-18.png", width="50%"),
                html.H4(children="Health problems in the United States"),
                html.P(
                    id="description",
                    children="Health problems listed by year and county",
                ),
            ],
        ),
        html.Div(
            id="app-container",
            children=[
                html.Div(
                    id="left-column",
                    children=[
                        html.Div(
                            id="slider-container",
                            children=[
                                html.P(
                                    id="slider-text",
                                    children="Drag the slider to change the year:",
                                ),
                                dcc.Slider(
                                    id="years-slider",
                                    min=min(YEARS),
                                    max=max(YEARS),
                                    value=max(YEARS),
                                    marks={
                                        str(year): {
                                            "label": str(year),
                                            "style": {"color": "#7fafdf"},
                                        }
                                        for year in YEARS
                                    },
                                ),
                            ],
                        ),
                        html.Div(
                            id="heatmap-container",
                            children=[
                                html.P(
                                    "Heatmap of adjusted mortality rates {0}".format(
                                        min(YEARS)
                                    ),
                                    id="heatmap-title",
                                ),
                                dcc.Graph(
                                    id="county-choropleth",
                                    figure=dict(
                                        layout=dict(
                                            mapbox=dict(
                                                layers=[],
                                                accesstoken=mapbox_access_token,
                                                style=mapbox_style,
                                                center=dict(
                                                    lat=38.72490, lon=-95.61446
                                                ),
                                                pitch=0,
                                                zoom=3.5,
                                            ),
                                            autosize=True,
                                        ),
                                    ),
                                ),
                            ],
                        ),
                    ],
                ),
                html.Div(
                    id="graph-container",
                    children=[
                        html.P(id="chart-selector", children="Select chart:"),
                        dcc.Dropdown(
                            options=[
                                {
                                    "label": "COVID-19 Value (Live Update)",
                                    "value": "Confirmed_cases",
                                },
                            ],
                            value="Confirmed_cases",
                            id="chart-dropdown",

                        ),
                        dcc.Graph(
                            id="selected-data",
                            figure=dict(
                                data=[dict(x=0, y=0)],
                                layout=dict(
                                    paper_bgcolor="#F4F4F8",
                                    plot_bgcolor="#F4F4F8",
                                    autofill=True,
                                    margin=dict(t=75, r=50, b=100, l=50),
                                ),
                            ),
                        ),
                    ],
                ),
            ],
        ),
    ],
)


# OUTPUT SELECTION FROM YEAR SELECTION

@app.callback(
    Output("county-choropleth", "figure"),
    [Input("years-slider", "value")],
    [State("county-choropleth", "figure")],
)
# DISPLAY THE MAP

def display_map(year, figure):
    # DISPLAYING BINS ON MAP WITH COLOR
    cv = dict(zip(COVID_BINS, DEFAULT_COLORSCALE))

    data = [
        dict(
            lat=df_lat_lon["Latitude "],
            lon=df_lat_lon["Longitude"],
            text=df_lat_lon["Hover"],
            type="scattermapbox",
            hoverinfo="text",
            marker=dict(size=5, color="white", opacity=0),
        )
    ]

    annotations = [
        dict(
            showarrow=False,
            align="right",
            text='<b>COVID-19 VALUES</b>',
            font=dict(color="#2cfec1"),
            bgcolor="#1f2630",
            x=0.95,
            y=0.95,
        )
    ]

    # DISPLAY THE BINS IN MAP

    for i, bin in enumerate(reversed(COVID_BINS)):
        color = cv[bin]
        annotations.append(
            dict(
                arrowcolor=color,
                text=bin,
                x=0.95,
                y=0.85 - (i / 20),
                ax=-60,
                ay=0,
                arrowwidth=5,
                arrowhead=0,
                bgcolor="#1f2630",
                font=dict(color="#2cfec1"),
            )
        )

    # POSITIONING OF MAP

    if "layout" in figure:
        lat = figure["layout"]["mapbox"]["center"]["lat"]
        lon = figure["layout"]["mapbox"]["center"]["lon"]
        zoom = figure["layout"]["mapbox"]["zoom"]
    else:
        lat = 38.72490
        lon = -95.61446
        zoom = 3.5

    # SELCTION OF COUNTIES, CONVERT INTO DICTIONARY

    layout = dict(
        mapbox=dict(
            layers=[],
            accesstoken=mapbox_access_token,
            style=mapbox_style,
            center=dict(lat=lat, lon=lon),
            zoom=zoom,
        ),
        hovermode="closest",
        margin=dict(r=0, l=0, t=0, b=0),
        annotations=annotations,
        dragmode="lasso",
    )

    # SOURCE OF MAPBOX COUNTIES GEOMETRY FIGURES

    base_url = "https://raw.githubusercontent.com/pedroescobedob/mapbox-counties/master/"
    for bin in COVID_BINS:
        geo_layer = dict(
            sourcetype="geojson",
            source=base_url + str(year) + "/" + bin + ".geojson",
            type="fill",
            color=cv[bin],
            opacity=DEFAULT_OPACITY,
            # CHANGE THIS
            fill=dict(outlinecolor="#afafaf"),
        )
        layout["mapbox"]["layers"].append(geo_layer)

    fig = dict(data=data, layout=layout)
    return fig


# RETURN VALUES FROM YEAR SLIDER

@app.callback(Output("heatmap-title", "children"), [Input("years-slider", "value")])
def update_map_title(year):
    return "Heatmap of diseases in the year {0}".format(
        year
    )


# SELECTED DATA CALLBACK

@app.callback(
    Output("selected-data", "figure"),
    [
        Input("county-choropleth", "selectedData"),
        Input("chart-dropdown", "value"),
        Input("years-slider", "value"),
    ],
)
# DISPLAY SELECTED DATA, BAR CHART ALSO ON FUNCTION

def display_selected_data(selectedData, chart_dropdown, year):
    if selectedData is None:
        return dict(
            data=[dict(x=0, y=0)],
            layout=dict(
                title="Click-drag on the map to select counties",
                paper_bgcolor="#1f2630",
                plot_bgcolor="#1f2630",
                font=dict(color="#2cfec1"),
                margin=dict(t=75, r=50, b=100, l=75),
            ),
        )

    pts = selectedData["points"]
    fips = [str(pt["text"].split("<br>")[-1]) for pt in pts]
    # fips = [str(pt["text"].split("<br>")) for pt in pts]
    for i in range(len(fips)):
        if len(fips[i]) == 4:
            fips[i] = "0" + fips[i]

    dff2 = df_covid_data[df_covid_data["County Code"].isin(fips)]
    dff2 = dff2.sort_values("Year")

    regex_pat = re.compile(r"Unreliable", flags=re.IGNORECASE)
    dff2["Confirmed_cases"] = dff2["Confirmed_cases"].replace(regex_pat, 0)

    # COVID BAR CHART
    if "Confirmed_cases" == chart_dropdown:
        dff2 = dff2[dff2.Year == year]
        title = "COVID-19"
        AGGREGATE_BY = "Confirmed_cases"

        # COVID-19 aggregate values
        dff2[AGGREGATE_BY] = pd.to_numeric(dff2[AGGREGATE_BY], errors="coerce")
        covid_values = dff2.groupby("County")[AGGREGATE_BY].sum()
        covid_values = covid_values.sort_values()

        # Only look at non-zero rows:
        covid_values = covid_values[covid_values > 0]

        fig = df_covid_data.iplot(
            kind="bar", y=AGGREGATE_BY, title=title, asFigure=True
        )

        fig_layout = fig["layout"]
        fig_data = fig["data"]

        fig_data[0]["text"] = covid_values.values.tolist()
        fig_data[0]["marker"]["color"] = "#ff0000"
        fig_data[0]["marker"]["opacity"] = 1
        fig_data[0]["marker"]["line"]["width"] = 0
        fig_data[0]["textposition"] = "outside"
        fig_layout["paper_bgcolor"] = "#1f2630"
        fig_layout["plot_bgcolor"] = "#1f2630"
        fig_layout["font"]["color"] = "#ff0000"
        fig_layout["title"]["font"]["color"] = "#ff0000"
        fig_layout["xaxis"]["tickfont"]["color"] = "#ff0000"
        fig_layout["yaxis"]["tickfont"]["color"] = "#ff0000"
        fig_layout["xaxis"]["gridcolor"] = "#5b5b5b"
        fig_layout["yaxis"]["gridcolor"] = "#5b5b5b"
        fig_layout["margin"]["t"] = 75
        fig_layout["margin"]["r"] = 50
        fig_layout["margin"]["b"] = 100
        fig_layout["margin"]["l"] = 50

        return fig

###

    fig = dff2.iplot(
        kind="area",
        x="Year",
        y='Confirmed_cases',
        text="County",
        categories="County",
        colors=[
            "#FF0000",
            "#FF0000",
            "#7570b3",
            "#e7298a",
            "#66a61e",
            "#e6ab02",
            "#a6761d",
            "#666666",
            "#1b9e77",
        ],
        vline=[year],
        asFigure=True,
    )

    for i, trace in enumerate(fig["data"]):
        trace["mode"] = "lines+markers"
        trace["marker"]["size"] = 4
        trace["marker"]["line"]["width"] = 1
        trace["type"] = "scatter"
        for prop in trace:
            fig["data"][i][prop] = trace[prop]

    # Only show first 500 lines
    fig["data"] = fig["data"][0:500]

    fig_layout = fig["layout"]

    # See plot.ly/python/reference
    fig_layout["yaxis"]["title"] = "COVID-19"
    fig_layout["xaxis"]["title"] = "County"
    fig_layout["yaxis"]["fixedrange"] = True
    fig_layout["xaxis"]["fixedrange"] = True
    fig_layout["hovermode"] = "closest"
    fig_layout["title"] = "<b>{0}</b> counties selected".format(len(fips))
    fig_layout["legend"] = dict(orientation="v")
    fig_layout["autosize"] = True
    fig_layout["paper_bgcolor"] = "#1f2630"
    fig_layout["plot_bgcolor"] = "#1f2630"
    fig_layout["font"]["color"] = "#2cfec1"
    fig_layout["xaxis"]["tickfont"]["color"] = "#2cfec1"
    fig_layout["yaxis"]["tickfont"]["color"] = "#2cfec1"
    fig_layout["xaxis"]["gridcolor"] = "#5b5b5b"
    fig_layout["yaxis"]["gridcolor"] = "#5b5b5b"

    if len(fips) > 100:
        fig["layout"][
            "title"
        ] = "Disease per county per year"

    return fig
#

if __name__ == "__main__":
    app.run_server(debug=True)
