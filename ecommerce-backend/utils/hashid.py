from django.conf import settings
from hashids import Hashids

hashids = Hashids(salt=settings.HASHID_FIELD_SALT, min_length=7)


def encode(val):
    return hashids.encode(val)


def decode(val):
    return hashids.decode(val)[0]
