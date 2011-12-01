from django import template

register = template.Library()

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
  