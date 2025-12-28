from ._anvil_designer import SettingsTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from ... import Global


class Settings(SettingsTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.item['dash_variances'] = app_tables.settings.get(id='budget')['dash_variances']
    self.init_components(**properties)
    self.item['category_list'] = app_tables.settings.get(id='budget')['dash_var_top_five']
    names_list = sorted(list(map(lambda x: x['display'], Global.CATEGORIES.values())))
    self.autocomplete_1.suggestions = names_list
    self.account = {}
    self.changed = False
    self.repeating_panel_2.set_event_handler('x-account-clicked',self.choose_account)
    self.rp_autokeys.set_event_handler('x-changed',self.edit_and_change)
    self.rp_autokeys.set_event_handler('x-pressed-enter',self.add_an_auto)
    self.rp_autokeys.set_event_handler('x-delete-key',self.delete_a_key)
    self.rp_csvkeys.set_event_handler('x-changed',self.edit_and_change)
    self.refresh_data_bindings()
    


  def category_choose(self,**event_args):
    cat_id = next((k for k, v in Global.CATEGORIES.items() if v.get('display') == self.autocomplete_1.text), None)
    self.item['category_list'].append({'name':self.autocomplete_1.text,'cat_id':cat_id})
    self.autocomplete_1.text = ''
    if len(self.item['category_list']) > 5:
      self.item['category_list'].pop(0)
    app_tables.settings.get(id='budget')['dash_var_top_five'] = self.item['category_list']
    self.refresh_data_bindings()

  def switch_1_change(self, **event_args):
    app_tables.settings.get(id='budget')['dash_variances'] = self.switch_1.checked
    self.refresh_data_bindings()

  @handle("", "show")
  def form_show(self, **event_args):
    self.repeating_panel_2.items = Global.ACCOUNTS_WHOLE
    self.cp_account_details.visible = False
    self.btn_edit.enabled = False
    self.btn_delete.enabled = False

  def choose_account(self,acc_id,**event_args):
    self.account = acc_id
    if acc_id:
      print(acc_id)
      self.work_account("load")
      self.cp_account_details.visible = True
      for l in self.repeating_panel_2.get_components():
        l.chosen(acc_id['acc_id']==l.item['acc_id'])
      self.btn_edit.enabled = True
      self.btn_delete.enabled = True
    else:
      print(acc_id)
      self.cp_account_details.visible = False
      for l in self.repeating_panel_2.get_components():
        l.chosen(False)
      self.btn_edit.enabled = False
      self.btn_delete.enabled = False

  @handle('btn_edit','click')
  def work_account(self,edit_del_load="edit",**event_args):
    if edit_del_load == "load":
      self.txt_acc_name.text = self.account['acc_name']
      self.rp_autokeys.items = self.account['acc_keywords']
      self.rp_csvkeys.items = [{'key':k,'value':v} for k,v in self.account['key_map'].items()]
      self.enable_accounts(False)
    elif edit_del_load == "edit":
      if event_args['sender'].text == "EDIT":
        self.enable_accounts(True)
        self.changed = False
        self.btn_edit.text = "SAVE"
      elif event_args['sender'].text == "SAVE":
        if self.changed:
          map = {}
          for obj in self.rp_csvkeys.get_components():
            map[obj.item['key']] = obj.item['value']
          auto_list = []
          for obj in self.rp_autokeys.get_components():
            if len(obj.text_box_1.text) > 2 and obj.text_box_1.placeholder == 'New auto-word':
              auto_list.append(obj.text_box_1.text)
            elif obj.text_box_1.placeholder == '':
              auto_list.append(obj.text_box_1.text)
          upload = {'acc_name':self.txt_acc_name.text,
                    'acc_keywords':auto_list,
                   'key_map':map,'acc_id':self.account['acc_id']}
          anvil.server.call('update_account',upload)
          for a in Global.ACCOUNTS_WHOLE:
            if a['acc_id'] == upload['acc_id']:
              a.update(**upload)
              break
          self.changed = False
        self.btn_edit.text = "EDIT"
        self.enable_accounts(False,True)
        self.work_account('load')

  def enable_accounts(self,enabled,save=False,**event_args):
    self.txt_acc_name.enabled = enabled
    if enabled:
      l = self.rp_autokeys.items
      l.insert(0,'')
      self.rp_autokeys.items = l
      self.rp_autokeys.get_components()[0].text_box_1.placeholder = 'New auto-word'
    else:
      if save:
        # we need to gt rid of inserted item in list
        l = self.rp_autokeys.items
        l.pop(0)
        self.rp_autokeys.items = l
    for row in self.rp_autokeys.get_components():
      row.text_box_1.enabled = enabled
      row.btn_del_key.enabled = enabled
    for row in self.rp_csvkeys.get_components():
      row.text_box_1.enabled = enabled

  @handle('txt_acc_name','change')
  def edit_and_change(self,caller=None,**event_args):
    self.changed = True
    if not caller:
      for k in self.repeating_panel_2.get_components():
        if k.item['acc_id'] == self.account['acc_id']:
          k.link_1.text = self.txt_acc_name.text

  def add_an_auto(self,key_word,**event_args):
    self.account['acc_keywords'].insert(0,key_word)
    a_l = self.account['acc_keywords']
    a_l.insert(0,'')
    self.rp_autokeys.items = a_l
    self.rp_autokeys.get_components()[0].text_box_1.placeholder = 'New auto-word'

  def delete_a_key(self,**event_args):
    self.changed = True
    a_l = self.rp_autokeys.items
    print(a_l)
    idx = 0
    for obj in self.rp_autokeys.get_components():
      if obj.to_delete:
        print(obj.text_box_1.text)
        a_l.pop(idx)
        break
      else:
        idx += 1
    if a_l[0] != '':
      a_l.insert(0,'')
    self.rp_autokeys.items = a_l
    self.rp_autokeys.get_components()[0].text_box_1.placeholder = 'New auto-word'

  @handle('btn_delete','click')
  def delete_account(self,**event_args):
    a_c = "Are you sure you wish to delete {a_n}?".format(a_n = self.account['acc_name'])
    a_t = "Delete {a_n}".format(a_n = self.account['acc_name'])
    a = confirm(a_c,title=a_t,buttons=[("Cancel",False),("Delete",True)])
    if a:
      anvil.server.call('delete_account',self.account)