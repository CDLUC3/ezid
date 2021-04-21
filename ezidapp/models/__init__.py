# def getIdentifier(identifier, prefixMatch=False):
#     if prefixMatch:
#         l = list(
#             store_identifier.StoreIdentifier.objects.select_related(
#                 "owner", "owner__group", "ownergroup", "datacenter", "profile"
#             ).filter(identifier__in=impl.util.explodePrefixes(identifier))
#         )
#         if len(l) > 0:
#             return max(l, key=lambda si: len(si.identifier))
#         else:
#             raise store_identifier.StoreIdentifier.DoesNotExist()
#     else:
#         return store_identifier.StoreIdentifier.objects.select_related(
#             "owner", "owner__group", "ownergroup", "datacenter", "profile"
#         ).get(identifier=identifier)
