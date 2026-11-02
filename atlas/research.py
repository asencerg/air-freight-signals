"""Corridor research presentation. Underlying analytical calculations stay in analysis.py."""
import calendar
import pandas as pd
from atlas.analysis import LB_PER_TONNE, LIMITATIONS, findings

RANKINGS = ['Freight growth', 'Freight contraction', 'Carrier structure', 'Full eligible universe']


def month_label(months):
    months = sorted(set(int(m) for m in months))
    return 'Jan–Dec' if months == list(range(1, 13)) else ', '.join(calendar.month_abbr[m] for m in months)


def corridor_records(evidence, rows, months):
    """One row per directed pair; positive-freight carrier activity is window-relative."""
    if evidence.empty:
        return evidence.copy()
    out = evidence.copy()
    out['market'] = out.origin + ' → ' + out.destination
    legacy = findings(evidence)
    signals = legacy.groupby('market').finding_type.agg(list).to_dict()
    keys = evidence[['origin', 'destination']].rename(columns={'origin':'ORIGIN', 'destination':'DEST'})
    selected = rows.loc[rows.MONTH.isin(months), ['ORIGIN','DEST','YEAR','MONTH','UNIQUE_CARRIER','FREIGHT']].merge(keys, on=['ORIGIN','DEST'], validate='many_to_one')
    monthly = selected.groupby(['ORIGIN', 'DEST', 'YEAR', 'MONTH']).FREIGHT.sum().unstack('YEAR')
    monthly['delta'] = monthly.get(2025, float('nan')) - monthly.get(2024, float('nan'))
    carriers = selected.groupby(['ORIGIN', 'DEST', 'UNIQUE_CARRIER', 'YEAR']).FREIGHT.sum().unstack('YEAR')
    # An absent carrier has no reported freight within a complete eligible market;
    # this does not impute missing months for corridor eligibility.
    carriers = carriers.reindex(columns=[2024, 2025]).fillna(0)
    carriers['delta'] = (carriers[2025] - carriers[2024]) / LB_PER_TONNE
    return attach_signals(out, monthly, carriers, months)


def attach_signals(out, monthly, carriers, months):
    signals = findings(out).groupby('market').finding_type.agg(list).to_dict()
    carrier_groups = {k: v.droplevel([0, 1]) for k, v in carriers.groupby(level=[0, 1])}
    month_groups = {k: v for k, v in monthly.groupby(level=[0, 1])}
    additions = []
    for r in out.to_dict('records'):
        key = (r['origin'], r['destination'])
        c, m = carrier_groups[key], month_groups[key]
        delta = r['tonnes_2025'] - r['tonnes_2024']
        newly = c[(c[2024] == 0) & (c[2025] > 0)].index.tolist()
        absent = c[(c[2024] > 0) & (c[2025] == 0)].index.tolist()
        lead = c['delta'].abs().idxmax()
        labels = list(signals.get(r['market'], []))
        if abs(r['departures_change_pct']) >= 15:
            labels.append('Departure change')
        if abs(r['tonnes_per_departure_change_pct']) >= 15:
            labels.append('Freight per departure change')
        if newly: labels.append('Newly observed carrier freight')
        if absent: labels.append('Disappearing carrier freight')
        additions.append(dict(
            absolute_change_tonnes=delta, magnitude_tonnes=abs(delta),
            comparison_size_tonnes=min(r['tonnes_2024'], r['tonnes_2025']),
            same_direction_months=int(((m.delta > 0) if delta > 0 else (m.delta < 0) if delta < 0 else (m.delta == 0)).sum()),
            compared_months=len(months), newly_observed=', '.join(newly), no_longer_observed=', '.join(absent),
            leading_carrier=str(lead), leading_carrier_change_tonnes=float(c.loc[lead, 'delta']),
            leading_carrier_net_contribution_pct=float(c.loc[lead, 'delta'] / delta * 100) if delta else float('nan'),
            signal_count=len(labels), signals='; '.join(labels),
            primary_issue=labels[0] if labels else 'Baseline observation',
            classification='Analytical observation',
        ))
    return pd.concat([out.reset_index(drop=True), pd.DataFrame(additions)], axis=1)


def rank_corridors(records, category='Freight growth', significant_only=True):
    if records.empty:
        return records.copy()
    r = records.copy()
    if category != 'Full eligible universe' and significant_only:
        r = r[r.comparison_size_tonnes >= 1000]
        if category != 'Carrier structure':
            r = r[r.magnitude_tonnes >= 500]
    if category == 'Freight growth':
        r = r[r.absolute_change_tonnes > 0]
    elif category == 'Freight contraction':
        r = r[r.absolute_change_tonnes < 0]
    elif category == 'Carrier structure':
        r = r[(r.hhi_change.abs() >= 500) | r.newly_observed.ne('') | r.no_longer_observed.ne('')]
    # Separate questions, no weighted score. Directional persistence resolves size ties.
    keys = ['comparison_size_tonnes', 'same_direction_months', 'magnitude_tonnes'] if category == 'Carrier structure' else ['magnitude_tonnes', 'same_direction_months', 'comparison_size_tonnes']
    return r.sort_values(keys + ['market'], ascending=[False, False, False, True]).reset_index(drop=True)


