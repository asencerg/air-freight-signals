"""Explicit OurAirports joins: BTS airport code → unique IATA only, country checked."""
import io
import pandas as pd


def _read(content):
    return pd.read_csv(io.BytesIO(content), dtype=str, keep_default_na=False)


def reference_metadata(airports, regions, countries):
    a, r, c = map(_read, [airports, regions, countries])
    for frame, fields in [(a, {'iata_code','ident','name','iso_country','iso_region','latitude_deg','longitude_deg'}),
                          (r, {'code','name','iso_country'}), (c, {'code','name'})]:
        if not fields <= set(frame):
            raise ValueError('Missing OurAirports fields: ' + ', '.join(sorted(fields-set(frame))))
    for frame in [r,c]:
        if frame.code.eq('').any() or frame.code.duplicated().any():
            raise ValueError('Reference country/region codes must be nonempty and unique.')
    a['iata_code'] = a.iata_code.str.strip().str.upper()
    a['iata_ambiguous'] = a.iata_code.ne('') & a.iata_code.duplicated(keep=False)
    a = a.merge(c[['code','name']].rename(columns={'code':'iso_country','name':'country_name'}),
                on='iso_country', how='left', validate='many_to_one')
    a = a.merge(r[['code','name','iso_country']].rename(columns={'code':'iso_region','name':'region_name','iso_country':'region_country'}),
                on='iso_region', how='left', validate='many_to_one')
    a['region_consistent'] = a.region_country.eq(a.iso_country)
    a.loc[~a.region_consistent, 'region_name'] = pd.NA
    for col in ['latitude_deg','longitude_deg']:
        a[col] = pd.to_numeric(a[col], errors='coerce')
    a['coordinates_valid'] = a.latitude_deg.between(-90,90) & a.longitude_deg.between(-180,180)
    a.loc[~a.coordinates_valid, ['latitude_deg','longitude_deg']] = float('nan')
    return a


def match_airports(rows, reference):
    required = {'ORIGIN','DEST','ORIGIN_COUNTRY','DEST_COUNTRY'}
    if not required <= set(rows):
        raise ValueError('Country-checked airport matching requires BTS ORIGIN_COUNTRY and DEST_COUNTRY.')
    endpoints = pd.concat([
        rows[['ORIGIN','ORIGIN_COUNTRY']].rename(columns={'ORIGIN':'bts_code','ORIGIN_COUNTRY':'bts_country'}),
        rows[['DEST','DEST_COUNTRY']].rename(columns={'DEST':'bts_code','DEST_COUNTRY':'bts_country'})
    ], ignore_index=True).drop_duplicates()
    unique = reference[reference.iata_code.ne('') & ~reference.iata_ambiguous]
    result = endpoints.merge(unique, left_on='bts_code', right_on='iata_code', how='left', validate='many_to_one')
    ambiguous = set(reference.loc[reference.iata_ambiguous,'iata_code'])
    result['match_status'] = 'matched_iata_country'
    result.loc[result.ident.isna(),'match_status'] = 'unmatched_iata'
    result.loc[result.bts_code.isin(ambiguous),'match_status'] = 'ambiguous_iata'
    conflict = result.ident.notna() & result.bts_country.ne(result.iso_country)
    result.loc[conflict,'match_status'] = 'country_conflict'
    result['coordinate_match'] = result.match_status.eq('matched_iata_country') & result.coordinates_valid.eq(True)
    result.loc[~result.coordinate_match,['latitude_deg','longitude_deg']] = float('nan')
    return result
