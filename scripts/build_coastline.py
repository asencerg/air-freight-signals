"""Optional reproducible Natural Earth context builder; never runs at app startup."""
from pathlib import Path
import hashlib,json,urllib.request

REVISION='ca96624a56bd078437bca8184e78163e5039ad19'
URL=f'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/{REVISION}/geojson/ne_110m_coastline.geojson'
SOURCE_SHA256='851f581ff5ffb844deed8ae1a9ce22e3c4bb3d74fa342cadb5d8e39b41ae7c3c'
OUTPUT_SHA256='71e4ecd3dc5f2ee60b401440992fa3f49eef16ce98c3bb47b1a87c4dd1109e1b'


def compact(content):
    if hashlib.sha256(content).hexdigest()!=SOURCE_SHA256:raise ValueError('Unexpected coastline source bytes')
    lines=[]
    for feature in json.loads(content)['features']:
        geo=feature['geometry'];lines.extend([geo['coordinates']] if geo['type']=='LineString' else geo['coordinates'])
    encoded=json.dumps([[[round(x,3),round(y,3)] for x,y,*_ in line] for line in lines],separators=(',',':')).encode('utf-8')
    if hashlib.sha256(encoded).hexdigest()!=OUTPUT_SHA256:raise ValueError('Unexpected generated coastline')
    return encoded


if __name__=='__main__':
    data=urllib.request.urlopen(URL,timeout=30).read()
    destination=Path(__file__).resolve().parents[1]/'assets/coastlines-110m.json'
    destination.write_bytes(compact(data));print(destination,len(destination.read_bytes()),OUTPUT_SHA256)
