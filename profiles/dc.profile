# Format:
#
# element: ...
# displayname: ...
# displaytype: 'text', 'datetime', 'url', 'boolean', or 'status'
# tooltip: ...
# ... XHTML content ...
#                        <-- 1+ blank lines
# element:
# etc.

element: dc.creator
displayname: Creator
displaytype: text
tooltip:
<b><u>Creator</u></b><br/>
An entity primarily responsible for making the content of the
resource.  Examples of a Creator include a person, an organization, or
a service.  Typically, the name of a Creator should be used to
indicate the entity.

element: dc.title
displayname: Title
displaytype: text
tooltip:
<b><u>Title</u></b><br/>
A name given to the resource.  Typically, a Title will be a name by
which the resource is formally known.

element: dc.publisher
displayname: Publisher
displaytype: text
tooltip:
<b><u>Publisher</u></b><br/>
An entity responsible for making the resource available.  Examples of
a Publisher include a person, an organization, or a service.
Typically, the name of a Publisher should be used to indicate the
entity.

element: dc.date
displayname: Date
displaytype: text
tooltip:
<b><u>Date</u></b><br/>
A date associated with an event in the life cycle of the resource.
Typically, Date will be associated with the creation or availability
of the resource.  Recommended best practice for encoding the date
value is defined in a profile of ISO 8601 and follows the YYYY-MM-DD
format.

element: dc.type
displayname: Type
displaytype: text
tooltip:
<b><u>Type</u></b><br/>
The nature or genre of the resource.  Recommended best practice is to
use a term from the DCMI Type Vocabulary:<br/>
&nbsp;&nbsp;<font face="Courier">Collection</font><br/>
&nbsp;&nbsp;<font face="Courier">Dataset</font><br/>
&nbsp;&nbsp;<font face="Courier">Event</font><br/>
&nbsp;&nbsp;<font face="Courier">Image</font><br/>
&nbsp;&nbsp;<font face="Courier">InteractiveResource</font><br/>
&nbsp;&nbsp;<font face="Courier">MovingImage</font><br/>
&nbsp;&nbsp;<font face="Courier">PhysicalObject</font><br/>
&nbsp;&nbsp;<font face="Courier">Service</font><br/>
&nbsp;&nbsp;<font face="Courier">Software</font><br/>
&nbsp;&nbsp;<font face="Courier">Sound</font><br/>
&nbsp;&nbsp;<font face="Courier">StillImage</font><br/>
&nbsp;&nbsp;<font face="Courier">Text</font><br/>
