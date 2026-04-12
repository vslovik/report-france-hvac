import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import pandas as pd


def plot_cohort_curves(df: pd.DataFrame):
    df_sorted = df.sort_values(['numero_compte', 'dt_creation_devis'])

    # First and last product per customer
    journey = df_sorted.groupby('numero_compte').agg(
        first_quote_date=('dt_creation_devis', 'first'),
        last_quote_date=('dt_creation_devis', 'last'),
        first_product=('regroup_famille_equipement_produit_principal', 'first'),
        last_product=('regroup_famille_equipement_produit_principal', 'last'),
        converted=('fg_devis_accepte', 'max'),
        total_quotes=('id_devis', 'count'),
        decision_days=('dt_creation_devis', lambda x: (x.max() - x.min()).days)
    ).reset_index()

    # Build journey label
    journey['segment'] = journey['first_product'] + ' → ' + journey['last_product']

    # Summary
    print(journey['segment'].value_counts())
    print(f"\nTotal customers: {len(journey):,}")
    print(f"Multi-product journeys: {(journey['first_product'] != journey['last_product']).sum():,}")

    # Focus on the 4 main diagonal segments
    main_segments = ['BOILER_GAS → BOILER_GAS', 'STOVE → STOVE',
                     'AIR_CONDITIONER → AIR_CONDITIONER', 'HEAT_PUMP → HEAT_PUMP']

    labels = {
        'BOILER_GAS → BOILER_GAS': 'Boiler',
        'STOVE → STOVE': 'Stove',
        'AIR_CONDITIONER → AIR_CONDITIONER': 'AC',
        'HEAT_PUMP → HEAT_PUMP': 'Heat Pump'
    }

    # Build weekly cohorts per segment
    journey['cohort_week'] = journey['first_quote_date'].dt.to_period('W').dt.start_time
    journey['year'] = journey['first_quote_date'].dt.year

    cohort_seg = (
        journey[journey['segment'].isin(main_segments)]
        .groupby(['segment', 'cohort_week'])
        .agg(
            total=('numero_compte', 'count'),
            converted=('converted', 'sum'),
            avg_decision_days=('decision_days', 'mean')
        )
        .reset_index()
    )
    cohort_seg['conversion_rate'] = cohort_seg['converted'] / cohort_seg['total'] * 100

    # Rolling average (4-week) per segment
    cohort_seg = cohort_seg.sort_values(['segment', 'cohort_week'])
    cohort_seg['conv_roll4'] = (
        cohort_seg.groupby('segment')['conversion_rate']
        .transform(lambda x: x.rolling(4, center=True, min_periods=2).mean())
    )
    cohort_seg['days_roll4'] = (
        cohort_seg.groupby('segment')['avg_decision_days']
        .transform(lambda x: x.rolling(4, center=True, min_periods=2).mean())
    )

    # Mark incomplete cohorts (last 12 weeks)
    cutoff = journey['cohort_week'].max() - pd.Timedelta(weeks=12)
    cohort_seg['incomplete'] = cohort_seg['cohort_week'] > cutoff

    colors = {
        'BOILER_GAS → BOILER_GAS': 'steelblue',
        'STOVE → STOVE': 'tomato',
        'AIR_CONDITIONER → AIR_CONDITIONER': 'mediumseagreen',
        'HEAT_PUMP → HEAT_PUMP': 'darkorange'
    }

    fig, axes = plt.subplots(2, 1, figsize=(16, 10))
    fig.suptitle('Weekly Cohort Curves by Product Segment', fontsize=14, fontweight='bold')

    for seg in main_segments:
        data = cohort_seg[cohort_seg['segment'] == seg]
        complete = data[~data['incomplete']]
        incompl = data[data['incomplete']]
        color = colors[seg]
        label = labels[seg]

        for ax, metric, roll in zip(axes, ['conversion_rate', 'avg_decision_days'], ['conv_roll4', 'days_roll4']):
            # Raw dots
            ax.scatter(complete['cohort_week'], complete[metric],
                       s=12, alpha=0.3, color=color)
            # Rolling avg — complete
            ax.plot(complete['cohort_week'], complete[roll],
                    color=color, linewidth=2, label=label)
            # Rolling avg — incomplete (dashed)
            ax.plot(incompl['cohort_week'], incompl[roll],
                    color=color, linewidth=1.5, linestyle='--', alpha=0.6)

    # Panel 1: Conversion rate
    axes[0].set_title('Conversion Rate (4-week rolling avg)', fontsize=11, loc='left')
    axes[0].set_ylabel('Conversion Rate')
    axes[0].yaxis.set_major_formatter(mtick.PercentFormatter())
    axes[0].legend(fontsize=9)
    axes[0].grid(True, axis='y', alpha=0.3)
    axes[0].tick_params(labelbottom=False)

    # Panel 2: Decision days
    axes[1].set_title('Avg Decision Days (4-week rolling avg)', fontsize=11, loc='left')
    axes[1].set_ylabel('Days to Convert')
    axes[1].legend(fontsize=9)
    axes[1].grid(True, axis='y', alpha=0.3)
    axes[1].tick_params(axis='x', rotation=30)

    # Shade incomplete zone on both panels
    for ax in axes:
        ax.axvspan(cutoff, journey['cohort_week'].max(),
                   alpha=0.07, color='orange')
        ax.text(cutoff, ax.get_ylim()[1] * 0.97, '  ⚠ incomplete',
                fontsize=7.5, color='darkorange', va='top')

    plt.tight_layout()
    plt.savefig('cohort_curves_by_segment.png', dpi=150, bbox_inches='tight')
    plt.show()