import ast
import base64
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
    """

    description = 'Field containing arbitrary gzipped JSON'

    # def __str__(self):
    #     return self.get_prep_value(self)

    def get_db_prep_save(self, obj, connection):
        """
        Args:
            obj (object):
            connection (object):

        Returns:
            object:
        """
        # impl.util.log_obj(obj, args, kwargs, msg='get_db_prep_save')
        log.debug('CompressedJsonField.get_db_prep_save()')
        return _field_to_compressed_blob(obj)

    def from_db_value(self, obj, expression, connection):
        impl.util.log_obj(
            obj, expression, connection, msg='CompressedJsonField.from_db_value() input'
        )
        # impl.util.log_obj(expression, msg='from_db_value: input expression', sep=False)
        # impl.util.log_obj(
        #     connection, msg='from_db_value: input connection', sep_before=False
        # )
        obj = _field_from_compressed_blob(obj)
        impl.util.log_obj(obj, msg='CompressedJsonField.from_db_value() return')
        return obj

    def to_python(self, obj):
        """https://docs.djangoproject.com/en/3.2/howto/custom-model-fields/#converting-values-to-python-objects
        to_python() must handle the following input:
        - None (if the field allows null=True)
        - An instance of the correct model type
        - A string
        """
        impl.util.log_obj(obj, msg='CompressedJsonField.to_python() input')
        # obj = _to_bytes(obj)
        obj = _py_from_base64(obj)
        impl.util.log_obj(obj, msg='CompressedJsonField.to_python() return')
        return obj

    def deserialize_field(self, obj):
        impl.util.log_obj(obj, msg='CompressedJsonField.deserialize_field() input')
        if _is_ready(obj):
            return obj
        obj = _field_from_compressed_blob(obj)
        # obj.cm = None
        # obj.object = None
        # obj.cm = _py_from_compressed_blob(obj.cm)
        # obj = obj.object
        impl.util.log_obj(obj, msg='CompressedJsonField.deserialize_field() return')
        return obj

    def serialize_field(self, obj):
        impl.util.log_obj(obj, msg='CompressedJsonField.serialize_field() input')
        if _is_ready(obj):
            return obj
        return _field_to_compressed_blob(obj)



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

    def value_to_string(self, obj):
        if isinstance(obj, ezidapp.models.identifier.StoreIdentifier):
            return None

        impl.util.log_obj(obj, msg='StoreIdentifierObjectField.value_to_string() input')
        # if isinstance(obj, django.db.models.Model):
        #     return None
        obj = self.value_from_object(obj)
        obj = self.get_prep_value(obj)
        impl.util.log_obj(
            obj, msg='StoreIdentifierObjectField.value_to_string() return'
        )
        return obj

    description = 'Field containing a StoreIdentifier model instance as gzipped JSON'

    # def db_type(self, connection):
    #     def db_type(self, connection):
    #         return 'mytype'

    def get_prep_value(self, obj):
        """Python object to query value."""
        impl.util.log_obj(obj, msg='StoreIdentifierObjectField.get_prep_value() return')
        return self.serialize_field(obj)

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
        impl.util.log_obj(obj, msg='StoreIdentifierObjectField.value_to_string() input')
        return self.deserialize_field(obj)

    def to_python(self, obj):
        """https://docs.djangoproject.com/en/3.2/howto/custom-model-fields/#converting-values-to-python-objects
        to_python() must handle the following input:
        - None (if the field allows null=True)
        - An instance of the correct model type
        - A string
        """
        impl.util.log_obj(obj, msg='StoreIdentifierObjectField.to_python() input')
        obj = _to_bytes(obj)
        obj = self._py_from_base64(obj)
        impl.util.log_obj(obj, msg='StoreIdentifierObjectField.to_python() return')
        return obj

    def deserialize_field(self, obj):
        impl.util.log_obj(
            obj, msg='StoreIdentifierObjectField.deserialize_field() input'
        )
        if _is_ready(obj):
            return obj
        obj = _field_from_compressed_blob(obj)
        # obj.cm = None#_py_from_compressed_blob(obj.cm)
        # obj.cm = _py_from_compressed_blob(obj.cm)
        obj.cm = _py_from_base64(obj.cm)
        impl.util.log_obj(
            obj, msg='StoreIdentifierObjectField.deserialize_field() return'
        )
        return obj

    def serialize_field(self, obj):
        impl.util.log_obj(obj, msg='StoreIdentifierObjectField.serialize_field() input')
        if _is_ready(obj):
            return obj
        return _field_to_compressed_blob(obj)


# obj = copy.copy(obj)


def _field_to_compressed_blob(obj):
    impl.util.log_obj(obj, msg='_field_compress() input')
    obj = _compress(obj)
    impl.util.log_obj(obj, msg='_field_compress() return')
    return obj


def _field_from_compressed_blob(obj):
    assert isinstance(obj, bytes)
    impl.util.log_obj(obj, msg='_field_decompress() input')
    obj = _decompress(obj)
    obj = _trim_json_list(obj)
    obj = next(django.core.serializers.deserialize("json", obj))
    assert isinstance(obj, django.core.serializers.base.DeserializedObject)
    obj = obj.object
    assert isinstance(obj, django.db.models.Model)
    impl.util.log_obj(obj, msg='_field_decompress() return')
    return obj

    # cls=ezidapp.models.serialization.CompressedJsonEncoder,
    # obj = _to_str(obj)
    # obj = json.loads(obj)
    # obj = obj.encode('utf-8')
    # obj = zlib.compress(obj)
    # return obj
    # # return super().get_db_prep_save(obj, connection)


def _py_to_compressed_blob(obj):
    impl.util.log_obj(obj, msg='_py_to_compressed_blob() input')
    obj = repr(obj)
    obj = _compress(obj)
    impl.util.log_obj(obj, msg='_py_to_compressed_blob() return')
    assert isinstance(obj, bytes)
    return obj


def _py_from_compressed_blob(obj):
    impl.util.log_obj(obj, msg='_py_from_compressed_blob() input')
    assert isinstance(obj, bytes)
    obj = _decompress(obj)
    obj = _to_str(obj)
    obj = ast.literal_eval(obj)
    impl.util.log_obj(obj, msg='_py_from_compressed_blob() return')
    return obj


def _py_from_base64(obj):
    impl.util.log_obj(obj, msg='_py_from_base64() input')
    # obj = _decompress(obj)
    # obj = _to_str(obj)
    obj = base64.b64decode(obj)
    # obj = _to_bytes(obj)
    obj = _to_str(obj)
    obj = ast.literal_eval(obj)
    impl.util.log_obj(obj, msg='_py_from_base64() return')
    return obj


def _compress(obj):
    impl.util.log_obj(obj, msg='_compress() input')
    obj = _to_bytes(obj)
    obj = zlib.compress(obj)
    impl.util.log_obj(obj, msg='_compress() return')
    return obj


def _decompress(obj):
    impl.util.log_obj(obj, msg='_decompress() input')
    if isinstance(obj, memoryview):
        return obj.tobytes()
    assert isinstance(obj, bytes)
    # else:
    #     obj = _to_bytes(obj)
    obj = zlib.decompress(obj)
    impl.util.log_obj(obj, msg='_decompress() return')
    return obj


def _is_ready(obj):
    return isinstance(obj, django.db.models.Model)


def _to_bytes(obj):
    impl.util.log_obj(obj, msg='_to_bytes() input')
    # assert not isinstance(obj, django.db.models.Model)
    if obj is None:
        return None
    elif isinstance(obj, str):
        obj = obj.encode('utf-8', errors='replace')
    elif isinstance(obj, memoryview):
        obj = obj.tobytes()
    # assert isinstance(obj, bytes)
    impl.util.log_obj(obj, msg='_to_bytes() return')
    return obj


def _to_str(obj):
    assert not isinstance(obj, django.db.models.Model)
    if obj is None:
        return None
    obj = obj.decode('utf-8', errors='replace')
    assert isinstance(obj, str)
    return obj


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
