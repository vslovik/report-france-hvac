from datetime import date

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd

from util.quarter import last_n_quarters_label


class WeeklyCohorts:
    # Focus on the 4 main diagonal segments
    MAIN_SEGMENTS = ['BOILER_GAS → BOILER_GAS', 'STOVE → STOVE',
                     'AIR_CONDITIONER → AIR_CONDITIONER', 'HEAT_PUMP → HEAT_PUMP']

    MAIN_SEGMENT_LABELS = {
        'BOILER_GAS → BOILER_GAS': 'Boiler',
        'STOVE → STOVE': 'Stove',
        'AIR_CONDITIONER → AIR_CONDITIONER': 'AC',
        'HEAT_PUMP → HEAT_PUMP': 'Heat Pump'
    }

    MAIN_SEGMENT_COLORS = {
        'BOILER_GAS → BOILER_GAS': 'steelblue',
        'STOVE → STOVE': 'tomato',
        'AIR_CONDITIONER → AIR_CONDITIONER': 'mediumseagreen',
        'HEAT_PUMP → HEAT_PUMP': 'darkorange'
    }

    # Top 4 switcher segments only
    TOP_SWITCHERS = [
        'HEAT_PUMP → OTHER',
        'OTHER → HEAT_PUMP',
        'BOILER_GAS → HEAT_PUMP',
        'HEAT_PUMP → STOVE'
    ]

    TOP_SWITCHER_COLORS = {
        'HEAT_PUMP → OTHER': 'darkorange',
        'OTHER → HEAT_PUMP': 'steelblue',
        'BOILER_GAS → HEAT_PUMP': 'mediumseagreen',
        'HEAT_PUMP → STOVE': 'tomato'
    }

    QUARTERS_TO_SHOW = 5

    QUARTERS_COLORS = [
        'steelblue',
        'mediumseagreen',
        'darkorange',
        'tomato',
        'purple'
    ]

    MAX_WEEKS = 24
    MIN_CUSTOMERS = 50  # minimum per agency×product to plot

    DIAGONAL_MAP = {
        'Boiler': 'BOILER_GAS → BOILER_GAS',
        'Stove': 'STOVE → STOVE',
        'AC': 'AIR_CONDITIONER → AIR_CONDITIONER',
        'HP': 'HEAT_PUMP → HEAT_PUMP'
    }

    def __init__(self, df: pd.DataFrame):
        self.journey = self.get_journey(df)
        self.journey_excl = self.get_journey__exclude_agencies(df)
        self.journey_agency = self.get_journey_agency(df)
        self.journey_agency_process = self.get_journey_agency_process(df)
        self.new_process = df.groupby('nom_agence').agg(
            first_new_process=('dt_creation_devis',
                               lambda x: x[df.loc[x.index, 'fg_nouveau_process_relance_devis'] == 1].min()),
        ).reset_index()

        self.switchers = self.get_switchers(self.journey)
        self.quarters_to_plot = last_n_quarters_label(self.QUARTERS_TO_SHOW, date(2026, 3, 31))
        self.quarters_colors = dict(zip(self.quarters_to_plot, self.QUARTERS_COLORS))

    # Helper: assign week-within-quarter
    @classmethod
    def week_in_quarter(cls, date_series):
        quarter_start = date_series.dt.to_period('Q').dt.start_time
        return ((date_series - quarter_start) / pd.Timedelta(weeks=1)).astype(int) + 1

    @classmethod
    def get_journey(cls, df: pd.DataFrame) -> pd.DataFrame:
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

        # Build weekly cohorts per segment
        journey['cohort_week'] = journey['first_quote_date'].dt.to_period('W').dt.start_time
        journey['year'] = journey['first_quote_date'].dt.year

        journey['week_in_q'] = cls.week_in_quarter(journey['first_quote_date'])
        journey['quarter_label'] = journey['first_quote_date'].dt.year.astype(str) + ' Q' + journey['first_quote_date'].dt.quarter.astype(
            str)

        journey['cohort_month'] = journey['first_quote_date'].dt.to_period('M')

        # ToDo
        journey['product'] = journey['first_product'].map({
            'BOILER_GAS': 'Boiler',
            'STOVE': 'Stove',
            'AIR_CONDITIONER': 'AC',
            'HEAT_PUMP': 'Heat Pump'
        })

        # Summary
        print(journey['segment'].value_counts())
        print(f"\nTotal customers: {len(journey):,}")
        print(f"Multi-product journeys: {(journey['first_product'] != journey['last_product']).sum():,}")

        return journey

    @classmethod
    def get_journey_agency(cls, df: pd.DataFrame) -> pd.DataFrame:
        # Add agency to journey from raw quotes
        agency_per_customer = (
            df.sort_values('dt_creation_devis')
            .groupby('numero_compte')['nom_agence']
            .first()
            .reset_index()
            .rename(columns={'nom_agence': 'main_agency'})
        )
        journey = cls.get_journey(df)
        journey_agency = journey.merge(agency_per_customer, on='numero_compte', how='left')
        journey_agency['cohort_month'] = journey_agency['first_quote_date'].dt.to_period('M')
        journey_agency['conv_week'] = np.where(
            journey_agency['decision_days'] == 0, 0,
            np.ceil(journey_agency['decision_days'] / 7).astype(int)
        )

        return journey_agency

    @classmethod
    def get_journey_agency_process(cls, df: pd.DataFrame) -> pd.DataFrame:
        journey_agency = cls.get_journey_agency(df)

        # Add process flag to journey_agency
        # Get dominant process flag per customer (max = if any quote was new process)
        process_per_customer = (
            df.groupby('numero_compte')['fg_nouveau_process_relance_devis']
            .max()
            .reset_index()
            .rename(columns={'fg_nouveau_process_relance_devis': 'new_process'})
        )
        journey_agency_process = journey_agency.merge(process_per_customer, on='numero_compte', how='left')

        return journey_agency_process

    @classmethod
    def get_journey__exclude_agencies(cls, df: pd.DataFrame):
        def map_product(val):
            if pd.isna(val):
                return 'Other'
            v = str(val).upper()
            if 'HEAT_PUMP' in v:   return 'HP'
            if 'BOILER_GAS' in v:  return 'Boiler'
            if 'AIR_CONDITIONER' in v: return 'AC'
            if 'STOVE' in v:       return 'Stove'
            return 'Other'

        # Exclude late-onboarding agencies
        late_agencies = ['Lepretre', 'SMT Energies', 'GD Energies']

        df_excl = df[~df['nom_agence'].isin(late_agencies)].copy()
        df_excl['product'] = df_excl['regroup_famille_equipement_produit_principal'].map(map_product)

        print(f"Full dataset:     {df['numero_compte'].nunique():,} customers")
        print(f"Excluding 3 LBCs: {df_excl['numero_compte'].nunique():,} customers")
        print(
            f"Removed:          {df['numero_compte'].nunique() - df_excl['numero_compte'].nunique():,} customers")

        # Rebuild journey for excluded dataset
        df_excl_sorted = df_excl.sort_values(['numero_compte', 'dt_creation_devis'])

        journey_excl = df_excl_sorted.groupby('numero_compte').agg(
            first_quote_date=('dt_creation_devis', 'first'),
            last_quote_date=('dt_creation_devis', 'last'),
            first_product=('product', 'first'),
            last_product=('product', 'last'),
            converted=('fg_devis_accepte', 'max'),
            decision_days=('dt_creation_devis', lambda x: (x.max() - x.min()).days)
        ).reset_index()

        journey_excl['segment'] = journey_excl['first_product'] + ' → ' + journey_excl['last_product']
        journey_excl['cohort_month'] = journey_excl['first_quote_date'].dt.to_period('M')
        journey_excl['conv_week'] = np.where(
            journey_excl['decision_days'] == 0, 0,
            np.ceil(journey_excl['decision_days'] / 7).astype(int)
        )

        return journey_excl

    @classmethod
    def get_switchers(cls, journey: pd.DataFrame) -> pd.DataFrame:
        # Switcher segments with >50 customers
        switchers = journey[journey['first_product'] != journey['last_product']].copy()

        # Filter meaningful segments
        switcher_counts = switchers['segment'].value_counts()
        meaningful = switcher_counts[switcher_counts > 50].index.tolist()

        print(switcher_counts[switcher_counts > 50])
        print(f"\nTotal switcher segments to plot: {len(meaningful)}")

        # Build weekly cohorts per switcher segment
        switchers['cohort_week'] = switchers['first_quote_date'].dt.to_period('W').dt.start_time

        # Monthly cohorts
        switchers['cohort_month'] = switchers['first_quote_date'].dt.to_period('M').dt.start_time
        switchers['week_in_q'] = cls.week_in_quarter(switchers['first_quote_date'])
        switchers['quarter_label'] = switchers['first_quote_date'].dt.year.astype(str) + ' Q' + switchers['first_quote_date'].dt.quarter.astype(
            str)

        return switchers

    def plot_weekly_cohorts_performance_trend__single_quoters(self):
        cohort_seg = (
            self.journey[self.journey['segment'].isin(self.MAIN_SEGMENTS)]
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
        cutoff = self.journey['cohort_week'].max() - pd.Timedelta(weeks=12)
        cohort_seg['incomplete'] = cohort_seg['cohort_week'] > cutoff

        fig, axes = plt.subplots(2, 1, figsize=(16, 10))
        fig.suptitle('Weekly Cohort Curves by Product Segment', fontsize=14, fontweight='bold')

        for seg in self.MAIN_SEGMENTS:
            data = cohort_seg[cohort_seg['segment'] == seg]
            complete = data[~data['incomplete']]
            incompl = data[data['incomplete']]
            color = self.MAIN_SEGMENT_COLORS[seg]
            label = self.MAIN_SEGMENT_LABELS[seg]

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
            ax.axvspan(cutoff, self.journey['cohort_week'].max(),
                       alpha=0.07, color='orange')
            ax.text(cutoff, ax.get_ylim()[1] * 0.97, '  ⚠ incomplete',
                    fontsize=7.5, color='darkorange', va='top')

        plt.tight_layout()
        plt.savefig('pipeline_data/cohort_curves_by_segment.png', dpi=150, bbox_inches='tight')
        plt.show()

    def plot_weekly_cohorts_performance_trend__switchers(self):
        cohort_sw_m = (
            self.switchers[self.switchers['segment'].isin(self.TOP_SWITCHERS)]
            .groupby(['segment', 'cohort_month'])
            .agg(
                total=('numero_compte', 'count'),
                converted=('converted', 'sum'),
                avg_decision_days=('decision_days', 'mean')
            )
            .reset_index()
        )
        cohort_sw_m['conversion_rate'] = cohort_sw_m['converted'] / cohort_sw_m['total'] * 100

        # Rolling avg (3-month)
        cohort_sw_m = cohort_sw_m.sort_values(['segment', 'cohort_month'])
        cohort_sw_m['conv_roll3'] = (
            cohort_sw_m.groupby('segment')['conversion_rate']
            .transform(lambda x: x.rolling(3, center=True, min_periods=2).mean())
        )
        cohort_sw_m['days_roll3'] = (
            cohort_sw_m.groupby('segment')['avg_decision_days']
            .transform(lambda x: x.rolling(3, center=True, min_periods=2).mean())
        )

        # Incomplete = last 3 months
        cutoff_m = self.switchers['cohort_month'].max() - pd.DateOffset(months=3)
        cohort_sw_m['incomplete'] = cohort_sw_m['cohort_month'] > cutoff_m

        fig, axes = plt.subplots(2, 1, figsize=(16, 10))
        fig.suptitle('Monthly Cohort Curves — Top 4 Switcher Segments', fontsize=14, fontweight='bold')

        for seg in self.TOP_SWITCHERS:
            data = cohort_sw_m[cohort_sw_m['segment'] == seg]
            complete = data[~data['incomplete']]
            incompl = data[data['incomplete']]
            color = self.TOP_SWITCHER_COLORS[seg]
            label = seg.replace('_', ' ')
            n = int(self.switchers[self.switchers['segment'] == seg]['numero_compte'].count())

            for ax, metric, roll in zip(axes,
                                        ['conversion_rate', 'avg_decision_days'],
                                        ['conv_roll3', 'days_roll3']):
                ax.scatter(complete['cohort_month'], complete[metric],
                           s=25, alpha=0.35, color=color)
                ax.plot(complete['cohort_month'], complete[roll],
                        color=color, linewidth=2.2, label=f'{label}  (n={n})')
                ax.plot(incompl['cohort_month'], incompl[roll],
                        color=color, linewidth=1.5, linestyle='--', alpha=0.6)

        axes[0].set_title('Conversion Rate (3-month rolling avg)', fontsize=11, loc='left')
        axes[0].set_ylabel('Conversion Rate')
        axes[0].yaxis.set_major_formatter(mtick.PercentFormatter())
        axes[0].legend(fontsize=9)
        axes[0].grid(True, axis='y', alpha=0.3)
        axes[0].tick_params(labelbottom=False)

        axes[1].set_title('Avg Decision Days (3-month rolling avg)', fontsize=11, loc='left')
        axes[1].set_ylabel('Days to Convert')
        axes[1].legend(fontsize=9)
        axes[1].grid(True, axis='y', alpha=0.3)
        axes[1].tick_params(axis='x', rotation=30)

        for ax in axes:
            ax.axvspan(cutoff_m, self.switchers['cohort_month'].max(),
                       alpha=0.07, color='orange')
            ax.text(cutoff_m, ax.get_ylim()[1] * 0.97, '  ⚠ incomplete',
                    fontsize=7.5, color='darkorange', va='top')

        plt.tight_layout()
        plt.savefig('pipeline_data/cohort_curves_top_switchers.png', dpi=150, bbox_inches='tight')
        plt.show()

    def plot_quarters_report(self):
        # Assign quarter label
        for d in [self.journey, self.switchers]:
            d['quarter_label'] = d['first_quote_date'].dt.year.astype(str) + ' Q' + d[
                'first_quote_date'].dt.quarter.astype(
                str)

        # Diagonal segments
        diag_q = (
            self.journey[
                self.journey['segment'].isin(self.MAIN_SEGMENTS) & self.journey['quarter_label'].isin(self.quarters_to_plot)]
            .groupby(['segment', 'quarter_label'])
            .agg(total=('numero_compte', 'count'),
                 converted=('converted', 'sum'),
                 avg_decision_days=('decision_days', 'mean'))
            .reset_index()
        )
        diag_q['conversion_rate'] = diag_q['converted'] / diag_q['total'] * 100

        # Switcher segments
        sw_q = (
            self.switchers[self.switchers['segment'].isin(self.TOP_SWITCHERS) & self.switchers['quarter_label'].isin(
                self.quarters_to_plot)]
            .groupby(['segment', 'quarter_label'])
            .agg(total=('numero_compte', 'count'),
                 converted=('converted', 'sum'),
                 avg_decision_days=('decision_days', 'mean'))
            .reset_index()
        )
        sw_q['conversion_rate'] = sw_q['converted'] / sw_q['total'] * 100

        # Plot
        fig, axes = plt.subplots(2, 2, figsize=(18, 11))
        fig.suptitle('Quarterly Comparison: 2025 Q1–Q4 vs 2026 Q1', fontsize=14, fontweight='bold')

        def plot_quarterly(ax, data, segments, colors, labels, metric, ylabel, title):
            for seg in segments:
                d = data[data['segment'] == seg].set_index('quarter_label').reindex(self.quarters_to_plot)
                color = colors[seg]
                label = labels[seg]
                # Shade 2026 Q1 as partial
                ax.axvspan(3.5, 4.5, alpha=0.08, color='orange')
                ax.plot(self.quarters_to_plot, d[metric].values, marker='o', linewidth=2.2,
                        markersize=7, color=color, label=label)
                # Annotate last point
                val = d[metric].iloc[-1]
                if not pd.isna(val):
                    fmt = f'{val:.0f}%' if 'rate' in metric else f'{val:.0f}d'
                    ax.annotate(fmt, xy=(4, val), xytext=(4.05, val),
                                fontsize=7.5, color=color, va='center')
            ax.set_title(title, fontsize=10, fontweight='bold', loc='left')
            ax.set_ylabel(ylabel)
            if 'rate' in metric:
                ax.yaxis.set_major_formatter(mtick.PercentFormatter())
            ax.tick_params(axis='x', rotation=30)
            ax.legend(fontsize=8)
            ax.grid(True, axis='y', alpha=0.3)
            ax.text(3.7, ax.get_ylim()[1] * 0.97, '⚠ partial',
                    fontsize=7.5, color='darkorange', va='top')

        plot_quarterly(axes[0, 0], diag_q, self.MAIN_SEGMENTS, self.MAIN_SEGMENT_COLORS, self.MAIN_SEGMENT_LABELS,
                       'conversion_rate', 'Conversion Rate',
                       'Diagonal — Conversion Rate')

        plot_quarterly(axes[1, 0], diag_q, self.MAIN_SEGMENTS, self.MAIN_SEGMENT_COLORS, self.MAIN_SEGMENT_LABELS,
                       'avg_decision_days', 'Avg Decision Days',
                       'Diagonal — Decision Days')

        plot_quarterly(axes[0, 1], sw_q, self.TOP_SWITCHERS, self.TOP_SWITCHER_COLORS,
                       {s: s.replace('_', ' ') for s in self.TOP_SWITCHERS},
                       'conversion_rate', 'Conversion Rate',
                       'Switchers — Conversion Rate')

        plot_quarterly(axes[1, 1], sw_q, self.TOP_SWITCHERS, self.TOP_SWITCHER_COLORS,
                       {s: s.replace('_', ' ') for s in self.TOP_SWITCHERS},
                       'avg_decision_days', 'Avg Decision Days',
                       'Switchers — Decision Days')

        plt.tight_layout()
        plt.savefig('pipeline_data/quarterly_comparison.png', dpi=150, bbox_inches='tight')
        plt.show()

    def build_intra_cohorts(self, df, segments, freq):
        """Build weekly (stayers) or bi-weekly (switchers) within-quarter cohorts."""
        filtered = df[df['segment'].isin(segments) & df['quarter_label'].isin(self.quarters_to_plot)]
        if freq == 'M':
            filtered = filtered.copy()
            filtered['week_in_q'] = ((filtered['week_in_q'] - 1) // 2) + 1  # bi-weekly buckets

        return (
            filtered
            .groupby(['segment', 'quarter_label', 'week_in_q'])
            .agg(total=('numero_compte', 'count'),
                 converted=('converted', 'sum'))
            .reset_index()
            .assign(conversion_rate=lambda x: x['converted'] / x['total'] * 100)
        )

    def plot_intra_quarter(self, data, segments, labels, title_prefix, freq_label, ncols=2):
            nrows = len(segments) // ncols + len(segments) % ncols
            fig, axes = plt.subplots(nrows, ncols, figsize=(16, 4 * nrows), sharey=False)
            fig.suptitle(f'{title_prefix} — Conversion Rate Within Quarter', fontsize=13, fontweight='bold')
            axes = axes.flatten()

            for i, seg in enumerate(segments):
                ax = axes[i]
                d = data[data['segment'] == seg]
                label = labels[seg]

                for q in self.quarters_to_plot:
                    qd = d[d['quarter_label'] == q].sort_values('week_in_q')
                    if qd.empty:
                        continue
                    # smooth with rolling avg if enough points
                    y = qd['conversion_rate'].rolling(2, min_periods=1).mean()
                    ls = '--' if q == '2026 Q1' else '-'
                    ax.plot(qd['week_in_q'], y, marker='o', linewidth=2,
                            markersize=5, color=self.quarters_colors[q], linestyle=ls, label=q)

                ax.set_title(label, fontweight='bold', fontsize=10)
                ax.set_xlabel(f'{freq_label} within quarter')
                ax.set_ylabel('Conversion Rate')
                ax.yaxis.set_major_formatter(mtick.PercentFormatter())
                ax.legend(fontsize=8)
                ax.grid(True, axis='y', alpha=0.3)

            # Hide unused subplots
            for j in range(i + 1, len(axes)):
                axes[j].set_visible(False)

            plt.tight_layout()
            return fig

    def plot_intra_quarters(self):
        diag_intra = self.build_intra_cohorts(self.journey, self.MAIN_SEGMENTS, freq='W')
        sw_intra = self.build_intra_cohorts(self.switchers, self.TOP_SWITCHERS, freq='M')

        # Plot stayers (weekly)
        fig1 = self.plot_intra_quarter(
            diag_intra, self.MAIN_SEGMENTS, self.MAIN_SEGMENT_LABELS,
            title_prefix='Stayers', freq_label='Week'
        )
        fig1.savefig('pipeline_data/intra_quarter_stayers.png', dpi=150, bbox_inches='tight')

        # Plot switchers (bi-weekly)
        fig2 = self.plot_intra_quarter(
            sw_intra, self.TOP_SWITCHERS,
            {s: s.replace('_', ' ') for s in self.TOP_SWITCHERS},
            title_prefix='Switchers', freq_label='Bi-week'
        )
        fig2.savefig('pipeline_data/intra_quarter_switchers.png', dpi=150, bbox_inches='tight')

        plt.show()

    def plot_quarter_x_product(self, data, segments, labels, colors, title_prefix, freq_label, ncols=3):
        nrows = len(self.quarters_to_plot) // ncols + len(self.quarters_to_plot) % ncols - 1
        fig, axes = plt.subplots(nrows, ncols, figsize=(18, 4 * nrows), sharey=False)
        fig.suptitle(f'{title_prefix} — Conversion Rate by Product Within Quarter',
                     fontsize=13, fontweight='bold')
        axes = axes.flatten()

        for i, q in enumerate(self.quarters_to_plot):
            ax = axes[i]
            ls = '--' if q == '2026 Q1' else '-'

            for seg in segments:
                d = data[(data['segment'] == seg) & (data['quarter_label'] == q)].sort_values('week_in_q')
                if d.empty:
                    continue
                y = d['conversion_rate'].rolling(2, min_periods=1).mean()
                ax.plot(d['week_in_q'], y, marker='o', linewidth=2,
                        markersize=5, color=colors[seg], linestyle=ls,
                        label=labels[seg])

            ax.set_title(f'{q}{"  ⚠ partial" if q == "2026 Q1" else ""}',
                         fontweight='bold', fontsize=10)
            ax.set_xlabel(f'{freq_label} within quarter')
            ax.set_ylabel('Conversion Rate')
            ax.yaxis.set_major_formatter(mtick.PercentFormatter())
            ax.legend(fontsize=8)
            ax.grid(True, axis='y', alpha=0.3)

        for j in range(i + 1, len(axes)):
            axes[j].set_visible(False)

            plt.tight_layout()
            return fig

    def plot_quarter_x_product_report(self):
        diag_intra = self.build_intra_cohorts(self.journey, self.MAIN_SEGMENTS, freq='W')
        sw_intra = self.build_intra_cohorts(self.switchers, self.TOP_SWITCHERS, freq='M')

        # Stayers — weekly
        fig1 = self.plot_quarter_x_product(
            diag_intra, self.MAIN_SEGMENTS, self.MAIN_SEGMENT_LABELS, self.MAIN_SEGMENT_COLORS,
            title_prefix='Stayers', freq_label='Week'
        )
        fig1.savefig('pipeline_data/quarter_x_product_stayers.png', dpi=150, bbox_inches='tight')

        # Switchers — bi-weekly
        fig2 = self.plot_quarter_x_product(
            sw_intra, self.TOP_SWITCHERS,
            {s: s.replace('_', ' ') for s in self.TOP_SWITCHERS},
            self.TOP_SWITCHER_COLORS,
            title_prefix='Switchers', freq_label='Bi-week'
        )
        fig2.savefig('pipeline_data/quarter_x_product_switchers.png', dpi=150, bbox_inches='tight')

        plt.show()

    def plot_monthly_cohort_conversion_curves(self):
        cohorts = self.journey[self.journey['cohort_month'] >= pd.Period('2024-01', 'M')].copy()

        # Week number: ceil(days/7), same day = week 0
        cohorts['conv_week'] = np.where(
            cohorts['decision_days'] == 0,
            0,
            np.ceil(cohorts['decision_days'] / 7).astype(int)
        )

        all_months = sorted(cohorts['cohort_month'].unique())
        print(f"Cohorts: {len(all_months)}  ({all_months[0]} → {all_months[-1]})")

        # Build cumulative conversion curve per cohort
        curves = []
        for month in all_months:
            c = cohorts[cohorts['cohort_month'] == month]
            total = len(c)
            converted = c[c['converted'] == 1]

            for w in range(self.MAX_WEEKS + 1):
                cum_conv = (converted['conv_week'] <= w).sum()
                curves.append({
                    'cohort': str(month),
                    'week': w,
                    'cumulative_pct': cum_conv / total * 100,
                    'total': total
                })

        curves_df = pd.DataFrame(curves)

        # Colour map: one colour per cohort
        cmap = plt.cm.get_cmap('turbo', len(all_months))
        colors = {str(m): cmap(i) for i, m in enumerate(all_months)}

        # Plot: all cohorts on one graph
        fig, ax = plt.subplots(figsize=(16, 7))
        fig.suptitle('Monthly Cohort Conversion Curves  —  Jan 2024 to Mar 2026',
                     fontsize=13, fontweight='bold')

        # Mark incomplete cohorts (last 3 months = fewer than 24 weeks of data)
        cutoff_month = pd.Period('2025-12', 'M')

        for month in all_months:
            d = curves_df[curves_df['cohort'] == str(month)]
            # Trim to available weeks (no extrapolation into the future)
            months_since = (pd.Period('2026-03', 'M') - pd.Period(str(month), 'M')).n
            max_w = min(self.MAX_WEEKS, months_since * 4)  # approx weeks available
            d = d[d['week'] <= max_w]

            ls = '--' if pd.Period(str(month), 'M') > cutoff_month else '-'
            alpha = 0.6 if pd.Period(str(month), 'M') > cutoff_month else 0.9

            ax.plot(d['week'], d['cumulative_pct'],
                    color=colors[str(month)], linewidth=1.5,
                    linestyle=ls, alpha=alpha, label=str(month))

        ax.set_xlabel('Weeks from first quote', fontsize=10)
        ax.set_ylabel('Cumulative % converted', fontsize=10)
        ax.yaxis.set_major_formatter(mtick.PercentFormatter())
        ax.set_xlim(0, self.MAX_WEEKS)
        ax.set_ylim(0, 70)
        ax.set_xticks(range(0, self.MAX_WEEKS + 1, 2))
        ax.grid(True, alpha=0.3)

        # Colorbar as legend (too many lines for text legend)
        sm = plt.cm.ScalarMappable(cmap='turbo',
                                   norm=plt.Normalize(vmin=0, vmax=len(all_months) - 1))
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, pad=0.01)
        cbar.set_ticks(range(len(all_months)))
        cbar.set_ticklabels([str(m) for m in all_months], fontsize=7)
        cbar.set_label('Cohort month', fontsize=9)

        ax.text(0.01, 0.97, 'Dashed = incomplete cohorts (< 24 weeks data)',
                transform=ax.transAxes, fontsize=8, color='grey', va='top')

        plt.tight_layout()
        plt.savefig('pipeline_data/monthly_cohort_conversion_curves.png', dpi=150, bbox_inches='tight')
        plt.show()

        fig, axes = plt.subplots(3, 1, figsize=(16, 18), sharey=True)
        fig.suptitle('Monthly Cohort Conversion Curves — Split by Year',
                     fontsize=13, fontweight='bold')

        years = [2024, 2025, 2026]

        for ax, year in zip(axes, years):
            year_months = [m for m in all_months if m.year == year]
            cmap_year = plt.cm.get_cmap('turbo', max(len(year_months), 1))

            for i, month in enumerate(year_months):
                d = curves_df[curves_df['cohort'] == str(month)]
                months_since = (pd.Period('2026-03', 'M') - month).n
                max_w = min(self.MAX_WEEKS, months_since * 4)
                d = d[d['week'] <= max_w]

                ls = '--' if month > cutoff_month else '-'
                alpha = 0.6 if month > cutoff_month else 0.9
                color = cmap_year(i / max(len(year_months) - 1, 1))

                ax.plot(d['week'], d['cumulative_pct'],
                        color=color, linewidth=2, linestyle=ls,
                        alpha=alpha, label=str(month))

            ax.set_title(f'{year}  —  {len(year_months)} cohorts', fontweight='bold', fontsize=11, loc='left')
            ax.set_ylabel('Cumulative % converted', fontsize=9)
            ax.yaxis.set_major_formatter(mtick.PercentFormatter())
            ax.set_xlim(0, self.MAX_WEEKS)
            ax.set_ylim(0, 70)
            ax.set_xticks(range(0, self.MAX_WEEKS + 1, 2))
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=8, ncol=len(year_months), loc='lower right')

        axes[-1].set_xlabel('Weeks from first quote', fontsize=10)
        axes[-1].text(0.01, -0.08, 'Dashed = incomplete cohorts',
                      transform=axes[-1].transAxes, fontsize=8, color='grey')

        plt.tight_layout()
        plt.savefig('pipeline_data/monthly_cohort_curves_by_year.png', dpi=150, bbox_inches='tight')
        plt.show()

    def plot_monthly_cohort_conversion_curves_by_product(self):
        # ToDo
        cutoff_month = pd.Period('2025-12', 'M')
        products = ['Boiler', 'Stove', 'AC', 'Heat Pump']
        years = [2024, 2025, 2026]

        prod_colors = {'Boiler': 'steelblue', 'Stove': 'tomato',
                       'AC': 'mediumseagreen', 'Heat Pump': 'darkorange'}

        # Build curves per product × cohort month
        cohorts_prod = self.journey[
            (self.journey['cohort_month'] >= pd.Period('2024-01', 'M')) &
            (self.journey['product'].notna())
            ].copy()
        cohorts_prod['conv_week'] = np.where(
            cohorts_prod['decision_days'] == 0,
            0,
            np.ceil(cohorts_prod['decision_days'] / 7).astype(int)
        )

        curves_prod = []
        for (month, product), grp in cohorts_prod.groupby(['cohort_month', 'product']):
            total = len(grp)
            converted = grp[grp['converted'] == 1]
            for w in range(self.MAX_WEEKS + 1):
                cum_conv = (converted['conv_week'] <= w).sum()
                curves_prod.append({
                    'cohort': str(month),
                    'product': product,
                    'year': month.year,
                    'week': w,
                    'cumulative_pct': cum_conv / total * 100,
                    'total': total
                })

        curves_prod_df = pd.DataFrame(curves_prod)

        def get_curve(df, month, product):
            """Trim curve to available weeks."""
            d = df[(df['cohort'] == str(month)) & (df['product'] == product)]
            months_since = (pd.Period('2026-03', 'M') - month).n
            max_w = min(self.MAX_WEEKS, months_since * 4)
            return d[d['week'] <= max_w]

        all_months = sorted(cohorts_prod['cohort_month'].unique())
        print(f"Cohorts: {len(all_months)}  ({all_months[0]} → {all_months[-1]})")

        # Option A: one figure per product, 3 year panels
        for product in products:
            fig, axes = plt.subplots(3, 1, figsize=(16, 15), sharey=True)
            fig.suptitle(f'Cohort Conversion Curves — {product}',
                         fontsize=13, fontweight='bold')

            for ax, year in zip(axes, years):
                year_months = [m for m in all_months if m.year == year]
                cmap_year = plt.cm.get_cmap('turbo', max(len(year_months), 1))

                for i, month in enumerate(year_months):
                    d = get_curve(curves_prod_df, month, product)
                    if d.empty:
                        continue
                    ls = '--' if month > cutoff_month else '-'
                    alpha = 0.6 if month > cutoff_month else 0.9
                    color = cmap_year(i / max(len(year_months) - 1, 1))

                    ax.plot(d['week'], d['cumulative_pct'],
                            color=color, linewidth=2, linestyle=ls,
                            alpha=alpha, label=str(month))

                ax.set_title(f'{year}  —  {len(year_months)} cohorts',
                             fontweight='bold', fontsize=10, loc='left')
                ax.set_ylabel('Cumulative % converted', fontsize=9)
                ax.yaxis.set_major_formatter(mtick.PercentFormatter())
                ax.set_xlim(0, self.MAX_WEEKS)
                ax.set_ylim(0, 80)
                ax.set_xticks(range(0, self.MAX_WEEKS + 1, 2))
                ax.grid(True, alpha=0.3)
                ax.legend(fontsize=8, ncol=len(year_months), loc='lower right')

            axes[-1].set_xlabel('Weeks from first quote', fontsize=10)
            plt.tight_layout()
            plt.savefig(f'pipeline_data/monthly_cohort_curves_{product.lower().replace(" ", "_")}.png',
                        dpi=150, bbox_inches='tight')
            plt.show()

        # Option B: 4 products × 3 years grid
        fig, axes = plt.subplots(3, 4, figsize=(24, 15), sharey=True, sharex=True)
        fig.suptitle('Cohort Conversion Curves — All Products × All Years',
                     fontsize=14, fontweight='bold')

        for col, product in enumerate(products):
            for row, year in enumerate(years):
                ax = axes[row, col]
                year_months = [m for m in all_months if m.year == year]
                cmap_year = plt.cm.get_cmap('turbo', max(len(year_months), 1))

                for i, month in enumerate(year_months):
                    d = get_curve(curves_prod_df, month, product)
                    if d.empty:
                        continue
                    ls = '--' if month > cutoff_month else '-'
                    alpha = 0.6 if month > cutoff_month else 0.9
                    color = cmap_year(i / max(len(year_months) - 1, 1))

                    ax.plot(d['week'], d['cumulative_pct'],
                            color=color, linewidth=1.5, linestyle=ls, alpha=alpha)

                if row == 0:
                    ax.set_title(product, fontweight='bold', fontsize=11,
                                 color=prod_colors[product])
                if col == 0:
                    ax.set_ylabel(f'{year}\nCumulative % converted', fontsize=9)

                ax.yaxis.set_major_formatter(mtick.PercentFormatter())
                ax.set_xlim(0, self.MAX_WEEKS)
                ax.set_ylim(0, 80)
                ax.set_xticks(range(0, self.MAX_WEEKS + 1, 4))
                ax.grid(True, alpha=0.3)

        for col in range(4):
            axes[-1, col].set_xlabel('Weeks from first quote', fontsize=9)

        plt.tight_layout()
        plt.savefig('pipeline_data/monthly_cohort_curves_grid.png', dpi=150, bbox_inches='tight')
        plt.show()

    def plot_monthly_cohort_conversion_curves_by_product_strict(self):
        #ToDo
        cutoff_month = pd.Period('2025-12', 'M')
        years = [2024, 2025, 2026]

        top_switchers = [
            'HEAT_PUMP → OTHER',
            'OTHER → HEAT_PUMP',
            'BOILER_GAS → HEAT_PUMP',
            'HEAT_PUMP → STOVE'
        ]

        main_segments = ['BOILER_GAS → BOILER_GAS', 'STOVE → STOVE',
                         'AIR_CONDITIONER → AIR_CONDITIONER', 'HEAT_PUMP → HEAT_PUMP']

        # Build curves per segment × cohort month
        segments_to_plot = main_segments + top_switchers

        cohorts_seg = self.journey[
            (self.journey['cohort_month'] >= pd.Period('2024-01', 'M')) &
            (self.journey['segment'].isin(segments_to_plot))
            ].copy()

        cohorts_seg['conv_week'] = np.where(
            cohorts_seg['decision_days'] == 0,
            0,
            np.ceil(cohorts_seg['decision_days'] / 7).astype(int)
        )

        all_months = sorted(cohorts_seg['cohort_month'].unique())

        curves_seg = []
        for (month, segment), grp in cohorts_seg.groupby(['cohort_month', 'segment']):
            total = len(grp)
            converted = grp[grp['converted'] == 1]
            for w in range(self.MAX_WEEKS + 1):
                cum_conv = (converted['conv_week'] <= w).sum()
                curves_seg.append({
                    'cohort': str(month),
                    'segment': segment,
                    'year': month.year,
                    'week': w,
                    'cumulative_pct': cum_conv / total * 100,
                    'total': total
                })

        curves_seg_df = pd.DataFrame(curves_seg)

        seg_labels = {
            'BOILER_GAS → BOILER_GAS': 'Boiler → Boiler',
            'STOVE → STOVE': 'Stove → Stove',
            'AIR_CONDITIONER → AIR_CONDITIONER': 'AC → AC',
            'HEAT_PUMP → HEAT_PUMP': 'Heat Pump → Heat Pump',
            'HEAT_PUMP → OTHER': 'Heat Pump → Other',
            'OTHER → HEAT_PUMP': 'Other → Heat Pump',
            'BOILER_GAS → HEAT_PUMP': 'Boiler → Heat Pump',
            'HEAT_PUMP → STOVE': 'Heat Pump → Stove',
        }

        # One figure per segment, 3 year panels
        for seg in segments_to_plot:
            fig, axes = plt.subplots(3, 1, figsize=(16, 15), sharey=True)
            fig.suptitle(f'Cohort Conversion Curves — {seg_labels[seg]}',
                         fontsize=13, fontweight='bold')

            for ax, year in zip(axes, years):
                year_months = [m for m in all_months if m.year == year]
                cmap_year = plt.cm.get_cmap('turbo', max(len(year_months), 1))

                for i, month in enumerate(year_months):
                    d = curves_seg_df[
                        (curves_seg_df['cohort'] == str(month)) &
                        (curves_seg_df['segment'] == seg)
                        ]
                    if d.empty:
                        continue
                    months_since = (pd.Period('2026-03', 'M') - month).n
                    max_w = min(self.MAX_WEEKS, months_since * 4)
                    d = d[d['week'] <= max_w]
                    ls = '--' if month > cutoff_month else '-'
                    alpha = 0.6 if month > cutoff_month else 0.9
                    color = cmap_year(i / max(len(year_months) - 1, 1))

                    ax.plot(d['week'], d['cumulative_pct'],
                            color=color, linewidth=2, linestyle=ls,
                            alpha=alpha, label=str(month))

                ax.set_title(f'{year}  —  {len(year_months)} cohorts',
                             fontweight='bold', fontsize=10, loc='left')
                ax.set_ylabel('Cumulative % converted', fontsize=9)
                ax.yaxis.set_major_formatter(mtick.PercentFormatter())
                ax.set_xlim(0, self.MAX_WEEKS)
                ax.set_ylim(0, 100)
                ax.set_xticks(range(0, self.MAX_WEEKS + 1, 2))
                ax.grid(True, alpha=0.3)
                ax.legend(fontsize=8, ncol=len(year_months), loc='lower right')

            axes[-1].set_xlabel('Weeks from first quote', fontsize=10)
            plt.tight_layout()
            fname = seg.lower().replace(' ', '_').replace('→', 'to').replace('__', '_')
            plt.savefig(f'pipeline_data/monthly_cohort_curves_{fname}_strict.png', dpi=150, bbox_inches='tight')
            plt.show()

        # Reuse curves_seg_df already built — just filter to diagonal segments
        diag_seg_labels = {
            'BOILER_GAS → BOILER_GAS': 'Boiler',
            'STOVE → STOVE': 'Stove',
            'AIR_CONDITIONER → AIR_CONDITIONER': 'AC',
            'HEAT_PUMP → HEAT_PUMP': 'Heat Pump'
        }

        for seg, label in diag_seg_labels.items():
            fig, axes = plt.subplots(3, 1, figsize=(16, 15), sharey=True)
            fig.suptitle(f'Cohort Conversion Curves — {label} (strict: {seg})',
                         fontsize=13, fontweight='bold')

            for ax, year in zip(axes, years):
                year_months = [m for m in all_months if m.year == year]
                cmap_year = plt.cm.get_cmap('turbo', max(len(year_months), 1))

                for i, month in enumerate(year_months):
                    d = curves_seg_df[
                        (curves_seg_df['cohort'] == str(month)) &
                        (curves_seg_df['segment'] == seg)
                        ]
                    if d.empty:
                        continue
                    months_since = (pd.Period('2026-03', 'M') - month).n
                    max_w = min(self.MAX_WEEKS, months_since * 4)
                    d = d[d['week'] <= max_w]
                    ls = '--' if month > cutoff_month else '-'
                    alpha = 0.6 if month > cutoff_month else 0.9
                    color = cmap_year(i / max(len(year_months) - 1, 1))

                    ax.plot(d['week'], d['cumulative_pct'],
                            color=color, linewidth=2, linestyle=ls,
                            alpha=alpha, label=str(month))

                ax.set_title(f'{year}  —  {len(year_months)} cohorts',
                             fontweight='bold', fontsize=10, loc='left')
                ax.set_ylabel('Cumulative % converted', fontsize=9)
                ax.yaxis.set_major_formatter(mtick.PercentFormatter())
                ax.set_xlim(0, self.MAX_WEEKS)
                ax.set_ylim(0, 80)
                ax.set_xticks(range(0, self.MAX_WEEKS + 1, 2))
                ax.grid(True, alpha=0.3)
                ax.legend(fontsize=8, ncol=len(year_months), loc='lower right')

            axes[-1].set_xlabel('Weeks from first quote', fontsize=10)
            plt.tight_layout()
            fname = label.lower().replace(' ', '_')
            plt.savefig(f'pipeline_data/monthly_cohort_curves_{fname}_strict.png', dpi=150, bbox_inches='tight')
            plt.show()

        diag_colors = {
            'BOILER_GAS → BOILER_GAS': 'steelblue',
            'STOVE → STOVE': 'tomato',
            'AIR_CONDITIONER → AIR_CONDITIONER': 'mediumseagreen',
            'HEAT_PUMP → HEAT_PUMP': 'darkorange'
        }
        diag_labels = {
            'BOILER_GAS → BOILER_GAS': 'Boiler',
            'STOVE → STOVE': 'Stove',
            'AIR_CONDITIONER → AIR_CONDITIONER': 'AC',
            'HEAT_PUMP → HEAT_PUMP': 'Heat Pump'
        }

        fig, axes = plt.subplots(3, 4, figsize=(24, 15), sharey=True, sharex=True)
        fig.suptitle('Cohort Conversion Curves — All Products × All Years (strict: first = last product)',
                     fontsize=14, fontweight='bold')

        for col, (seg, label) in enumerate(diag_seg_labels.items()):
            for row, year in enumerate(years):
                ax = axes[row, col]
                year_months = [m for m in all_months if m.year == year]
                cmap_year = plt.cm.get_cmap('turbo', max(len(year_months), 1))

                for i, month in enumerate(year_months):
                    d = curves_seg_df[
                        (curves_seg_df['cohort'] == str(month)) &
                        (curves_seg_df['segment'] == seg)
                        ]
                    if d.empty:
                        continue
                    months_since = (pd.Period('2026-03', 'M') - month).n
                    max_w = min(self.MAX_WEEKS, months_since * 4)
                    d = d[d['week'] <= max_w]
                    ls = '--' if month > cutoff_month else '-'
                    alpha = 0.6 if month > cutoff_month else 0.9
                    color = cmap_year(i / max(len(year_months) - 1, 1))

                    ax.plot(d['week'], d['cumulative_pct'],
                            color=color, linewidth=1.5, linestyle=ls, alpha=alpha)

                if row == 0:
                    ax.set_title(label, fontweight='bold', fontsize=11,
                                 color=list(diag_colors.values())[col])
                if col == 0:
                    ax.set_ylabel(f'{year}\nCumulative % converted', fontsize=9)

                ax.yaxis.set_major_formatter(mtick.PercentFormatter())
                ax.set_xlim(0, self.MAX_WEEKS)
                ax.set_ylim(0, 80)
                ax.set_xticks(range(0, self.MAX_WEEKS + 1, 4))
                ax.grid(True, alpha=0.3)

        for col in range(4):
            axes[-1, col].set_xlabel('Weeks from first quote', fontsize=9)

        plt.tight_layout()
        plt.savefig('pipeline_data/cohort_curves_grid_strict.png', dpi=150, bbox_inches='tight')
        plt.show()

    def plot_monthly_cohort_conversion_curves_by_agency(self):

        year_colors = {2024: 'steelblue', 2025: 'tomato', 2026: 'mediumseagreen'}

        for product, seg in self.DIAGONAL_MAP.items():
            # Filter to this product's diagonal segment
            prod_df = self.journey_agency[
                (self.journey_agency['segment'] == seg) &
                (self.journey_agency['cohort_month'] >= pd.Period('2024-01', 'M'))
                ]

            # Which agencies have enough data?
            agency_counts = prod_df['main_agency'].value_counts()
            valid_agencies = agency_counts[agency_counts >= self.MIN_CUSTOMERS].index.tolist()
            valid_agencies = sorted(valid_agencies)

            n = len(valid_agencies)
            ncols = 4
            nrows = int(np.ceil(n / ncols))

            fig, axes = plt.subplots(nrows, ncols, figsize=(20, 5 * nrows), sharey=True)
            fig.suptitle(f'Cohort Conversion Curves by Agency — {product} (strict: {seg})',
                         fontsize=13, fontweight='bold')
            axes = axes.flatten() if n > 1 else [axes]

            for i, agency in enumerate(valid_agencies):
                ax = axes[i]
                agency_df = prod_df[prod_df['main_agency'] == agency]

                for year in [2024, 2025, 2026]:
                    year_df = agency_df[agency_df['cohort_month'].dt.year == year]
                    if year_df.empty:
                        continue

                    year_months = sorted(year_df['cohort_month'].unique())
                    month_curves = []

                    for month in year_months:
                        grp = year_df[year_df['cohort_month'] == month]
                        total = len(grp)
                        if total < 5:  # skip tiny monthly cohorts
                            continue
                        converted = grp[grp['converted'] == 1]
                        months_since = (pd.Period('2026-03', 'M') - month).n
                        max_w = min(self.MAX_WEEKS, months_since * 4)
                        curve = []
                        for w in range(max_w + 1):
                            curve.append((converted['conv_week'] <= w).sum() / total * 100)
                        month_curves.append(curve)

                    if not month_curves:
                        continue

                    # Median curve + range band across monthly cohorts
                    max_len = max(len(c) for c in month_curves)
                    padded = [c + [c[-1]] * (max_len - len(c)) for c in month_curves]
                    arr = np.array(padded)
                    median = np.median(arr, axis=0)
                    lo = np.percentile(arr, 25, axis=0)
                    hi = np.percentile(arr, 75, axis=0)
                    weeks = range(max_len)

                    ls = '--' if year == 2026 else '-'
                    n_coh = len(month_curves)
                    ax.plot(weeks, median, color=year_colors[year], linewidth=2,
                            linestyle=ls, label=f'{year} (n={n_coh} months)')
                    ax.fill_between(weeks, lo, hi, color=year_colors[year], alpha=0.15)

                total_n = len(agency_df)
                ax.set_title(f'{agency}\n(n={total_n})', fontsize=8, fontweight='bold')
                ax.set_xlim(0, self.MAX_WEEKS)
                ax.set_ylim(0, 80)
                ax.set_xticks(range(0, self.MAX_WEEKS + 1, 4))
                ax.yaxis.set_major_formatter(mtick.PercentFormatter())
                ax.grid(True, alpha=0.3)
                ax.legend(fontsize=7, loc='lower right')

            # Hide unused panels
            for j in range(i + 1, len(axes)):
                axes[j].set_visible(False)

            axes[0].set_ylabel('Cumulative % converted', fontsize=9)
            if nrows > 1:
                for r in range(nrows):
                    axes[r * ncols].set_ylabel('Cumulative % converted', fontsize=9)

            plt.tight_layout()
            fname = product.lower().replace(' ', '_')
            plt.savefig(f'cohort_curves_agency_{fname}.png', dpi=150, bbox_inches='tight')
            plt.show()
            print(f"Saved: cohort_curves_agency_{fname}.png — {len(valid_agencies)} agencies plotted")

    def plot_monthly_cohort_conversion_curves_by_agency_process(self):

        # Add process flag to journey_agency
        # Get dominant process flag per customer (max = if any quote was new process)

        # Process labels
        proc_labels = {0: 'Old process', 1: 'New process (TechEasy)'}
        proc_colors = {0: 'steelblue', 1: 'tomato'}

        for product, seg in self.DIAGONAL_MAP.items():
            prod_df = self.journey_agency_process[
                (self.journey_agency_process['segment'] == seg) &
                (self.journey_agency_process['cohort_month'] >= pd.Period('2024-01', 'M'))
                ]

            agency_counts = prod_df['main_agency'].value_counts()
            valid_agencies = sorted(agency_counts[agency_counts >= self.MIN_CUSTOMERS].index.tolist())

            n = len(valid_agencies)
            ncols = 4
            nrows = int(np.ceil(n / ncols))

            fig, axes = plt.subplots(nrows, ncols, figsize=(20, 5 * nrows), sharey=True)
            fig.suptitle(f'Cohort Conversion Curves by Agency — {product}\nOld Process vs TechEasy (New Process)',
                         fontsize=13, fontweight='bold')
            axes = axes.flatten()

            for i, agency in enumerate(valid_agencies):
                ax = axes[i]
                ag_df = prod_df[prod_df['main_agency'] == agency]

                for proc_flag in [0, 1]:
                    proc_df = ag_df[ag_df['new_process'] == proc_flag]
                    if len(proc_df) < 10:
                        continue

                    months = sorted(proc_df['cohort_month'].unique())
                    month_curves = []

                    for month in months:
                        grp = proc_df[proc_df['cohort_month'] == month]
                        total = len(grp)
                        if total < 5:
                            continue
                        converted = grp[grp['converted'] == 1]
                        months_since = (pd.Period('2026-03', 'M') - month).n
                        max_w = min(self.MAX_WEEKS, months_since * 4)
                        curve = []
                        for w in range(max_w + 1):
                            curve.append((converted['conv_week'] <= w).sum() / total * 100)
                        month_curves.append(curve)

                    if not month_curves:
                        continue

                    max_len = max(len(c) for c in month_curves)
                    padded = [c + [c[-1]] * (max_len - len(c)) for c in month_curves]
                    arr = np.array(padded)
                    median = np.median(arr, axis=0)
                    lo = np.percentile(arr, 25, axis=0)
                    hi = np.percentile(arr, 75, axis=0)
                    weeks = range(max_len)
                    color = proc_colors[proc_flag]
                    label = f'{proc_labels[proc_flag]} (n={len(proc_df)})'

                    ax.plot(weeks, median, color=color, linewidth=2, label=label)
                    ax.fill_between(weeks, lo, hi, color=color, alpha=0.15)

                # Adoption month annotation
                ag_adoption = self.new_process[self.new_process['nom_agence'] == agency]['first_new_process'].values[0]
                if pd.notna(ag_adoption):
                    adoption_period = pd.Period(ag_adoption, 'M')
                    months_since_start = (adoption_period - pd.Period('2024-01', 'M')).n
                    approx_week = months_since_start * 4
                    if 0 < approx_week < self.MAX_WEEKS:
                        ax.axvline(approx_week, color='grey', linewidth=1,
                                   linestyle=':', alpha=0.7, label='TechEasy adoption')

                total_n = len(ag_df)
                ax.set_title(f'{agency}\n(n={total_n})', fontsize=8, fontweight='bold')
                ax.set_xlim(0, self.MAX_WEEKS)
                ax.set_ylim(0, 80)
                ax.set_xticks(range(0, self.MAX_WEEKS + 1, 4))
                ax.yaxis.set_major_formatter(mtick.PercentFormatter())
                ax.grid(True, alpha=0.3)
                ax.legend(fontsize=7, loc='lower right')

            for j in range(i + 1, len(axes)):
                axes[j].set_visible(False)
            for r in range(nrows):
                axes[r * ncols].set_ylabel('Cumulative % converted', fontsize=9)

            axes[-nrows * ncols + nrows * ncols - ncols].set_xlabel('Weeks from first quote', fontsize=9)

            plt.tight_layout()
            fname = product.lower().replace(' ', '_')
            plt.savefig(f'cohort_curves_agency_{fname}_process.png', dpi=150, bbox_inches='tight')
            plt.show()
            print(f"Saved: cohort_curves_agency_{fname}_process.png")


