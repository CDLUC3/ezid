from django import template
from django.conf import settings
from django.utils.html import escape
from decorators import basictag

register = template.Library()
      
# a simple menu tag
@register.simple_tag
def request_value(request, key_name):
  """Outputs the value of the request.REQUEST[key_name], required because
  normal django templating will not retrieve any variables starting with an underscore
  which all of the internal profile variables have"""
  if key_name in request.REQUEST:
    return escape(request.REQUEST[key_name])
  else:
    return ''

#@register.simple_tag(takes_context=True)
@register.tag
@basictag(takes_context=True) 
def form_or_dict_value(context, dict, key_name):
  """Outputs the value of the dict[key_name] unless request.POST contains the data
  for the item which then overrides the dictionary's value.
  This both fixes problems with normal django templating which will not retrieve
  any keys starting with an underscore and it solves the problem of re-POSTed values
  which were getting clobbered by the stored values.  POSTed values should override
  so people do not lose their in-process edits.
  """
  request = context['request']
  if request.POST and key_name in request.POST:
    return escape(request.POST[key_name])
  elif key_name in dict:
    return escape(dict[key_name])
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
  return escape(prefix_dict['namespace'].split()[1] + " (" + prefix_dict['prefix'] + ")")
  
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
    

  