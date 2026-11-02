"""Matched calendar-period comparisons; directed airport pairs."""
import pandas as pd

LB_PER_TONNE = 2204.62262185


def analyze(rows, months=tuple(range(1, 13)), min_departures=30, min_tonnes=100):
    months = sorted(set(months))
    if not months or not set(months) <= set(range(1, 13)):
        raise ValueError('Select at least one valid calendar month.')
    selected = rows[rows.MONTH.isin(months)]
    results, shares = [], []
    for (origin, dest), market in selected.groupby(['ORIGIN', 'DEST']):
        stats = {}
        for year in (2024, 2025):
            group = market[market.YEAR == year]
            if set(group.MONTH) != set(months):
                break
            freight = group.FREIGHT.sum()
            departures = group.DEPARTURES_PERFORMED.sum()
            if departures < min_departures or freight / LB_PER_TONNE < min_tonnes or departures <= 0 or freight <= 0:
                break
            carrier = group.groupby('UNIQUE_CARRIER').FREIGHT.sum() / freight
            stats[year] = dict(tonnes=freight / LB_PER_TONNE, departures=departures,
                               tonnes_per_departure=freight / LB_PER_TONNE / departures,
                               hhi=float((carrier ** 2).sum() * 10000), top_share=float(carrier.max()),
                               top_carrier=str(carrier.idxmax()))
            for name, share in carrier.items():
                shares.append(dict(origin=origin, destination=dest, year=year, carrier=name, share=share))
        if len(stats) != 2:
            continue
        result = dict(origin=origin, destination=dest, months=','.join(map(str, months)))
        for year, values in stats.items():
            result.update({f'{key}_{year}': value for key, value in values.items()})
        for key in ['tonnes', 'departures', 'tonnes_per_departure']:
            result[key + '_change_pct'] = (stats[2025][key] / stats[2024][key] - 1) * 100
        result['hhi_change'] = stats[2025]['hhi'] - stats[2024]['hhi']
        results.append(result)
    evidence = pd.DataFrame(results)
    shares = pd.DataFrame(shares)
    if not evidence.empty and not shares.empty:
        shares = shares.merge(evidence[['origin', 'destination']], on=['origin', 'destination'])
    else:
        shares = pd.DataFrame(columns=['origin', 'destination', 'year', 'carrier', 'share'])
    return evidence, shares


LIMITATIONS = ('Reported flight segments are not shipment origins/destinations. Freight per departure is not '
              'aircraft load factor. Changes do not prove unmet demand. Revisions, aircraft mix, service mix, '
              'routing and incomplete source extracts can affect results; mail is excluded.')


def findings(evidence, synthetic=False):
    output = []
    for r in evidence.to_dict('records'):
        types = []
        growth = r['tonnes_change_pct']
        if abs(growth) >= 15:
            types.append(('Freight growth' if growth > 0 else 'Freight contraction', abs(growth),
                          'Review whether shipper activity, routing or service changes explain the reported volume shift.'))
        gap = growth - r['departures_change_pct']
        if abs(gap) >= 15:
            types.append(('Freight–frequency divergence', abs(gap),
                          'Review aircraft and service mix before inferring changes in capacity utilization.'))
        if abs(r['hhi_change']) >= 500:
            types.append(('Concentration increase' if r['hhi_change'] > 0 else 'Diversification', abs(r['hhi_change']) / 100,
                          'Review carrier continuity and customer exposure to changes in the available services.'))
        if r['top_share_2025'] >= .8:
            types.append(('Carrier dependence', r['top_share_2025'] * 100,
                          'Investigate resilience to schedule changes by the dominant reporting carrier.'))
        for kind, score, relevance in types:
            output.append(dict(market=f"{r['origin']} → {r['destination']}", finding_type=kind,
                rank_score=round(score, 2), period=f"2024 versus 2025; calendar months {r['months']}",
                observation=(f"Freight {r['tonnes_2024']:,.1f} → {r['tonnes_2025']:,.1f} metric tonnes ({growth:+.1f}%); "
                    f"departures {r['departures_2024']:,.0f} → {r['departures_2025']:,.0f} ({r['departures_change_pct']:+.1f}%); "
                    f"tonnes/departure {r['tonnes_per_departure_2024']:.3f} → {r['tonnes_per_departure_2025']:.3f}. "
                    f"HHI {r['hhi_2024']:.0f} → {r['hhi_2025']:.0f}; top carrier "
                    f"{r['top_carrier_2024']} ({r['top_share_2024']:.1%}) → {r['top_carrier_2025']} ({r['top_share_2025']:.1%})."),
                commercial_relevance=relevance, limitations=LIMITATIONS,
                next_steps='Verify BTS extract coverage and revisions; inspect monthly and carrier evidence; corroborate with airport statistics and published schedules.',
                source='SYNTHETIC DEMONSTRATION — not empirical evidence' if synthetic else 'BTS T-100 Segment CSV (local input; coverage must be verified)'))
    columns = ['market', 'finding_type', 'rank_score', 'period', 'observation', 'commercial_relevance', 'limitations', 'next_steps', 'source']
    return pd.DataFrame(output, columns=columns).sort_values(['rank_score', 'market'], ascending=[False, True]).reset_index(drop=True)


def markdown(frame):
    return '# Air Freight Signals research findings\n\n' + '\n\n'.join(
        f"## {r.market}: {r.finding_type}\n\n" + '\n\n'.join(f'**{label}:** {getattr(r, key)}' for label, key in
        [('Source', 'source'), ('Period', 'period'), ('Observation', 'observation'), ('Commercial relevance', 'commercial_relevance'),
         ('Limitations', 'limitations'), ('Next research steps', 'next_steps')]) for r in frame.itertuples())
