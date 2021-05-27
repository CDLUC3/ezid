# import json

import django.core.serializers.json
import django.core.serializers.python


# class _Serializer(django.core.serializers.json.DjangoJSONEncoder):
#     def __init__(self):
#         super().__init__()
#
#     def default(self, obj):
#         print('8' * 100)
#         # print(repr(obj))
#         si = django.apps.apps.get_model('ezidapp', 'StoreIdentifier')
#
#         if isinstance(obj, si):
#             return 'X'
#             # return ezidapp.models.custom_fields._field_to_compressed_json_blob(si.cm)
#
#         return super().default(obj)
#
#
# # Serializer = _Serializer()


class CompressedJsonEncoder(django.core.serializers.json.DjangoJSONEncoder):
    def default(self, obj):
        return str(obj)
        # return 'X'
        # if isinstance(obj, uuid.UUID):
        #     return obj.hex
        return super().default(obj)

        # si = django.apps.apps.get_model('ezidapp', 'StoreIdentifier')
        # if isinstance(obj, si):
        #     return _field_to_compressed_json_blob(si.cm)
        # return super().default(obj)


# class Serializer(django.core.serializers.python.Serializer):
#     internal_use_only = False
#
#     def end_serialization(self):
#         json.dump(self.objects, self.stream, cls=CompressedJsonEncoder, **self.options)
#
#     def getvalue(self):
#         if callable(getattr(self.stream, 'getvalue', None)):
#             return self.stream.getvalue()


# class Deserializer(django.core.serializers.python.Deserializer):
#     # internal_use_only = False
#     #
#     # def end_serialization(self):
#     #     json.dump(self.objects, self.stream, cls=CompressedJsonEncoder, **self.options)
#
#     def setvalue(self):
#         if callable(getattr(self.stream, 'getvalue', None)):
#             return self.stream.getvalue()
#
#
# # class Deserializer(django.core.serializers.python.Deserializer):
# #     pass
#
# # Deserializer = django.core.serializers.python.Deserializer
