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
  
    # 2. Generate two random datasets for Account A and Account B
    # Values ranging from -ZAR200k to +ZAR500k
    data_a = [random.randint(-200000, 500000) for _ in range(12)]
    data_b = [random.randint(-200000, 500000) for _ in range(12)]
  
    # 3. Calculate the total value for the line graph
    total_value = [sum(x) for x in zip(data_a, data_b)]
  
    # 4. Create the bar traces for the two accounts
    trace_a = go.Bar(
      x=x_months,
      y=data_a,
      name='Account A',
      marker_color='#1f77b4',  # Muted blue
      hovertemplate='Account A: %{y:,.2f} ZAR'
    )
    trace_b = go.Bar(
      x=x_months,
      y=data_b,
      name='Account B',
      marker_color='#add8e6',  # Light blue
      hovertemplate='Account B: %{y:,.2f} ZAR'
    )
  
    # 5. Create the line trace for the total value
    trace_total = go.Scatter(
      x=x_months,
      y=total_value,
      name='Total Value',
      yaxis='y2',  # This line graph will use a secondary y-axis
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
      xaxis_tickangle=-45,
      xaxis_title='Month',
      yaxis=dict(
        title='Value (ZAR)',
        title_font=dict(color='#1f77b4'),
        tickformat='f'
      ),
      yaxis2=dict(
        title='Total Value (ZAR)',
        title_font=dict(color='#663399'),
        overlaying='y',
        side='right',
        tickformat='f'
      ),
      hovermode='x unified', # Show all traces on hover
      legend=dict(x=0.01, y=0.99, bgcolor='rgba(255, 255, 255, 0.7)'),
      height=500 # Set a fixed height for the plot
    )
  
    return fig
