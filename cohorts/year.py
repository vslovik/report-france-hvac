from datetime import date

import numpy as np
import pandas as pd

from cohorts.cohorts import Cohorts
from util.quarter import last_n_quarters_label, week_in_quarter

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick


class YearCohorts(Cohorts):
    def __init__(self, df: pd.DataFrame, max_weeks=24, start_month='2024-01', end_month='2026-03'):
        self.max_weeks = max_weeks
        self.start_month = start_month
        self.end_month = end_month

        self.journey = self.get_journey(df)
        self.quarters_to_plot = last_n_quarters_label(self.QUARTERS_TO_SHOW, self.LAST_DATE)
        self.quarters_colors = dict(zip(self.quarters_to_plot, self.QUARTERS_COLORS))

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

        journey['week_in_q'] = week_in_quarter(journey['first_quote_date'])
        journey['quarter_label'] = journey['first_quote_date'].dt.year.astype(str) + ' Q' + journey['first_quote_date'].dt.quarter.astype(
            str)

        journey['cohort_month'] = journey['first_quote_date'].dt.to_period('M')

        return journey

    def plot(self):
        cohorts = self.journey[self.journey['cohort_month'] >= pd.Period(self.start_month, 'M')].copy()

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

            for w in range(self.max_weeks + 1):
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
        cutoff_month = pd.Period('2025-12', 'M') #ToDo

        for month in all_months:
            d = curves_df[curves_df['cohort'] == str(month)]
            # Trim to available weeks (no extrapolation into the future)
            months_since = (pd.Period(self.end_month, 'M') - pd.Period(str(month), 'M')).n
            max_w = min(self.max_weeks, months_since * 4)  # approx weeks available
            d = d[d['week'] <= max_w]

            ls = '--' if pd.Period(str(month), 'M') > cutoff_month else '-'
            alpha = 0.6 if pd.Period(str(month), 'M') > cutoff_month else 0.9

            ax.plot(d['week'], d['cumulative_pct'],
                    color=colors[str(month)], linewidth=1.5,
                    linestyle=ls, alpha=alpha, label=str(month))

        ax.set_xlabel('Weeks from first quote', fontsize=10)
        ax.set_ylabel('Cumulative % converted', fontsize=10)
        ax.yaxis.set_major_formatter(mtick.PercentFormatter())
        ax.set_xlim(0, self.max_weeks)
        ax.set_ylim(0, 70)
        ax.set_xticks(range(0, self.max_weeks + 1, 2))
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
        plt.savefig(f'{self.OUTPUT_DIR}/monthly_cohort_conversion_curves.png', dpi=150, bbox_inches='tight')
        plt.show()

        fig, axes = plt.subplots(3, 1, figsize=(16, 18), sharey=True)
        fig.suptitle('Monthly Cohort Conversion Curves — Split by Year',
                     fontsize=13, fontweight='bold')

        for ax, year in zip(axes, self.YEARS):
            year_months = [m for m in all_months if m.year == year]
            cmap_year = plt.cm.get_cmap('turbo', max(len(year_months), 1))

            for i, month in enumerate(year_months):
                d = curves_df[curves_df['cohort'] == str(month)]
                months_since = (pd.Period('2026-03', 'M') - month).n
                max_w = min(self.max_weeks, months_since * 4)
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
            ax.set_xlim(0, self.max_weeks)
            ax.set_ylim(0, 70)
            ax.set_xticks(range(0, self.max_weeks + 1, 2))
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=8, ncol=len(year_months), loc='lower right')

        axes[-1].set_xlabel('Weeks from first quote', fontsize=10)
        axes[-1].text(0.01, -0.08, 'Dashed = incomplete cohorts',
                      transform=axes[-1].transAxes, fontsize=8, color='grey')

        plt.tight_layout()
        plt.savefig(f'{self.OUTPUT_DIR}/monthly_cohort_curves_by_year.png', dpi=150, bbox_inches='tight')
        plt.show()


def plot_year_cohorts(df: pd.DataFrame) -> None:
    YearCohorts(df).plot()