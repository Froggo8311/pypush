from __future__ import annotations

import courier, albert
from hashlib import sha1


def _serialize_field(id: int, value: bytes) -> bytes:
    return id.to_bytes() + len(value).to_bytes(2, "big") + value


def _serialize_payload(id: int, fields: list[(int, bytes)]) -> bytes:
    payload = b""

    for fid, value in fields:
        if fid is not None:
            payload += _serialize_field(fid, value)

    return id.to_bytes() + len(payload).to_bytes(4, "big") + payload


def _deserialize_field(stream: bytes) -> tuple[int, bytes]:
    id = int.from_bytes(stream[:1], "big")
    length = int.from_bytes(stream[1:3], "big")
    value = stream[3 : 3 + length]
    return id, value

# Note: Takes a stream, not a buffer, as we do not know the length of the payload
# WILL BLOCK IF THE STREAM IS EMPTY
def _deserialize_payload(stream) -> tuple[int, list[tuple[int, bytes]]] | None:
    id = int.from_bytes(stream.read(1), "big")

    if id == 0x0:
        return None

    length = int.from_bytes(stream.read(4), "big")

    buffer = stream.read(length)

    fields = []

    while len(buffer) > 0:
        fid, value = _deserialize_field(buffer)
        fields.append((fid, value))
        buffer = buffer[3 + len(value) :]

    return id, fields

def _deserialize_payload_from_buffer(buffer: bytes) -> tuple[int, list[tuple[int, bytes]]] | None:
    id = int.from_bytes(buffer[:1], "big")

    if id == 0x0:
        return None

    length = int.from_bytes(buffer[1:5], "big")

    buffer = buffer[5:]

    if len(buffer) < length:
        raise Exception("Buffer is too short")

    fields = []

    while len(buffer) > 0:
        fid, value = _deserialize_field(buffer)
        fields.append((fid, value))
        buffer = buffer[3 + len(value) :]

    return id, fields


# Returns the value of the first field with the given id
def _get_field(fields: list[tuple[int, bytes]], id: int) -> bytes:
    for field_id, value in fields:
        if field_id == id:
            return value
    return None


