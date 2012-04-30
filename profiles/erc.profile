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

element: erc.who
displayname: Who
displaytype: text
tooltip:
<b><u>Who</u></b><br/>
The name of an entity (person, organization, or service) responsible
for creating the content or making it available.  For an article, this
could be an author.  Put name parts in "sort-friendly" order, such
as:<br/>
&nbsp;&nbsp;<font face="Courier">van Gogh, Vincent,</font><br/>
&nbsp;&nbsp;<font face="Courier">Hu Jintao</font><br/>
&nbsp;&nbsp;<font face="Courier">Gilbert, William, Sir,,; Sullivan,
Arthur, Sir,,</font><br/>
Separate multiple names with ";".  Append one or more final commas
(",") to indicate that one or more internal commas can be used as
inversion points to recover natural word order (if different from
sort-friendly word order).

element: erc.what
displayname: What
displaytype: text
tooltip:
<b><u>What</u></b><br/>
A name or other human-oriented identifier given to the resource.  For
an article, this could be a title such as:<br/>
&nbsp;&nbsp;<font face="Courier">Moby Dick</font><br/>
&nbsp;&nbsp;<font face="Courier">Scarlet Pimpernel, The,</font><br/>
Use sort-friendly name parts and final commas in the same way as for
the "Who" element.

element: erc.when
displayname: When
displaytype: text
tooltip:
<b><u>When</u></b><br/>
A point or period of time important in the lifecycle of the resource,
often when it was created, modified, or made available.  For an
article, this could be the date it was written, such as:<br/>
&nbsp;&nbsp;<font face="Courier">2009.04.23</font><br/>
&nbsp;&nbsp;<font face="Courier">1924~</font><br/>
&nbsp;&nbsp;<font face="Courier">BCE0386</font><br/>
&nbsp;&nbsp;<font face="Courier">1998-2003; 2008-</font><br/>
A date range (which can be open ended) may be useful, such as to
indicate the years during which a periodical operated.  Use ";" to
separate entries and "~" to indicate approximation.
