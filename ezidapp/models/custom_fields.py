import ast
import base64

# import functools
import json
import logging
import zlib

import django.core.exceptions
import django.core.serializers
import django.core.serializers.base
import django.db.models

# import ezidapp.models.identifier
# import ezidapp.models.serialization
import impl.util

log = logging.getLogger(__name__)

import django.core.serializers.json


class CompressedJsonField(django.db.models.BinaryField):
    """Field containing a nested Python object as a gzipped JSON string. Object must consist of
    basic types that can be represented in JSON. The top level object is typically a list or a
    dict, which nested objects being list, dict, str, int or float. Other types can be added by
    adding a class with coding/decoding methods to the JSON

    https://docs.djangoproject.com/en/3.2/howto/custom-model-fields/
    """

    description = 'Field containing arbitrary gzipped JSON'

    def __str__(self):
        return f'{self.__class__.__name__}: {len(super().__str__())} bytes (compressed)'

    def get_db_prep_save(self, obj, connection):
        """Serialize a Django model (ORM) instance for storage in the database.

        Args:
            obj: Django model instance
            connection: Open connection to the database. Can he used if details in the serialization
            depends on what already exist in the DB.

        Returns:
            Compressed JSON bytes, ready for storing in the database.

        - get_db_prep_save() is used only when an object is serialized for storage, not when it is
        serialized for queries. We use it so that we can compress the objects before storing them in
        the database, while still keeping in the clear for queries.
        """
        impl.util.log_obj(obj, connection, msg='CompressedJsonField.get_db_prep_save()')
        return _field_to_compressed_json(obj)

    def get_prep_value(self, obj):
        """Python object to query value."""
        # if obj is None or _is_orm(obj):
        #     return obj
        impl.util.log_obj(obj, msg='StoreIdentifierObjectField.get_prep_value()')
        return _field_to_compressed_json(obj)
        # return self.serialize_field(obj)

    def from_db_value(self, obj, expression, connection):
        impl.util.log_obj(obj, connection, msg='CompressedJsonField.from_db_value()')
        return _compressed_json_to_field(obj)

    def to_python(self, obj):
        """https://docs.djangoproject.com/en/3.2/howto/custom-model-fields/#converting-values-to-python-objects
        to_python() must handle the following input:
        - None (if the field allows null=True)
        - An instance of the correct model type
        - A string
        """
        # if obj is None or _is_orm(obj):
        #     return obj
        impl.util.log_obj(obj, msg='CompressedJsonField.to_python()')
        return _base64_to_py(obj)


class NonValidatingForeignKey(django.db.models.ForeignKey):
    """A ForeignKey that doesn't perform any validation."""

    def validate(self, obj, model_instance):
        pass


