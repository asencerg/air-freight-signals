"""Reproduce the compact offline Natural Earth land fill from a pinned source."""
from pathlib import Path
import hashlib,json,urllib.request

REVISION='ca96624a56bd078437bca8184e78163e5039ad19'
URL=f'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/{REVISION}/geojson/ne_110m_land.geojson'
SOURCE_SHA256='9e0729ee253ca7d7a5c4ae9395fb1902264c5377c52e224d13dd85010e2835d9'
OUTPUT_SHA256='4f6e9a66f41aaefb0d2693b4d112abdb440b26186c92727e70abee7cdfc7d566'


def compact(content):
    if hashlib.sha256(content).hexdigest()!=SOURCE_SHA256:raise ValueError('Unexpected land source bytes')
    rings=[]
    for feature in json.loads(content)['features']:
        g=feature['geometry'];polygons=[g['coordinates']] if g['type']=='Polygon' else g['coordinates']
        for polygon in polygons:rings.append([[round(x,3),round(y,3)] for x,y,*_ in polygon[0]])
    result=json.dumps(rings,separators=(',',':')).encode('utf-8')
    if hashlib.sha256(result).hexdigest()!=OUTPUT_SHA256:raise ValueError('Unexpected compact land bytes')
    return result


if __name__=='__main__':
    content=urllib.request.urlopen(URL,timeout=30).read()
    destination=Path(__file__).resolve().parents[1]/'assets/land-110m.json'
    destination.write_bytes(compact(content));print(destination.name,len(destination.read_bytes()),OUTPUT_SHA256)