def airport_labels(airports):
    if airports is None or airports.empty:
        return {}
    safe = airports[airports.coordinate_match].dropna(subset=['name'])
    safe = safe[~safe.bts_code.duplicated(keep=False)]
    return dict(zip(safe.bts_code, safe.name))


def research_brief(r, names=None):
    names = names or {}
    origin = f"{names.get(r['origin'], r['origin'])} ({r['origin']})" if r['origin'] in names else r['origin']
    dest = f"{names.get(r['destination'], r['destination'])} ({r['destination']})" if r['destination'] in names else r['destination']
    change = r['absolute_change_tonnes']
    verb = 'increased' if change >= 0 else 'decreased'
    observation = f"Reported freight {verb} by {abs(change):,.0f} metric tonnes ({r['tonnes_change_pct']:+.1f}%). The annual-change direction also appears in {r['same_direction_months']} of {r['compared_months']} matched months."
    carrier = r['leading_carrier']
    if abs(r['hhi_change']) >= 500:
        interpretation = f"The reporting-carrier distribution on {r['market']} changed materially (HHI {r['hhi_change']:+,.0f}). Airport teams can investigate continuity of the reported carrier mix; HHI does not establish commercial control or customer choice."
        question = f"Does {carrier}'s {r['leading_carrier_change_tonnes']:+,.0f}-tonne change on {r['market']} coincide with dated schedule or aircraft/service-mix changes, and do the monthly carrier shares show a persistent shift?"
    elif abs(r['tonnes_per_departure_change_pct']) >= 15:
        interpretation = f"Freight per reported departure changed {r['tonnes_per_departure_change_pct']:+.1f}% on {r['market']}. Frequency alone does not explain the freight change; aircraft and service mix warrant comparison. This is not a load-factor estimate."
        question = f"Which aircraft types and service classes account for {carrier}'s {r['leading_carrier_change_tonnes']:+,.0f}-tonne change on {r['market']}, and does it persist within like-for-like classes?"
    else:
        interpretation = f"The measured {'increase' if change >= 0 else 'decline'} on {r['market']} provides a market-monitoring lead, not evidence of unmet demand or a revenue opportunity."
        question = f"Can published statistics at {r['origin']} and {r['destination']} corroborate the {abs(change):,.0f}-tonne segment change, particularly the {carrier} contribution, after accounting for through-routing?"
    return dict(title=f"{origin} → {dest}: {r['primary_issue']}", observation=observation,
                interpretation=interpretation, next_investigation=question,
                limitations='Matched reported months; freight excludes mail. New/absent carrier freight refers only to this comparison window. No inference of customers, capacity utilization or unmet demand.')


def evidence_table(r):
    return pd.DataFrame({'Metric':['Freight (metric tonnes)', 'Departures', 'Metric tonnes / departure', 'Carrier HHI'],
        '2024':[f"{r['tonnes_2024']:,.0f}",f"{r['departures_2024']:,.0f}",f"{r['tonnes_per_departure_2024']:,.2f}",f"{r['hhi_2024']:,.0f}"],
        '2025':[f"{r['tonnes_2025']:,.0f}",f"{r['departures_2025']:,.0f}",f"{r['tonnes_per_departure_2025']:,.2f}",f"{r['hhi_2025']:,.0f}"]})


def briefs_markdown(records, names=None, source='US DOT BTS T-100 Segment (All Carriers)'):
    parts = ['# Air Freight Signals corridor research', f'Source: {source}', LIMITATIONS]
    for r in records.to_dict('records'):
        b = research_brief(r, names)
        table = evidence_table(r)
        grid = '| Metric | 2024 | 2025 |\n|---|---:|---:|\n' + '\n'.join('| '+' | '.join(map(str,row))+' |' for row in table.itertuples(index=False,name=None))
        parts.append(f"## {b['title']}\n\nAnalytical observation · {month_label(r['months'].split(','))}\n\n### Observation\n{b['observation']}\n\n### Evidence\n{grid}\n\nSignals: {r['signals']}\n\n### Interpretation\n{b['interpretation']}\n\n### Next investigation\n{b['next_investigation']}\n\n### Limitations\n{b['limitations']}")
    return '\n\n'.join(parts)