class StoreIdentifierObjectField(django.db.models.BinaryField):
    """Field containing a StoreIdentifier model instance as gzipped JSON.

    - The StoreIdentifier model instance primary key (pk) attribute may be set or unset. If `pk` is
    unset, the object is designated as newly created and unsaved (existing only in memory). The
    object does not reference any existing rows in the the StoreIdentifier table, and the identifier
    in the model instance may or may not exist in the StoreIdentifier, or other tables.

    - If set, `pk` must reference an existing row in the StoreIdentifier table. The identifier in
    the referenced row should be an exact match for identifier in the model instance. Other values
    may differ, representing the identifier in a different state.

    - Model instances are normally in an unsaved state only briefly after they're created, which is
    while they are being populated with field values. Once populated, the object's `.save()` method
    is called, which causes the object to be serialized and written to a new database row, and the
    object's `pk` to be set to the index of the new row, which enables future model modifications to
    be synced to the database.

    - If there are issues finding the field values for an object, e.g., if the object was intended
    to hold the results of an operation, and the operation was cancelled or interrupted, the object
    may end up being discarded instead of saved. Any object that becomes unreachable without having
    had its `.save()` method called, is discarded.

    - Calling `.save()` on an an object always causes a new row to be inserted if `pk` is unset, and
    an existing row to be updated if `pk` is set. If the inserted or updated row breaks any
    constraints, the operation fails with an IntegrityError or other exception.

    - `pk` can be manipulated programmatically before calling `.save()` in order to change an update
    to an insert and vice versa, or to change which row is updated.

    - Sample StoreIdentifier model instance, after serialization to JSON. Note that .cm is a nested
    serialized instance of a metadata object.

    {
        "model": "ezidapp.storeidentifier",
        "pk": 45,
        "fields": {
            "identifier": "ark:/13030/c7ks6j41m",
            "createTime": 1296220114,
            "updateTime": 1559168402,
            "status": "U",
            "unavailableReason": "SUPPRIME",
            "exported": true,
            "crossrefStatus": "",
            "crossrefMessage": "",
            "target": "http://ezid.cdlib.org/id/ark:/13030/c7ks6j41m",
            "cm": "e3UnZXJjLndobyc6IHUnU1VQUFJJTUUnLCB1J2VyYy53aGVuJzogdSdTVVBQUklNRScsIHUnZXJjLndoYXQnOiB1J1NVUFBSSU1FJ30=",
            "agentRole": "",
            "isTest": false,
            "owner": 421,
            "ownergroup": 28,
            "datacenter": null,
            "profile": 1,
        },
    }

    """

    # def value_to_string(self, obj):
    #     impl.util.log_obj(obj, msg='StoreIdentifierObjectField.value_to_string()')
    #
    #     if _is_orm(obj):
    #         return None
    #
    #     # if _is_orm(obj):
    #     #     return None
    #     obj = self.value_from_object(obj)
    #     obj = self.get_prep_value(obj)
    #     impl.util.log_obj(
    #         obj, msg='StoreIdentifierObjectField.value_to_string()'
    #     )
    #     return obj

    description = 'Field containing a StoreIdentifier model instance as gzipped JSON'

    # def db_type(self, connection):
    #     def db_type(self, connection):
    #         return 'mytype'

    def __str__(self):
        return f'{self.__class__.__name__}: {len(super().__str__())} bytes (compressed)'

    def get_db_prep_save(self, obj, connection):
        """Serialize a Django model (ORM) instance for storage in the database.

        Args:
            obj: Django model instance
            connection: Open connection to the database. Can he used if details in the serialization
            depends on what already exist in the DB.

        Returns:
            Compressed JSON bytes, ready for storing in the database.

        - get_db_prep_save() is used only when an object is serialized for storage, not when it is
        serialized for queries. We use it so that we can compress the objects before storing them in
        the database, while still keeping in the clear for queries.
        """
        # if obj is None or _is_orm(obj):
        #     return obj
        # impl.util.log_obj(obj, connection, msg='CompressedJsonField.get_db_prep_save()')
        # return _field_to_compressed_json(obj)

    def get_prep_value(self, obj):
        """Python object to query value."""
        if obj is None or _is_orm(obj):
            return obj
        impl.util.log_obj(obj, msg='StoreIdentifierObjectField.get_prep_value()')
        return _field_to_compressed_json(obj)
        # return self.serialize_field(obj)

    # def get_db_prep_save(self, obj, connection):
    #     """StoreIdentifier model instance -> gzipped JSON
    #
    #     Returns:
    #         Union[None, bytes]:
    #
    #     Args:
    #         obj (object):
    #         connection ():
    #
    #     - Convert a StoreIdentifier model instance with data to bytes. The bytes are later stored in
    #     the object field of UpdateQueue. The reverse operation is performed in `from_db_value()`.
    #
    #     - This method is used when the custom field needs a conversion when saved that is different
    #     from the one used when the field is accessed in queries.
    #     """
    #     impl.util.log_obj(obj, msg='StoreIdentifierObjectField.get_db_prep_save()')
    #     log.debug('StoreIdentifierObjectField.get_db_prep_save()')
    #     # if isinstance(obj.cm, str):
    #     obj.cm = self.serialize_field(obj.cm)
    #     obj = self.serialize_field(obj)
    #     return self.serialize_field(obj)

    def from_db_value(self, obj, expression, connection):
        """gzipped JSON -> StoreIdentifier model instance with data.

        - Convert the bytes which are stored in the `object` field of UpdateQueue to a
        StoreIdentifier model instance with data. The reverse operation is performed in
        `get_db_prep_save()`.

        - Must be able to handle the value as it arrives from the database, and None.

        - If present for the field subclass, from_db_value() will be called in all circumstances
        when the data is loaded from the database, including in aggregates and values() calls.
        """
        if obj is None or _is_orm(obj):
            return obj

        # obj.cm = None#_compressed_bytes_to_py(obj.cm)
        # obj.cm = _compressed_bytes_to_py(obj.cm)

        impl.util.log_obj(obj, msg='StoreIdentifierObjectField.from_db_value()')
        obj = _compressed_json_to_field(obj)
        obj.cm = _base64_to_py(obj.cm)
        return obj

    def to_python(self, obj):
        """https://docs.djangoproject.com/en/3.2/howto/custom-model-fields/#converting-values-to-python-objects
        to_python() must handle the following:
        - None (if the field allows null=True)
        - An instance of the correct model type
        - A string
        """
        impl.util.log_obj(obj, msg='StoreIdentifierObjectField.to_python()')
        if obj is None or _is_orm(obj):
            return obj
        return _base64_to_py(obj)

    def value_to_string(self, obj):
        obj = self.value_from_object(obj)
        return _field_to_compressed_json(obj)


