"""Artificial arithmetic fixtures for unit tests only; never application data."""
import pandas as pd


def generate():
    rows = []
    for year in (2024, 2025):
        for month in range(1, 13):
            for origin, dest, growth, shares in [('AAA', 'BBB', 1.45, (.5, .9)), ('CCC', 'DDD', .7, (.9, .5))]:
                total = 1000000 * (1 + month / 24) * (growth if year == 2025 else 1)
                top = shares[year - 2024]
                for carrier, share in [('DEMO1', top), ('DEMO2', 1 - top)]:
                    rows.append(dict(YEAR=year, MONTH=month, ORIGIN=origin, DEST=dest, UNIQUE_CARRIER=carrier,
                                     FREIGHT=round(total * share, 2), DEPARTURES_PERFORMED=50))
    return pd.DataFrame(rows)
