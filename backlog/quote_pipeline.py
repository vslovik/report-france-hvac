import pandas as pd
import matplotlib.pyplot as plt

from cohorts.cohorts import Cohorts


def plot_quote_pipeline(df_clean, start_date='2024-03-31', end_date=None):
    if end_date is None:
        end_date = Cohorts.LAST_DATE.strftime('%Y-%m-%d')

    snapshots = pd.date_range(start_date, end_date, freq='QE')
    snap_labels = [d.strftime('%Y Q') + str((d.month - 1) // 3 + 1) for d in snapshots]
    print("Snapshot dates:", [s.strftime('%Y-%m-%d') for s in snapshots])

    df_clean = df_clean.copy()
    df_clean['product'] = df_clean['regroup_famille_equipement_produit_principal'].map(Cohorts.map_product)

    main_diag = ['Boiler → Boiler', 'Stove → Stove', 'AC → AC', 'HP → HP']
    seg_colors = {
        'Boiler → Boiler': 'steelblue',
        'Stove → Stove':   'tomato',
        'AC → AC':         'mediumseagreen',
        'HP → HP':         'darkorange',
        'Other → HP':      'purple',
        'Boiler → HP':     'brown',
        'HP → Stove':      'pink',
        'AC → HP':         'olive',
        'HP → Boiler':     'grey'
    }

    thresholds = {
        'No threshold':    None,
        '12-month window': 365,
        '60-day window':   60
    }

    partial_idx = len(snap_labels) - 1  # last snapshot is always the current partial quarter

    fig, axes = plt.subplots(3, 2, figsize=(18, 18))
    fig.suptitle('Quote Pipeline Backlog — Threshold Comparison\n(Diagonal segments only)',
                 fontsize=14, fontweight='bold')

    for row, (thresh_label, days) in enumerate(thresholds.items()):
        for col, qtype in enumerate(['Single-quoter', 'Multi-quoter']):
            ax = axes[row, col]

            thresh_records = []
            for snap_date in snapshots:
                snap_quotes = df_clean[df_clean['dt_creation_devis'] <= snap_date].copy()

                if days is not None:
                    snap_quotes = snap_quotes[
                        snap_quotes['dt_creation_devis'] >= snap_date - pd.Timedelta(days=days)
                    ]

                converted_by_snap = snap_quotes.groupby('numero_compte')['fg_devis_accepte'].max()
                non_conv = converted_by_snap[converted_by_snap == 0].index

                # All quotes for those customers up to snapshot (not just in window)
                # to correctly determine first→last product journey
                all_quotes_to_snap = df_clean[
                    (df_clean['dt_creation_devis'] <= snap_date) &
                    (df_clean['numero_compte'].isin(non_conv))
                ]

                customer_snap = all_quotes_to_snap.groupby('numero_compte').agg(
                    first_product=('product', 'first'),
                    last_product=('product', 'last'),
                    n_quotes=('id_devis', 'count')
                ).reset_index()

                customer_snap['segment'] = customer_snap['first_product'] + ' → ' + customer_snap['last_product']
                customer_snap['quoter_type'] = customer_snap['n_quotes'].apply(
                    lambda x: 'Single-quoter' if x == 1 else 'Multi-quoter'
                )
                customer_snap['snap_label'] = snap_date.strftime('%Y Q') + str((snap_date.month - 1) // 3 + 1)
                thresh_records.append(customer_snap)

            thresh_pipeline = pd.concat(thresh_records, ignore_index=True)
            thresh_agg = (
                thresh_pipeline.groupby(['snap_label', 'segment', 'quoter_type'])
                .size()
                .reset_index(name='n_customers')
            )

            for seg in main_diag:
                d = thresh_agg[
                    (thresh_agg['quoter_type'] == qtype) &
                    (thresh_agg['segment'] == seg)
                ].set_index('snap_label').reindex(snap_labels)

                if d['n_customers'].isna().all():
                    continue

                ax.plot(snap_labels, d['n_customers'].values,
                        marker='o', linewidth=2.2, markersize=6,
                        color=seg_colors.get(seg, 'black'),
                        label=seg)

            ax.set_title(f'{thresh_label} — {qtype}', fontweight='bold', fontsize=10)



            ax.set_ylabel('Customers in pipeline')
            ax.set_xlabel('Quarter end')
            ax.tick_params(axis='x', rotation=30)
            ax.legend(fontsize=8)
            ax.grid(True, axis='y', alpha=0.3)
            ax.axvspan(partial_idx - 0.5, partial_idx + 0.5, alpha=0.08, color='orange')
            ax.text(partial_idx - 0.4, ax.get_ylim()[1] * 0.97, '⚠ partial',
                    fontsize=7.5, color='darkorange', va='top')

    plt.tight_layout()
    plt.savefig('pipeline_threshold_comparison.png', dpi=150, bbox_inches='tight')
    plt.show()
