class Menu(object):
  #takes name, function name and children (also menus) which should be a list 
  def __init__(self, name, func_name, children):
    self.name = name
    self.func_name = func_name
    self.children = children #tuple
    
    
    