@impl.util.log_inout()
def _field_to_compressed_json(obj):
    assert _is_orm(obj), f'Unexpected type: {obj!r}'
    obj = django.core.serializers.serialize("json", [obj])
    obj = _compress(obj)
    return obj


@impl.util.log_inout()
def _compressed_json_to_field(obj):
    if obj is None or _is_orm(obj):
        return obj
    assert isinstance(obj, bytes)
    obj = _decompress(obj)
    # obj = _trim_json_list(obj)
    obj = next(django.core.serializers.deserialize("json", obj))
    assert isinstance(obj, django.core.serializers.base.DeserializedObject)
    obj = obj.object
    assert _is_orm(obj)
    return obj


@impl.util.log_inout()
def _py_to_compressed_bytes(obj):
    obj = repr(obj)
    obj = _compress(obj)
    return obj


@impl.util.log_inout()
def _compressed_bytes_to_py(obj):
    assert isinstance(obj, bytes)
    obj = _decompress(obj)
    obj = _to_str(obj)
    obj = ast.literal_eval(obj)
    return obj


@impl.util.log_inout()
def _base64_to_py(obj):
    """Compressed (?) Base64 str or bytes -> arbitrarily nested Python objects."""
    if _is_orm(obj):
        return obj
    obj = _to_bytes(obj)
    obj = base64.b64decode(obj)
    # obj = _decompress(obj)
    obj = _to_str(obj)
    obj = ast.literal_eval(obj)
    return obj


@impl.util.log_inout()
def _compress(obj):
    """str, memoryview or bytes -> compressed bytes
    None -> None
    """
    obj = _to_bytes(obj)
    obj = zlib.compress(obj)
    assert isinstance(obj, bytes)
    return obj


@impl.util.log_inout()
def _decompress(obj):
    """Compressed bytes -> clear bytes"""
    assert isinstance(obj, bytes)
    # if isinstance(obj, memoryview):
    #     return obj.tobytes()
    # else:
    #     obj = _to_bytes(obj)
    obj = zlib.decompress(obj)
    return obj


@impl.util.log_inout()
def _to_bytes(obj):
    if obj is None:
        return None
    elif isinstance(obj, bytes):
        return obj
    elif isinstance(obj, str):
        return obj.encode('utf-8', errors='replace')
    elif isinstance(obj, memoryview):
        return obj.tobytes()
    else:
        raise AssertionError(f'Unexpected type: {obj!r}')


@impl.util.log_inout()
def _to_str(obj):
    return _to_bytes(obj).decode('utf-8', errors='replace')


@impl.util.log_inout()
def _trim_json_list(obj):
    if obj is None:
        obj = b'{}'
    if isinstance(obj, str):
        obj = obj.encode('utf-8', errors='replace')
    assert isinstance(obj, bytes), f'Unexpected type: {obj!r}'
    obj = json.loads(obj)
    if isinstance(obj, list) and len(obj) == 1:
        obj = obj[0]
    obj = json.dumps(obj)
    return obj


@impl.util.log_inout()
def _is_orm(obj):
    return obj is None or isinstance(
        obj,
        (django.db.models.Model, django.db.models.Field),
    )
