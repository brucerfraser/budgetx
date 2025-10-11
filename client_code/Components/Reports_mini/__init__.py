from ._anvil_designer import Reports_miniTemplate
from anvil import *
import plotly.graph_objects as go
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import plotly.graph_objects as go
import random
from datetime import date, timedelta

class Reports_mini(Reports_miniTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.plot_1.figure = self.generate_graph()
    
  
  def generate_graph(self,**event_args):
    """Generates a Plotly graph with 12 months of random data."""
  
    # 1. Generate previous 12 months for the x-axis
    today = date.today()
    x_months = [(today - timedelta(days=365) + timedelta(days=30*i)).strftime('%b %Y') for i in range(12)]
  
    # Format x-axis labels to 'J-25' style
    x_months_formatted = [m[0] + '-' + m[-2:] for m in x_months]
  
    # 2. Generate two random datasets for Account A and Account B
    # Values ranging from -ZAR200k to +ZAR500k
    data_a = [random.randint(-200000, 500000) for _ in range(12)]
    data_b = [random.randint(-200000, 500000) for _ in range(12)]
  
    # 3. Calculate the total value for the line graph
    total_value = [sum(x) for x in zip(data_a, data_b)]

    for i in range(0,12):
      print(data_a[i],data_b[i],total_value[i])
  
    # 4. Create the bar traces for the two accounts
    trace_a = go.Bar(
      x=x_months_formatted,
      y=data_a[6:12],
      name='Account A',
      marker_color='#1f77b4',  # Muted blue
      hovertemplate='Account A: %{y:,.2f} ZAR'
    )
    trace_b = go.Bar(
      x=x_months_formatted,
      y=data_b[6:12],
      name='Account B',
      marker_color='#add8e6',  # Light blue
      hovertemplate='Account B: %{y:,.2f} ZAR'
    )
  
    # 5. Create the line trace for the total value, now using the primary y-axis
    trace_total = go.Scatter(
      x=x_months_formatted,
      y=total_value[6:12],
      name='Total Value',
      mode='lines+markers',
      line=dict(color='#663399', width=3), # Deep purple
      hovertemplate='Total: %{y:,.2f} ZAR'
    )
  
    # 6. Combine traces into a figure
    fig = go.Figure(data=[trace_a, trace_b, trace_total])
  
    # 7. Customize layout and axes
    fig.update_layout(
      title='Account Performance: Last 12 Months',
      barmode='group', # Set the bars side-by-side
      showlegend=False, # Remove the legend
      xaxis=dict(
        title='Month',
        tickangle=0,
        tickfont=dict(size=10) # Set x-axis label font size
      ),
      yaxis=dict(
        title='Value (ZAR)',
        title_font=dict(size=10), # Reduce y-axis title font size
        tickfont=dict(size=10), # Reduce y-axis label font size
        tickformat='~s' # Format y-axis labels to k, M, etc.
      ),
      hovermode='x unified', # Show all traces on hover
      height=250, # Set a fixed height for the plot
      margin=dict(l=30, r=10, t=40, b=30) # Reduce margins to maximize plot area
    )
  
    return fig
