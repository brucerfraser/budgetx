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
import math
from ...F_Global_Logic import Global,Responsive,Reporting
import re

"""
Base code for later edits
"""


class Reports_mini(Reports_miniTemplate):
  def __init__(self, full_screen=False, **properties):
    self.init_components(**properties)
    self.mobile = Responsive.is_mobile()
    self.full_screen = full_screen
    if full_screen:
      self.plot_1.height = 600
      self.plot_1.interactive = True
    elif self.mobile:
      self.plot_1.height = 450
      self.plot_1.interactive = True

    start,end = Reporting.slider_date_range(0)

    # Pull compact Accounts Overview from Reporting module (dashboard mode)
    plot = Reporting.accounts_overview_plot(start, end, height=220, dashboard=True)
    self.plot_1.plot = plot
    self.plot_1.full_width = True
    