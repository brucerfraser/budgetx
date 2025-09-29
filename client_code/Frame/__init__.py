from ._anvil_designer import FrameTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from ..Reports import Reports
from ..Sales import Sales

#This is your startup form. It has a sidebar with navigation links and a content panel where page content will be added.
class Frame(FrameTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    #Present users with a login form with just one line of code:
    #anvil.users.login_with_form()

    #Set the Plotly plots template to match the theme of the app
    Plot.templates.default = "rally"
    #When the app starts up, the Sales form will be added to the page
    self.content_panel.add_component(Sales())
    #Change the color of the sales_page_link to indicate that the Sales page has been selected
    self.sales_page_link.background = app.theme_colors['Primary Container']
    

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

  #If using the Users service, uncomment this code to log out the user:
  # def signout_link_click(self, **event_args):
  #   """This method is called when the link is clicked"""
  #   anvil.users.logout()
  #   open_form('Logout')