class APNSConnection:
    def __init__(self, private_key=None, cert=None):
        # Generate the private key and certificate if they're not provided
        if private_key is None or cert is None:
            self.private_key, self.cert = albert.generate_push_cert()
        else:
            self.private_key, self.cert = private_key, cert

        self.sock = courier.connect(self.private_key, self.cert)

    def connect(self, root: bool = True, token: bytes = None):
        flags = 0b01000001
        if root:
            flags |= 0b0100
        
        if token is None:
            payload = _serialize_payload(7, [(2, 0x01.to_bytes()), (5, flags.to_bytes(4))])
        else:
            payload = _serialize_payload(7, [(1, token), (2, 0x01.to_bytes()), (5, flags.to_bytes(4))])

        self.sock.write(payload)

        payload = _deserialize_payload(self.sock)

        if payload == None or payload[0] != 8 or _get_field(payload[1], 1) != 0x00.to_bytes():
            raise Exception("Failed to connect")
        
        self.token = _get_field(payload[1], 3)

        return self.token

    def filter(self, topics: list[str]):
        fields = [(1, self.token)]

        for topic in topics:
            fields.append((2, sha1(topic.encode()).digest()))

        payload = _serialize_payload(9, fields)

        self.sock.write(payload)
    """Field ID: 4
Field Value: b'A\xb9\xb9\xd6'
Field ID: 1
Field Value: b"\xe4\xe6\xd9R\x95Ah\xd0\xa5\xdb\x02\xdb\xaf'\xcc5\xfc\x18\xd1Y"
Field ID: 2
Field Value: b"\xe5^\xc0c\xe8\xa4\x1e\xbe\x03\x89'\xea\xd5m\x94\x05\xae\xf5\x1bqK\x1aJTH\xa4\xeb8\xb8<\xd7)"
Field ID: 3
Field Value: b'bplist00\xda\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10\x11\x0c\x126RsPSfcnQcQERuaQvQiScdvSdtlQU_\x10\x10tel:+16106632676\x10\x01\x10dWpair-ec_\x10#[macOS,13.2.1,22D68,MacBookPro18,3]\x10\x08\x12A\xb9\xb9\xd6\xa5\x13\x1e$*0\xd5\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1dRtPQDRsTQPQt_\x10\x10tel:+16106632676\x08O\x10$\x06\x01E\xf20\x9e\xe9\xa0\x9fT\xd9\x1b\xe1t\xfbBD\xd7e\x13|\xdbA\xc2\xf5^\x13\x05\xb5\x18V5\x13T\xa6\x81O\x11\x01e\n\xf4\x01<\x90]$\xff\xa1\xf2\xde\xe1\xaau\xfa\x87\xbc,+C\xddt\x97\xa0\\f\x8e\xec\xf3\x12C\t\x15ShAb{y\xed\xa4\x8c?\xcf\xf5\xbd\x88\xa4\xf7O\xa0\x9d\xad\x12J\\\xe9p4\xa8\x93d\xf9B\xf7\xcc\xde\xdd\xb6\x16`\xdbm\xd5\xe5\xfbiw\x91\x93m\x8f/\xa4\x92*\xf6\xb7\x1b\x8d\x03\x0f6\x1d\xd2J \xe0\xa6xP\xf1\xdd\xf8\x03Ud&\xc6\xb95\x82=\xc6\xd6`\x84J\xb6F\x8c\xa8\x8d\xa2\x1a\xaa\xf6=\xd1d\x99\xa5\xee\x95\xcd\x80[b\xac\xe0\xed-\x80\xb6LK:\x15}\x9a\xa5\xde\xc8b-\xed+l\x10\x8dr\x16\x10U\x8f\\\xde\xec\xb1\xa45\xdb\xf9%\xc1%\x86\xb2\xfbv.\n&\x87R\xcfw\x8b|g{IC\x0b\n4\xed_\xfc\x15tB\x19jp\xc9\xf0\x9b_\xb2\'\x16g\x98&\xe1\x01\xf3\xf6\x89[\x9d\xa3\xab\xb7\xc7\xe7\x85e\x9c\x1f\xabQ\xf5\xa5l\xd42\xd9\x91|\xe8&\'\x8dmD\x12 U\x15\xb8e\x07ISj\x1bf\x1a@\x16\xb4\x98?\x84z\xd3\x85\x94b\x1f\x05#\x96\xb6\xe6\x88\x12\xaa\x99\x1a@\xf5\x98\x7f\x08\xb8\xdd\xfdo\x1b\xcd\x0c\x07\x9f\xa4\xc9\xd7\xa2z\x8a\xd8\x12\xfa\n\xbc\xb0]\xb1\x9a\x01&\xd9\xd0e\xad\xb8\xf9\x1b\x15\x81\xff\xfa\x11T\rT\xa4\xa1Z\xb2#C\xe4\x1c+\x15Zv\x8e\xd8\x07d\xdf\x89\x17\x9a\x06\x07\rlF\xdc!\xb3\x0cO\x10 \x13\xd4\'\x15\x87\xcf\x8dk\xe1\xde\x17\xba^\x9d\xed\xffy\xf8\xa9H\xda\xbc\xf8\x89S\r;\x92\xc3\xcf\x88\xb6\xd5\x14\x15\x16\x17\x18\x1f !"#_\x10\x1amailto:jjgill07@icloud.com\tO\x10$\x06\x01ieR\x01\x88\x1d\xe7\xe4\x141\xbc\x00\xd2\xb7\x89\x86\x8b\xd1t\x87\x99&\rv\xbf}q\x00\xbe\xb0Q\xee\xf4\x05O\x11\x01e\n\xf4\x01\xcf\x85\xceZ@\xe8\xff\x06\x03)0\x10\x88N\x11\x80B\xa1\x9db\xb2\xe0*\xdc\xb9\t\x93r\x93\x9dj w\xa8#P\xdf}\x95\x0b\x9e\x17\x864\xee\xd0S\xe11c\x9e\xb2\xfewp\x9b\xa7\x83o\x8c\xa14\xd2\x99\x8e\xac\xb9rF\xa1\x8a-\xa9\xe3\x17\xcac(^\x12 \x95\xeaB`\x82\x1d\xf2\xed\x95C\x9d&\x06n\x1dN\xd5[\x9a\x83S\x87\x07\xd7\r\x15\x93\xd5\xa7\xa6\xa0\xddv\xd5\xdb\x9d\xe80\xec}+J\x84uEN\xc6\xd6F\xaf\x0b\x04\x11\xb5\x0b\xe4\x97\x1f]\xbaZ\x96q\xc5\x1bNu\xa8\xd6i\xc8\x8f\xdb\r\xff\xa0\xb7\xc7}Ow\xa1\xd5\x1b\xd3\xb1v\xb6&\xf2\x15\xdb\x10\xbb\xde\x87.W\xa4\xe5\x99\xeap\xf0A\x03\xd2\xdbY5\x01\rIf\xa7]\x00\xd0Kn\xff\x81\xc5\x0b\xb8\x17\xda\x00\xe3\xcf\x11\xdb\x7f\xb9\x16\xc1\x92\x08\xab\xc4\x955\xcb\xeb1&\x0b\xce\x07\xfa\xdb\xa0a\xe2M=q\xd9\xd1\xe1}\xb7\xac\x12 v\x89\xb5\xad\xf2=\x9a\x98\x82\x83\xb4U\x00\xe6\xb7\x11\xd0\xd5G"\xf7G#\x1c \x10\xfc\xe9\x13\xc1\x96c\x1a@\x01u\xc1\xbc\xdaL\xa5\x8a\xca\xee\xfc\x8a\xa6\xa1W\x85\x8aD{+\x16\xd5\xd0\x89\xf8\x07\xba\xfcWJ\xb3*\xd0\x9d\x94\x06:\x8cj[\xf2\xd7\xb6\xdf\xb0z\x17\xad\xe5R\x13S\xa9\xbc\xc0\x89}\x12\x03\xd9\xd1\xed\xdd\xce\x9a\x06\x07\rlF\xdc!\xb3\x0cO\x10 \x13\xd4\'\x15\x87\xcf\x8dk\xe1\xde\x17\xba^\x9d\xed\xffy\xf8\xa9H\xda\xbc\xf8\x89S\r;\x92\xc3\xcf\x88\xb6\xd5\x14\x15\x16\x17\x18% \'()_\x10\x1amailto:jjgill07@icloud.com\tO\x10$\x06\x01\xc0\xaf\xc0\x90\xa5{\xf2\x15\xa8\xb8\x8e\xf0\xf5\xbfL\x15\xc1\xef\x1cJ<\xa5<\x97\xdd\xa1\x0eU6j%Z\x99\xd0O\x11\x01e\n\xf4\x01\xfb\x80\xd1\xca\xc7l\xb58\xd3\x01\xb1\xaa\xcc\xc4\xc0\xaet\xb3:\xee\x14R32\x18\xe0\xfd^\xf1\x8b\xe3\x01\x18\x95\x17\xb6\x7f\x10=\xe5Dl\xb5\xdd*m\xd8\xf5"\x90\x89h+Bc\xad^\x13>\xaa\xcd\xc3p(\xfa\xb6\x03\x93\xad\x1e\x19\xcfkO\x16\xfce`\x95\x90\xa9\xb3\xbe\xf2/\xeeX\x03\x8d\xd5\xa2|\xed\xd9z>d|\xe2l*\xf1\xfaPU\xda\xc5\xb6\x9b=\x90i\xca\t\x9b\xd0K\xfe2^\x9e4o\xb0\xb8c\x86R\xe4Q+\x1e\xf5\xe2\x9eh\xa5\x9b\x8b}\xe9\xd2Zi\x1fS\xe1f \x1a\xe2rA\x842\xae\x06\xa4e\xc57\xd9E\x1a\x03\x02\x7fLP%\xec\xec\x07 \x97\xaf\x0cC&\xfa\x14*\xf4\x0e\xc9\xa26\x01\xfc\xdb\xcdu\x8c\x8d\x8b\xc0Y\xb4 T\xc5\x98Ps}\x8fp\xb4\x03\x0b\xe2&\xd5\x13\xd7\xdd\xd1F_-\x85\xe7\xa8f8 \xec*\x15^F\xbe\x95}\xa2\xac\x8cUr\t\xe4\x98\x0b\x04\x12 \xc9`e\r\xcd\xc8\xd5\xf3\xe9O\x88\xfd[t\x89\xd6\xbbS\xc2I\xdf\xfc\xe3\\\xcfC\x8a%q\x10\xe3T\x1a@\x8a\xeb\r\xd8\xcal\x19\xd2C\x14\x9b\xdc_\x82T\xe4\xf7fVc\xd9\xf39\xa9\xff\x9b\xc9\xb9\xf8%\xf9\xbb\x81\xda\xabE\x8di\xf5\xa2\xbd\x8fJ\xb9\xda\xfc\x11Jn\\\xab_[\xec6\\\x8btF\x14R\x0bX\x98\x9a\x06\x07\rl\rl\xad\xbd\x0cO\x10 \x9c\x1e\x96b\xa5\x15`\xec@C\t\x12\xb4,\xfam\x88\xaeTJ\xae\xb8\xb0\xa6Ypf\xab\xb9\xf3\xe2\x84\xd5\x14\x15\x16\x17\x18+\x1a-./_\x10\x10tel:+16106632676\x08O\x10$\x06\x01\xed\xcf\x17\x93\x05L\xd1\x9c\x89\xa0Cl\xdb-\x15O\x93\x8c\x05\xc1\xc2\xe4\x10\x86\xaf\x0422E\x96\xf1\xb6\xcc\xb7O\x11\x01e\n\xf4\x01]\xa96\xed;\xa3(v\xc2\x9e\xf4\x97\xfe_\xdds\xb7\x99y\xe7\xf0\xea\xf0\xc4\xb1\xdc\x9e\xb9u\x8cD\x1d\xcb\x8d\xe3:^\x0e!\xc3\xb9\xb4\x16Hz^k\x0e\xbc0\xec\xd7"\xba\x8e\x1ax\xe1$\xcf\xa3\x00U\x05\x11\xfe\x86]\xe8\x06/\xb7\xee\x0e\xe6(\xfc\xbd\x1fh6\xa5B\xe3\x14\xfb\x1b\xa8,\xb7\xe1\xe9\xd6gX\xfc\xd9+\xfc\x1d\xea\xc9\x05f}\x1a\xdbTa\x10^\xbb\xde\x1a\xe46O\x7f]x{u\xe2\x8b\x98\x01\xf1\xd0\x12x\xa2Vite;\xad1^\r\xf1\x12\x12\x9a\x96@\x11>\xe0\xabx\x99\xf0\x7f\xdcM\x12\x81g+\xf1\x87\xcbh\x9a\xf7;/\xbc\xe3b\xb5\x07\xa8\xef\xe6F\x16\xb3\xec\xdcnBnp\xbb\x07\xd1 \xee\x97\xd8\xbc\x86\x8e)\x82d0\xec\x94\xe9*i\xce\xf3Fy9\x00[\xea/g\xeb\xaa\xf2\xf3\x89\x8a\x07.DN\x99/\x98\xa5\xe5.\xb2\xb7\x95v\x1f-|\xe7\xbe`t+\xb4\xd2\x12 3r\x9aC\xab\xb4\xcb\x1e|\xaaFz?F\xc5*9\x9d\x95\xe3*\x7f|j]\x17\xad\x02\xe6H\'^\x1a@W\xff\xb7\xf5\xdcb\xba[\x06\n\xd7\x08eq\xfd,\xfd\xf6\xf8$\x9dq.\xf6\xf9wR\x85\xe2\rD\x17F\x01\xd0\x96\xad\xc2\xac\xdb\xde\xd18\xe3ed\xd2\xa13\xb2@\xba\x06\xcf\xe9q\xea\xc5M\x14[\xb7(\x9d\x9a\x06\x07\rl\rl\xad\xbd\x0cO\x10 \x9c\x1e\x96b\xa5\x15`\xec@C\t\x12\xb4,\xfam\x88\xaeTJ\xae\xb8\xb0\xa6Ypf\xab\xb9\xf3\xe2\x84\xd5\x14\x15\x16\x17\x181 345_\x10\x1amailto:jjgill07@icloud.com\tO\x10$\x06\x01\x97\xebO\x04\xc3\xfc\x96\xd0N$\x06\xd6\x12\xaal\x07|\xd1\x17P\xcc\xffI\xead\x03\xb7\xa6N\x9d\xc8\xa3\x7fNO\x11\x01e\n\xf4\x010\xab\xf5[~?\xa8 *=8=(pI\xd4\xc5\xb9\x16`\x83uN\xfeL\x99:^\xb6\xc7\xcc"\x14\xef\x84K;\x9d\xd2\xe0\xa9\x95\x93\xac\x88x3\xfa^\xfb\xb3\x93\xe0P!\xa4\xbeJ\xa7\xc5%\xc07\x13\xb6\xe5\xed5\xc4\x90\xa6\xa0\xfb\xef\x1f9!\x04$\xbai\x99\x95\x1e\x85\x00\xdf`\xa4{\xcd\x0e\x97\xd5\x1e9\xdfgZ\x07\xc6k:\xe8\xee\xbb\x12\x13j\xe8G\xa7C\xcb\nB\xe1\x85\xb0]hY\x8f\x00e\\\x89\xee\x9b2\xf7\xb5\x18\x03\x14\xc5\xb2\xde\xc8h\xc4\x08\x8d(b\xc1\x0bN\xf1\xb6\xd1S\x81\x9f\xbe\x97\xaeZOX\x81ov\xfbX<c]q\xf7\xbc\xd4\xd5H\x19\x8f\xe3\xc4k\xeaH~~\x84a\xd12\x86\xc5\xf5\xfa\x1e\x0f\xb6\xbf\xd3;\x07\xfb\x88Y\x9b\x04MB\xbb~\xda\xab\xb8Q\xa3lV\xc4_\xa4Xj\xbd\xf38\x9d\xb1\x82AyK\\\x1b\x85\xbd_\x87\x11t]\x00\xd9\xdft\xce\xdf\xfd\x12 \x85\xa62+\x1f\x87\x02^\xc4v\xdb\xe6_\x14!\xcbU\xa6\xb0\r\x85\xdfmd\xa1O\x847\xda\x80\xa7\xb9\x1a@\x1e\xb9G\xb1\x90_\x94U\xfb"\x9a\x14\xd7\xf5W\xec+9\xb3\xd1\xdc\xf1\xdd\xaf)\xb6\x9e\xeb\xd0\x06\x8fW\x08\xa9\xd0\x88Q\x97\x07\x80\x941_\r\x95\xea,)\xe1\xce4\x86\x0c\xec\x1f\xc7\xff<\xef\xdbuJ\x8a=\x9a\x06\x07\rl\rl\x06.\x0cO\x10 \xe5^\xc0c\xe8\xa4\x1e\xbe\x03\x89\'\xea\xd5m\x94\x05\xae\xf5\x1bqK\x1aJTH\xa4\xeb8\xb8<\xd7)O\x10\x10UC>\x9f\xce\xa4N\xe0\xba\xe9\xad\x8e_h\xd7h\x00\x08\x00\x1d\x00 \x00$\x00&\x00(\x00+\x00-\x00/\x003\x007\x009\x00L\x00N\x00P\x00X\x00~\x00\x80\x00\x85\x00\x8b\x00\x96\x00\x99\x00\x9b\x00\x9e\x00\xa0\x00\xa2\x00\xb5\x00\xb6\x00\xdd\x02F\x02i\x02t\x02\x91\x02\x92\x02\xb9\x04"\x04E\x04P\x04m\x04n\x04\x95\x05\xfe\x06!\x06,\x06?\x06@\x06g\x07\xd0\x07\xf3\x07\xfe\x08\x1b\x08\x1c\x08C\t\xac\t\xcf\x00\x00\x00\x00\x00\x00\x02\x01\x00\x00\x00\x00\x00\x00\x007\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\t\xe2'"""
    """
    Field ID: 4
Field Value: b'A\xb9\xb9\xd6'
Field ID: 1
Field Value: b"\xe4\xe6\xd9R\x95Ah\xd0\xa5\xdb\x02\xdb\xaf'\xcc5\xfc\x18\xd1Y"
Field ID: 2
Field Value: b"\xe5^\xc0c\xe8\xa4\x1e\xbe\x03\x89'\xea\xd5m\x94\x05\xae\xf5\x1bqK\x1aJTH\xa4\xeb8\xb8<\xd7)"
Field ID: 3
Field Value: b'bplist00\xdd\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x13\x17\x18\x19ScdrRtPRgdQiRsPRnrQcQUQtScdvRuaRqHQvM\x08\xd6\xf3\xe6\x8d\x04\x18\x95\xfd\xea\xe9\xf50_\x10\x10tel:+16106632676\t\x12=\x12c&_\x10\x1amailto:jjgill07@icloud.com\x10\x01\x10mO\x10\x10UC>\x9f\xce\xa4N\xe0\xba\xe9\xad\x8e_h\xd7hO\x10 \xe5^\xc0c\xe8\xa4\x1e\xbe\x03\x89\'\xea\xd5m\x94\x05\xae\xf5\x1bqK\x1aJTH\xa4\xeb8\xb8<\xd7)_\x10#[macOS,13.2.1,22D68,MacBookPro18,3]O\x10!\x01\x97\xca\\"\xcaI\x82\x0c\xb66C\xa7\x89h\x91\xcd\x18Ozj"\x06u;9\x96\xebrQs|=\x10\x08\x00\x08\x00#\x00\'\x00*\x00-\x00/\x002\x005\x007\x009\x00;\x00?\x00B\x00E\x00G\x00U\x00h\x00i\x00n\x00\x8b\x00\x8d\x00\x8f\x00\xa2\x00\xc5\x00\xeb\x01\x0f\x00\x00\x00\x00\x00\x00\x02\x01\x00\x00\x00\x00\x00\x00\x00\x1a\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x11'"""
    def send_message(self, token: bytes, topic: str, payload: str):
        # Current time in UNIX nanoseconds
        import time 
        # Expire in 5 minutes
        expiry = int(time.time()) + 500
        #print(sha1(topic.encode()).digest())
        payload = _serialize_payload(0x0a,
                                     [(4, b'A\xb9\xb9\xd7'),
                                      (1, sha1(topic.encode()).digest()),
                                      (2, token),
                                      (3, payload),])
        # payload = _serialize_payload(0x0a, 
        #                              [(1, sha1(topic.encode()).digest()),
        #                               (2, token),
        #                               (3, payload.encode("utf-8")),
        #                               (4, (3864024149).to_bytes(4, "big")),
        #                               (5, expiry.to_bytes(4, "big")),
        #                               (6, time.time_ns().to_bytes(8, "big")),
        #                               (7, 0x00.to_bytes()),
        #                               (0xf, self.token)])
        
        print(payload)
        
        self.sock.write(payload)

        payload = _deserialize_payload(self.sock)

        print(payload)


    # TODO: Find a way to make this non-blocking
    def expect_message(self) -> tuple[int, list[tuple[int, bytes]]] | None:
        return _deserialize_payload(self.sock)