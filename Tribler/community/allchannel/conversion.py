from struct import pack, unpack_from

from Tribler.Core.dispersy.bloomfilter import BloomFilter
from Tribler.Core.dispersy.encoding import encode, decode
from Tribler.Core.dispersy.message import DropPacket
from Tribler.Core.dispersy.conversion import BinaryConversion

if __debug__:
    from Tribler.Core.dispersy.dprint import dprint

class AllChannelConversion(BinaryConversion):
    def __init__(self, community):
        super(AllChannelConversion, self).__init__(community, "\x01")
        self.define_meta_message(chr(1), community.get_meta_message(u"channelcast"), self._encode_channelcast, self._decode_channelcast)
        self.define_meta_message(chr(2), community.get_meta_message(u"channelcast-request"), self._encode_channelcast, self._decode_channelcast)
        self.define_meta_message(chr(3), community.get_meta_message(u"votecast"), self._encode_votecast, self._decode_votecast)

        self._address = ("", -1)

    def _encode_channelcast(self, message):
        packet = encode(message.payload.torrents)
        return packet,

    def _decode_channelcast(self, placeholder, offset, data):
        try:
            offset, payload = decode(data, offset)
        except ValueError:
            raise DropPacket("Unable to decode the channelcast-payload")
        return offset, placeholder.meta.payload.implement(payload)
    
    def _encode_votecast(self, message):
        return pack('!20shl', message.payload.cid, message.payload.vote, message.payload.timestamp),
    
    def _decode_votecast(self, placeholder, offset, data):
        if len(data) < offset + 26:
            raise DropPacket("Unable to decode the payload")
        
        cid, vote, timestamp = unpack_from('!20shl', data, offset)
        if not vote in [-1, 2]:
            raise DropPacket("Invalid 'vote' type or value")
        
        return offset, placeholder.meta.payload.implement(cid, vote, timestamp)

    def _encode_channel_search_request(self, message):
        skip = str(message.payload.skip)
        return encode({"skip":str(message.payload.skip),
                       "search":message.payload.search,
                       "method":message.payload.method}),

    def _decode_channel_search_request(self, placeholder, offset, data):
        try:
            offset, dic = decode(data, offset)
        except ValueError:
            raise DropPacket("Unable to decode the payload")

        if not isinstance(dic, dict):
            raise DropPacket("Invalid payload type")

        if not "skip" in dic:
            raise DropPacket("Missing 'skip'")
        try:
            skip = BloomFilter(dic["skip"], 0)
        except ValueError:
            raise DropPacket("Unable to decode the skip bloomfilter")

        if not "method" in dic:
            raise DropPacket("Missing 'method'")
        method = dic["method"]
        if not (isinstance(method, unicode) and method in (u"simple-any-keyword", u"simple-all-keywords")):
            raise DropPacket("Invalid 'method' type or value")

        if not "search" in dic:
            raise DropPacket("Missing 'search'")
        search = dic["search"]
        if not isinstance(search, (tuple, list)):
            raise DropPacket("'search' has invalid type")
        for item in search:
            if not isinstance(item, unicode):
                raise DropPacket("Item in 'search' has invalid type")

        return offset, placeholder.meta.payload.implement(skip, search, method)

    def _encode_channel_search_response(self, message):
        return encode({"request-identifier":message.payload.request_identifier,
                       "messages":[message.packet for message in message.payload.messages]}),

    def _decode_channel_search_response(self, placeholder, offset, data):
        try:
            offset, dic = decode(data, offset)
        except ValueError:
            raise DropPacket("Unable to decode the payload")

        if not isinstance(dic, dict):
            raise DropPacket("Invalid payload type")

        if not "request_identifier" in dic:
            raise DropPacket("Missing 'request-identifier'")
        request_identifier = dic["request-identifier"]
        if not (isinstance(request_identifier, str) and len(request_identifier) == 20):
            raise DropPacket("Invalid 'request-identifier' type or value")

        if not "messages" in dic:
            raise DropPacket("Missing 'messages'")
        messages = dic["messages"]
        if not isinstance(messages, list):
            raise DropPacket("Invalid 'messages' type")
        for message in messages:
            if not isinstance(message, str):
                raise DropPacket("Item in 'messages' has invalid type")
        messages = map(self.decode_message, messages)

        return offset, placeholder.meta.payload.implement(request_identifier, messages)

    # def _encode_torrent_request(self, message):
    #     return message.payload.infohash,

    # def _decode_torrent_request(self, placeholder, offset, data):
    #     if len(data) < offset + 20:
    #         raise DropPacket("Insufficient packet size")

    #     infohash = data[offset:offset+20]
    #     offset += 20

    #     return offset, placeholder.meta.payload.implement(infohash)

    def decode_message(self, address, data):
        self._address = address
        return super(AllChannelConversion, self).decode_message(address, data)