def get_journey(df: pd.DataFrame):
    return WeeklyCohorts(df).get_journey(df)


def plot_weekly_cohorts_performance_trend__single_quoters(df: pd.DataFrame) -> None:
    WeeklyCohorts(df).plot_weekly_cohorts_performance_trend__single_quoters()


def plot_weekly_cohorts_performance_trend__switchers(df: pd.DataFrame) -> None:
    WeeklyCohorts(df).plot_weekly_cohorts_performance_trend__switchers()


def plot_quarters_report(df: pd.DataFrame) -> None:
    WeeklyCohorts(df).plot_quarters_report()


def plot_intra_quarters(df: pd.DataFrame) -> None:
    WeeklyCohorts(df).plot_intra_quarters()


def plot_quarter_x_product_report(df: pd.DataFrame) -> None:
    WeeklyCohorts(df).plot_quarter_x_product_report()


def plot_monthly_cohort_conversion_curves(df: pd.DataFrame) -> None:
    WeeklyCohorts(df).plot_monthly_cohort_conversion_curves()


def plot_monthly_cohort_conversion_curves_by_product(df: pd.DataFrame) -> None:
    WeeklyCohorts(df).plot_monthly_cohort_conversion_curves_by_product()


def plot_monthly_cohort_conversion_curves_by_agency(df: pd.DataFrame) -> None:
    WeeklyCohorts(df).plot_monthly_cohort_conversion_curves_by_agency()


def plot_monthly_cohort_conversion_curves_by_agency_process(df: pd.DataFrame) -> None:
    WeeklyCohorts(df).plot_monthly_cohort_conversion_curves_by_agency_process()
