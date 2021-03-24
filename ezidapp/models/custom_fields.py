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

import django.forms.models
import ast
import json
import zlib
import logging

import django.core.exceptions
import django.core.serializers
import django.db.models

import ezidapp.models.shoulder
import ezidapp.models.store_group
import ezidapp.models.store_profile
import ezidapp.models.store_user

import impl.util


class CompressedJsonField(django.db.models.BinaryField):
    # Stores an arbitrary (well, pickle-able) Python object as a gzipped
    # JSON string.
    def get_db_prep_save(self, value, *args, **kwargs):
        if value is None:
            return None
        if isinstance(value, memoryview):
            value = value.tobytes().decode('utf-8')
        try:
            json_str = json.dumps(value, separators=(",", ":"))
            return super(CompressedJsonField, self).get_db_prep_save(
                zlib.compress(json_str.encode('utf-8')), *args, **kwargs
            )
        except Exception as e:
            raise django.core.exceptions.ValidationError(
                "Exception encountered packing compressed JSON database value: "
                + impl.util.formatException(e)
            )

    def from_db_value(self, value, *_args, **_kwargs):
        if value is None:
            return None
        else:
            try:
                return json.loads(zlib.decompress(value))
            except Exception as e:
                raise django.core.exceptions.ValidationError(
                    "Exception encountered unpacking compressed JSON database value: "
                    + impl.util.formatException(e)
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
        try:
            if isinstance(value, (bytes, memoryview)):
                pass
            else:
                if isinstance(value, django.db.models.Model):
                    value = django.forms.models.model_to_dict(value)
                if isinstance(value, dict):
                    value = str(value)
                if isinstance(value, str):
                    value = value.encode('utf-8')
            blob_bytes = zlib.compress(value)
            return super(StoreIdentifierObjectField, self).get_db_prep_save(
                blob_bytes, *args, **kwargs
            )
        except Exception as e:
            if django.conf.settings.DEBUG:
                raise e
            raise django.core.exceptions.ValidationError(
                "Exception encountered packing StoreIdentifier database value: "
                + impl.util.formatException(e)
            )

    def from_db_value(self, value, *_args, **_kwargs):
        if value is None:
            return None
        else:
            try:
                si = next(
                    django.core.serializers.deserialize("json", zlib.decompress(value))
                ).object
                # The citation metadata, being a dictionary and not a type the
                # Django serializer understands, appears to get serialized as
                # though by calling repr() and then base64-ing that.  Thus we
                # must eval() it to return it to its dictionary form.
                # (There's a way to inform the serializer of new types, but
                # that's not supported until Django 1.11.)
                try:
                    if isinstance(si.cm, memoryview):
                        cm = si.cm.tobytes().decode('utf-8')
                    else:
                        cm = str(si.cm)
                    # TODO: This eval may expose EZID to attacks by including code into citation metadata.
                    si.cm = ast.literal_eval(cm)
                except Exception as e:
                    logging.exception(
                        f'Parsing citation metadata failed. metadata="{str(si.cm)}"'
                    )
                # Replace subservient objects referenced by foreign keys with
                # pointers to cached copies to avoid database lookups.
                if si.owner_id is not None:
                    si.owner = ezidapp.models.store_user.getUserById(si.owner_id)
                if si.ownergroup_id is not None:
                    si.ownergroup = ezidapp.models.store_group.getProfileById(
                        si.ownergroup_id
                    )
                if si.datacenter_id is not None:
                    si.datacenter = ezidapp.models.shoulder.getDatacenterById(
                        si.datacenter_id
                    )
                si.profile = ezidapp.models.store_profile.getProfileById(si.profile_id)
                return si, value
            except Exception as e:
                raise django.core.exceptions.ValidationError(
                    "Exception encountered unpacking StoreIdentifier database value: "
                    + impl.util.formatException(e)
                )
