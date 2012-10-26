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

element: datacite.creator
displayname: Creator
displaytype: text
tooltip:
<b><u>Creator</u></b><br/>
The main researchers involved in producing the data, or the authors of
the publication in priority order.  Each name may be a corporate,
institutional, or personal name.  In personal names list family name
before given name, as in:<br/>
&nbsp;&nbsp;<font face="Courier">Shakespeare, William</font><br/>
Non-roman names should be transliterated according to the ALA-LC
schemes.

element: datacite.title
displayname: Title
displaytype: text
tooltip:
<b><u>Title</u></b><br/>
A name or title by which the data or publication is known.

element: datacite.publisher
displayname: Publisher
displaytype: text
tooltip:
<b><u>Publisher</u></b><br/>
A holder of the data (e.g., an archive) or the institution which
submitted the work.  In the case of datasets, the publisher is the
entity primarily responsible for making the data available to the
research community.

element: datacite.publicationyear
displayname: Publication year
displaytype: text
tooltip:
<b><u>Publication year</u></b><br/>
The year when the data was or will be made publicly available.  If an
embargo period is in effect, use the year when the embargo period
ends.

element: datacite.resourcetype
displayname: Resource type
displaytype: select: (('', '[Not Set]'), ('Collection', 'Collection'), ('Dataset', 'Dataset'), ('Event','Event'), ('Film', 'Film'), ('Image', 'Image'), ('InteractiveResource', 'InteractiveResource'), ('Model', 'Model'), ('PhysicalObject', 'PhysicalObject'), ('Service','Service'), ('Software', 'Software'), ('Sound', 'Sound'), ('Text', 'Text'))
tooltip:
<b><u>Resource type</u></b><br/>
The general type and, optionally, specific type of the data.  The
general type must be one of the controlled vocabulary terms defined in
the DataCite Metadata Scheme:<br/>
&nbsp;&nbsp;<font face="Courier">Collection</font><br/>
&nbsp;&nbsp;<font face="Courier">Dataset</font><br/>
&nbsp;&nbsp;<font face="Courier">Event</font><br/>
&nbsp;&nbsp;<font face="Courier">Film</font><br/>
&nbsp;&nbsp;<font face="Courier">Image</font><br/>
&nbsp;&nbsp;<font face="Courier">InteractiveResource</font><br/>
&nbsp;&nbsp;<font face="Courier">Model</font><br/>
&nbsp;&nbsp;<font face="Courier">PhysicalObject</font><br/>
&nbsp;&nbsp;<font face="Courier">Service</font><br/>
&nbsp;&nbsp;<font face="Courier">Software</font><br/>
&nbsp;&nbsp;<font face="Courier">Sound</font><br/>
&nbsp;&nbsp;<font face="Courier">Text</font><br/>
Specific types are unconstrained.  If a specific type is given, it
must be separated from the general type by a forward slash ("/"), as
in:<br/>
&nbsp;&nbsp;<font face="Courier">Image/Photograph</font>
