from django import template
from django.conf import settings

register = template.Library()
      
# a simple menu tag
@register.simple_tag
def request_value(request, key_name):
  """Outputs the value of the request.REQUEST[key_name], required because
  normal django templating will not retrieve any variables starting with an underscore
  which all of the internal profile variables have"""
  if key_name in request.REQUEST:
    return request.REQUEST[key_name]
  else:
    return ''

@register.simple_tag  
def dict_value(dict, key_name):
  """Outputs the value of the dict[key_name], required because
  normal django templating will not retrieve any variables starting with an underscore
  and maps hashes to dots and other ridiculous things."""
  if key_name in dict:
    return dict[key_name]
  else:
    return ''

@register.simple_tag
def selected_radio(request, request_item, loop_index, item_value):
  """returns checked="checked" if this should be the currently selected
  radio button based on matching request data or 1st item and nothing selected"""
  if request_item in request.REQUEST and request.REQUEST[request_item] == item_value:
    return 'checked="checked"'
  elif request_item not in request.REQUEST and loop_index == 1:
    return 'checked="checked"'
  else:
    return ''
  
@register.simple_tag
def shoulder_display(prefix_dict):
  return prefix_dict['namespace'].split()[1] + " (" + prefix_dict['prefix'] + ")"
  

@register.tag
def value_from_settings(parser, token):
  bits = token.split_contents()
  if len(bits) < 2:
    raise template.TemplateSyntaxError("'%s' takes at least one " \
      "argument (settings constant to retrieve)" % bits[0])
  settingsvar = bits[1]
  settingsvar = settingsvar[1:-1] if settingsvar[0] == '"' else settingsvar
  asvar = None
  bits = bits[2:]
  if len(bits) >= 2 and bits[-2] == 'as':
    asvar = bits[-1]
    bits = bits[:-2]
  if len(bits):
    raise template.TemplateSyntaxError("'value_from_settings' didn't recognise " \
      "the arguments '%s'" % ", ".join(bits))
  return ValueFromSettings(settingsvar, asvar)
  
@register.simple_tag
def menu_item2(text, path, this_item, current_item):
  if this_item == current_item:
    return """<span class="menu_current">""" + text + """</span>"""
  else:
    return """<a href="""" + path  +"""">""" + text + """</span></a>"""

#This captures the block around with rounded corners go, can't believe what a PITA this is in django
@register.tag(name="rounded_borders")
def do_rounded_borders(parser, token):
  nodelist = parser.parse(('endrounded_borders'))
  parser.delete_first_token()
  return FormatRoundedBordersNode(nodelist)

class FormatRoundedBordersNode(template.Node):
  def __init__(self,nodelist):
    self.nodelist = nodelist
    
  def render(self, context):
    content = self.nodelist.render(context)
    return """<div class="rb1"><div class="rb2"><div class="rb3"><div class="rb4">
    <div class="rb5"><div class="rb6"><div class="rb7"><div class="rb8">
    %(content)s
    </div></div></div></div></div></div></div></div>""" % {'content':content,}
    
class ValueFromSettings(template.Node):
  def __init__(self, settingsvar, asvar):
    self.arg = template.Variable(settingsvar)
    self.asvar = asvar
  def render(self, context):
    ret_val = getattr(settings,str(self.arg))
    if self.asvar:
      context[self.asvar] = ret_val
      return ''
    else:
      return ret_val
  