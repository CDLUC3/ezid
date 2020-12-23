# =============================================================================
#
# EZID :: ezidapp/models/custom_fields.py
#
# Custom model fields.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2015, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import ast
import json
import zlib

import django.core.exceptions
import django.core.serializers
import django.db.models

from . import shoulder
from . import store_group
from . import store_profile
from . import store_user
import util


class CompressedJsonField(django.db.models.BinaryField):
    # Stores an arbitrary (well, pickle-able) Python object as a gzipped
    # JSON string.

    def get_db_prep_save(self, value, *args, **kwargs):
        if value is None:
            return None
        # When the DB is populated via a JSON fixture, using the loaddata management
        # command, the values arrive here as strings wrapped in native C buffer objects
        # instead of the expected Python container type. This only occurs when invoking
        # loaddata using the Django call_command() method, not when invoking loaddata
        # via manage.py.
        if isinstance(value, buffer):
            value = eval(str(value))
        try:
            json_str = json.dumps(value, separators=(",", ":"))
            return super(CompressedJsonField, self).get_db_prep_save(
                zlib.compress(json_str), *args, **kwargs
            )
        except Exception as e:
            raise django.core.exceptions.ValidationError(
                "Exception encountered packing compressed JSON database value: "
                + util.formatException(e)
            )

    def from_db_value(self, value, *args, **kwargs):
        if value is None:
            return None
        else:
            try:
                return json.loads(zlib.decompress(value))
            except Exception as e:
                raise django.core.exceptions.ValidationError(
                    "Exception encountered unpacking compressed JSON database value: "
                    + util.formatException(e)
                )


class NonValidatingForeignKey(django.db.models.ForeignKey):
    # A ForeignKey that doesn't perform any validation.

    def validate(self, value, model_instance):
        pass


class StoreIdentifierObjectField(django.db.models.BinaryField):
    # Stores a StoreIdentifier object as a gzipped
    # Django/JSON-serialized string (hereinafter "blob").  The object
    # may have a primary key (i.e., represent an existing row in the
    # StoreIdentifier table) or not.  In setting the field, the supplied
    # value may be a StoreIdentifier object or a previously-created
    # blob.  In getting the field, the returned value is a tuple
    # (StoreIdentifier, blob).

    def get_db_prep_save(self, value, *args, **kwargs):
        if value is None:
            return None
        else:
            try:
                if type(value) in [str, buffer]:
                    v = value
                else:
                    v = zlib.compress(
                        django.core.serializers.serialize("json", [value])
                    )
                return super(StoreIdentifierObjectField, self).get_db_prep_save(
                    v, *args, **kwargs
                )
            except Exception as e:
                raise django.core.exceptions.ValidationError(
                    "Exception encountered packing StoreIdentifier database value: "
                    + util.formatException(e)
                )

    def from_db_value(self, value, *args, **kwargs):
        if value is None:
            return None
        else:
            try:
                si = (
                    django.core.serializers.deserialize("json", zlib.decompress(value))
                    .next()
                    .object
                )
                # The citation metadata, being a dictionary and not a type the
                # Django serializer understands, appears to get serialized as
                # though by calling repr() and then base64-ing that.  Thus we
                # must eval() it to return it to its dictionary form.
                # (There's a way to inform the serializer of new types, but
                # that's not supported until Django 1.11.)
                si.cm = ast.literal_eval(str(si.cm))
                # Replace subservient objects referenced by foreign keys with
                # pointers to cached copies to avoid database lookups.
                if si.owner_id != None:
                    si.owner = store_user.getById(si.owner_id)
                if si.ownergroup_id != None:
                    si.ownergroup = store_group.getById(si.ownergroup_id)
                if si.datacenter_id != None:
                    si.datacenter = shoulder.getDatacenterById(si.datacenter_id)
                si.profile = store_profile.getById(si.profile_id)
                return (si, value)
            except Exception as e:
                raise django.core.exceptions.ValidationError(
                    "Exception encountered unpacking StoreIdentifier database value: "
                    + util.formatException(e)
                )
