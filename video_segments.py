"""Read iPhone segment identifiers without decoding/re-encoding video."""
import json
import struct
import subprocess


def boxes(data):
    offset = 0
    while offset + 8 <= len(data):
        size, kind = struct.unpack_from('>I4s', data, offset)
        header = 8
        if size == 1:
            if offset + 16 > len(data):
                raise ValueError('truncated_atom')
            size = struct.unpack_from('>Q', data, offset + 8)[0]
            header = 16
        if size == 0:
            size = len(data) - offset
        if size < header or offset + size > len(data):
            raise ValueError('invalid_atom')
        yield kind, data[offset + header:offset + size]
        offset += size


def read_segments(path):
    moov = None
    with open(path, 'rb') as f:
        while True:
            h = f.read(8)
            if len(h) < 8:
                break
            size, kind = struct.unpack('>I4s', h)
            header = 8
            if size == 1:
                size = struct.unpack('>Q', f.read(8))[0]
                header = 16
            if size < header:
                break
            if kind == b'moov':
                if size > 128 * 1024 * 1024:
                    raise ValueError('metadata_too_large')
                moov = f.read(size - header)
                break
            f.seek(size - header, 1)
    if moov is None:
        return []
    track_id = None
    for kind, data in boxes(moov):
        if kind != b'trak' or b'com.apple.quicktime.segment-identifier' not in data:
            continue
        tkhd = next(v for k, v in boxes(data) if k == b'tkhd')
        track_id = struct.unpack_from('>I', tkhd, 20 if tkhd[0] == 1 else 12)[0]
        break
    if track_id is None:
        return []
    probe = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', path], capture_output=True, text=True, check=True, timeout=60)
    stream = next(s['index'] for s in json.loads(probe.stdout)['streams'] if int(s['id'], 0) == track_id)
    probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', str(stream), '-show_packets', '-show_data', '-of', 'json', path], capture_output=True, text=True, check=True, timeout=120)
    result = []
    for packet in json.loads(probe.stdout).get('packets', []):
        raw = b''.join(bytes.fromhex(line.split(': ', 1)[1].split('  ', 1)[0].replace(' ', '')) for line in packet['data'].strip().splitlines())
        identifier = raw[8:].decode('ascii')
        start = float(packet['pts_time'])
        end = start + float(packet['duration_time'])
        if result and result[-1]['segment_id'] == identifier:
            result[-1]['end'] = end
        else:
            result.append(dict(segment_id=identifier, start=start, end=end))
    return result
