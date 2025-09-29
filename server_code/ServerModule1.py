import anvil.files
from anvil.files import data_files
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
import plotly.graph_objects as go
from anvil.tables import app_tables
import anvil.server
import anvil.plotly_templates

anvil.plotly_templates.set_default("rally_dark")

#Return the contents of the Files data table. If this table included secure data, 
#we would only want to return the data that can be user visible
@anvil.server.callable
def return_table():
  return app_tables.files.search()

@anvil.server.callable
def return_data(year):
  #Your code to process and return data goes here
  if year == "2023":
    return [
      [11342, 11673, 12684, 12933, 13782, 13001, 13532, 13776, 14609, 15076, 15663, 15989], 
      [14331, 14887, 13520, 13021, 11000, 12956, 13451, 14805, 16004, 16599, 17885, 19053]
    ]
  elif year == "2022":
    return [
      [8695, 8704, 9201, 9554, 9760, 9963, 10003, 10889, 11073, 11992, 12743, 11221], 
      [12332, 12633, 13000, 13843, 12849, 12675, 13742, 14009, 14376, 14587, 15002, 14556]
    ]
  elif year == "2021":
    return [
      [5680, 5743, 5802, 6003, 6212, 7004, 6854, 6013, 6599, 7032, 7453, 7960, 8734], 
      [7832, 7945, 8432, 8049, 8775, 9321, 9674, 9900, 10342, 11483, 11954, 12511, 12030]
    ]

@anvil.server.callable
def return_bar_charts():
  #You can use any Python plotting library on the server including Plotly Express, MatplotLib, Seaborn, Bokeh
  fig = go.Figure(
    [
      go.Bar(
        y=["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"],
        x=[13, 21, 64, 119, 94],
        orientation='h',
        name="New Users"
        ),
      go.Bar(
        y=["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"],
        x=[24, 35, 80, 250, 274],
        orientation='h',
        name="Existing Users"
      ),
    ]
  )
  
  fig.update_layout(
    barmode="stack",
  )
  return fig
