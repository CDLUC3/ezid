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

element: _urlform
displayname: URL form
displaytype: url
tooltip:
<b><u>URL form of identifier</u></b><br/>
The identifier expressed as a URL.  Following this URL in a browser
will redirect to the object location URL.  Thus, include this URL
wherever a persistent hyperlink to the identified object is
desired.<br/>
In citations, a common practice is to display the identifier as a
hyperlink, with the identifier as the visible hyperlink text and the
URL form of the identifier as the link.  In HTML, this takes the
form<br/>
&nbsp;&nbsp;<font face="Courier">&lt;a href="url
form"&gt;identifier&lt;/a&gt;</font>

element: _status
displayname: Status
displaytype: string
tooltip:
<b><u>Status</u></b><br/>
The identifier's status.  "<font face="Courier">public</font>"
indicates the identifier is globally and publicly visible.  "<font
face="Courier">reserved</font>" indicates the identifier has been
reserved within EZID, but has not been made public yet.  "<font
face="Courier">unavailable</font>" indicates the identifier is public,
but the object referenced by the identifier is not available; a reason
for the object's unavailability may be given.

element: _target
displayname: Location (URL)
displaytype: url
tooltip:
<b><u>Object location URL</u></b><br/>
The current location (URL) of the identified object.

element: _profile
displayname: Profile
displaytype: text
tooltip:
<b><u>Profile</u></b><br/>
The identifier's metadata profile.

element: _owner
displayname: Owner
displaytype: text
tooltip:
<b><u>Owner</u></b><br/>
The identifier's owner.

element: _ownergroup
displayname: Group
displaytype: text
tooltip:
<b><u>Group</u></b><br/>
The identifier owner's group.

element: _created
displayname: Created
displaytype: datetime
tooltip:
<b><u>Created</u></b><br/>
The date and time the identifier was created.

element: _updated
displayname: Last modified
displaytype: datetime
tooltip:
<b><u>Last updated</u></b><br/>
The date and time the identifier was last updated.

element: _export
displayname: Allow harvesting/indexing?
displaytype: boolean
tooltip:
<b><u>Allow harvesting/indexing?</u></b><br/>
Determines if the identifier is publicized by exporting it to external
indexing and harvesting services.

element: _datacenter
displayname: Datacenter
displaytype: text
tooltip:
<b><u>Datacenter</u></b><br/>
The DataCite datacenter at which the identifier is registered (or will
be registered, in the case of a reserved identifier).

element: _crossref
displayname: Crossref registration
displaytype: text
tooltip:
<b><u>Crossref registration</u></b><br/>
If present, indicates that the identifier is registered with Crossref
(or, in the case of a reserved identifier, will be registered), and
also indicates the status of the registration process.
