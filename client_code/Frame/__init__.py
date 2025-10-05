from ._anvil_designer import FrameTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from .Reports import Reports
from .Sales import Sales
from ..Pop_menus.csv_confirm import csv_confirm
from .Transactions import Transactions

#This is your startup form. It has a sidebar with navigation links and a content panel where page content will be added.
class Frame(FrameTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    #Present users with a login form with just one line of code:
    #anvil.users.login_with_form()
    # anvil.server.call('read_file')
    #Set the Plotly plots template to match the theme of the app
    Plot.templates.default = "rally"
    #When the app starts up, the Transactions form will be added to the page
    self.load_transactions()
    # self.content_panel.add_component(Sales())
    #Change the color of the sales_page_link to indicate that the Sales page has been selected
    # self.sales_page_link.background = app.theme_colors['Primary Container']
    

  def sales_page_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    #Clear the content panel and add the Sales Form
    self.content_panel.clear()
    self.content_panel.add_component(Sales())
    #Change the color of the sales_page_link to indicate that the Sales page has been selected
    self.sales_page_link.background = app.theme_colors['Primary Container']
    self.reports_page_link.background = "transparent"

  def reports_page_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    #Clear the content panel and add the Reports Form
    self.content_panel.clear()
    self.content_panel.add_component(Reports())
    #Change the color of the sales_page_link to indicate that the Reports page has been selected
    self.reports_page_link.background = app.theme_colors['Primary Container']
    self.sales_page_link.background = "transparent"

  def load_transactions(self, **event_args):
    #Clear the content panel and add the Reports Form
    self.content_panel.clear()
    self.content_panel.add_component(Transactions())
    #Change the color of the sales_page_link to indicate that the Reports page has been selected
    self.transactions_page_link.background = app.theme_colors['Primary Container']
    self.sales_page_link.background = "transparent"
    self.reports_page_link.background = "transparent"

  #If using the Users service, uncomment this code to log out the user:
  # def signout_link_click(self, **event_args):
  #   """This method is called when the link is clicked"""
  #   anvil.users.logout()
  #   open_form('Logout')

  def file_loader_1_change(self, file, **event_args):
    acc_id, ready, raw, accounts = anvil.server.call('read_file',fn=file)
    # csv_confirm time
    result = alert(content=csv_confirm(accounts=accounts,acc_id=acc_id,ready=ready,
                                      trans=raw),
                   title="Confirm CSV Details",
                   large=True,
                   buttons=[])
    if result:
      anvil.server.call('save_transactions',ready_list=result)
    # print(result)







