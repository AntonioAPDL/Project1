from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from bokeh.plotting import figure
from bokeh.embed import file_html
from bokeh.resources import INLINE
from bokeh.models import ColumnDataSource, Span, Label
from bokeh.models.formatters import DatetimeTickFormatter
from datetime import datetime, timedelta
import requests
import math

app = FastAPI()

# Constants
CFSToCMS_CONVERSION_FACTOR = 0.0283168466
USGS_API_URL = "https://waterservices.usgs.gov/nwis/iv/"
PARAMS = {"sites": "11160500", "parameterCd": "00060", "format": "json"}
PALETTE = {"historical": "#7570b3", "real_time": "#1b9e77", "flood_stage": "#d95f02"}


# Function to fetch data from USGS
def fetch_usgs_data(start_date=None, end_date=None):
    """
    Fetch river discharge data from the USGS API.
    Args:
        start_date (str): Start date in YYYY-MM-DD format.
        end_date (str): End date in YYYY-MM-DD format.
    Returns:
        list: [(datetime, discharge_log)]
    """
    try:
        params = PARAMS.copy()
        if start_date and end_date:
            params["startDT"] = start_date
            params["endDT"] = end_date

        response = requests.get(USGS_API_URL, params=params, timeout=10)
        response.raise_for_status()
        json_data = response.json()

        time_series = json_data["value"]["timeSeries"][0]["values"][0]["value"]
        return [
            (
                datetime.strptime(entry["dateTime"][:19], "%Y-%m-%dT%H:%M:%S"),
                math.log(float(entry["value"]) * CFSToCMS_CONVERSION_FACTOR + 1),
            )
            for entry in time_series
            if "value" in entry
        ]
    except Exception as e:
        raise RuntimeError(f"Error fetching USGS data: {str(e)}")


# Home route
@app.get("/", response_class=HTMLResponse)
def home():
    """
    Welcome page with API usage instructions.
    """
    return """
        <h1>San Lorenzo River Discharge API</h1>
        <p>Explore real-time and historical river discharge data for the San Lorenzo River.</p>
        <ul>
            <li><a href="/plot">View Discharge Plot</a></li>
        </ul>
    """


# Plot route
@app.get("/plot", response_class=HTMLResponse)
def plot_discharge():
    """
    Generate and display a plot of river discharge.
    """
    try:
        # Fetch data
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        historical_data = fetch_usgs_data(start_date, end_date)
        real_time_data = fetch_usgs_data()

        if not (historical_data or real_time_data):
            return HTMLResponse("<h1>No data available.</h1>")

        # Separate timestamps and discharge values
        timestamps_hist, discharge_hist = zip(*historical_data) if historical_data else ([], [])
        timestamps_real, discharge_real = zip(*real_time_data) if real_time_data else ([], [])

        # Define the range for y-axis (log scale)
        y_min = 0  # Set the minimum log-discharge value
        y_max = 9 # Adjust for data
        y_range = (y_min, y_max)

        # Create Bokeh plot
        plot = figure(
            title=" ",
            x_axis_label="Date (mm/dd/yyyy)",
            y_axis_label="Log(Discharge + 1) (ft/s)",
            x_axis_type="datetime",
            y_range=y_range,  # Set y-axis range
            width=630,
            height=730,
            toolbar_location="above",
            background_fill_color="#f7f7f7",
        )

        plot.xaxis.formatter = DatetimeTickFormatter(days="%m/%d/%Y", months="%m/%d/%Y", years="%m/%d/%Y")
        plot.xaxis.major_label_orientation = 0.75  # Slight tilt for readability
        plot.title.text_font_size = "16pt"
        plot.axis.axis_label_text_font_size = "12pt"
        plot.axis.major_label_text_font_size = "10pt"

        # Add historical data
        if timestamps_hist:
            plot.line(
                timestamps_hist,
                discharge_hist,
                line_width=1,
                color=PALETTE["historical"],
                legend_label="Historical Data",
            )
            plot.circle(
                timestamps_hist,
                discharge_hist,
                size=2,
                color=PALETTE["historical"],
                legend_label="Historical Data",
            )

        # Add real-time data
        if timestamps_real:
            plot.line(
                timestamps_real,
                discharge_real,
                line_width=1,
                color=PALETTE["real_time"],
                legend_label="Real-Time Data",
            )
            plot.circle(
                timestamps_real,
                discharge_real,
                size=10,
                color=PALETTE["real_time"],
                legend_label="Real-Time Data",
            )

        # Add flood stages
        flood_stages = {
            "Minor Flooding (16.5 ft)": 16.5,
            "Major Flooding (21.76 ft)": 21.76,
        }
        for stage_name, feet in flood_stages.items():
            log_stage = math.log(feet / CFSToCMS_CONVERSION_FACTOR + 1)
            span = Span(
                location=log_stage,
                dimension="width",
                line_color=PALETTE["flood_stage"],
                line_dash="dashed",
                line_width=1,
            )
            plot.add_layout(span)
            label = Label(
                x=timestamps_hist[0] if timestamps_hist else datetime.now(),
                y=log_stage,
                text=stage_name,
                text_color=PALETTE["flood_stage"],
                text_font_size="10pt",
            )
            plot.add_layout(label)

        # Customize legend
        plot.legend.title = "Streamflow"
        plot.legend.title_text_font_size = "12pt"
        plot.legend.label_text_font_size = "10pt"
        plot.legend.location = "top_left"
        plot.legend.background_fill_alpha = 0.6

        # Return HTML response
        return HTMLResponse(file_html(plot, INLINE))
    except Exception as e:
        return HTMLResponse(f"<h1>Error: {str(e)}</h1>")
