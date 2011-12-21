# Format:
#
# element: ...
# displayname: ...
# displaytype: (of 'text', 'datetime', 'url', 'boolean', 'is_public')
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
displayname: Published
displaytype: is_public
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
displayname: Location
displaytype: url
tooltip:
<b><u>Object location URL</u></b><br/>
The current location (URL) of the identified object.

element: _profile
displayname: Profile
displaytype: text
tooltip:

element: _owner
displayname: Owner
displaytype: text
tooltip:
<b><u>Owner</u></b><br/>
The identifier's owner.  Only the owner and any account-wide or
per-identifier co-owners may modify the identifier.

element: _ownergroup
displayname: Group
displaytype: text
tooltip:
<b><u>Owner group</u></b><br/>
The identifier's owner group.

element: _coowners
displayname: Co-owners
displaytype: text
tooltip:
<b><u>Co-owners</u></b><br/>
The identifier's co-owners (additional users who may modify the
identifier).

element: _created
displayname: Created
displaytype: datetime
tooltip:
<b><u>Created</u></b><br/>
The UTC date and time the identifier was created.

element: _updated
displayname: Last modified
displaytype: datetime
tooltip:
<b><u>Updated</u></b><br/>
The UTC date and time the identifier was last updated.

element: _shadowedby
displayname: Shadow ARK
displaytype: text
tooltip:
<b><u>Shadow ARK</u></b><br/>
An independent but related ARK identifier.  The shadow ARK has the
same owner and citation metadata as this identifier, but may have a
different object location.  It may be used to provide, for example,
resolution to subcomponents of the identified object.

element: _shadows
displayname: Shadowed identifier
displaytype: text
tooltip:
<b><u>Shadowed identifier</u></b><br/>
This identifier is a "shadow ARK" that shadows another identifier.  A
shadow ARK has the same owner and citation metadata as the shadowed
identifier, but may have a different object location.  It may be used
to provide, for example, resolution to subcomponents of the identified
object.
