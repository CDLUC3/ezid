# Format:
#
# element: ...
# displayname: ...
# tooltip: ...
# ... XHTML content ...
#                        <-- 1+ blank lines
# element:
# etc.

element: datacite.creator
displayname: Creator
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
tooltip:
<b><u>Title</u></b><br/>
A name or title by which the data or publication is known.

element: datacite.publisher
displayname: Publisher
tooltip:
<b><u>Publisher</u></b><br/>
A holder of the data (e.g., an archive) or the institution which
submitted the work.  In the case of datasets, the publisher is the
entity primarily responsible for making the data available to the
research community.

element: datacite.publicationyear
displayname: Publication year
tooltip:
<b><u>Publication year</u></b><br/>
The year when the data was or will be made publicly available.  If an
embargo period is in effect, use the year when the embargo period
ends.
