from hashids import Hashids
from fastapi import HTTPException, status

hashids = Hashids(salt="your_salt_here", min_length=8)

def encode_id(id: int) -> str:
    return hashids.encode(id)

def decode_id(hashid: str | int) -> int | None:
    if isinstance(hashid, int):
        return hashid
    if hashid.isdigit():
        return int(hashid)
    decoded = hashids.decode(hashid)
    return decoded[0] if decoded else None

def decode_id_or_404(hashid: str | int) -> int:
    """Decode a public identifier; accepts canonical hashids and numeric compatibility inputs."""
    decoded = decode_id(hashid)
    if decoded is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    return decoded
