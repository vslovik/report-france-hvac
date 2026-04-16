import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import matplotlib.ticker as mtick
from cohorts.product import ProductCohorts
from util.cohort import get_cohort_conversion_curves
from util.plot import plot_median_band


class AgencyCohorts(ProductCohorts):
    def __init__(self, df: pd.DataFrame, max_weeks=24, start_month='2024-01', end_month='2026-03'):
        super().__init__(df, max_weeks, start_month, end_month)

    @classmethod
    def get_journey(cls, df: pd.DataFrame) -> pd.DataFrame:
        # Add agency to journey from raw quotes
        agency_per_customer = (
            df.sort_values('dt_creation_devis')
            .groupby('numero_compte')['nom_agence']
            .first()
            .reset_index()
            .rename(columns={'nom_agence': 'main_agency'})
        )
        journey = super().get_journey(df)
        journey_agency = journey.merge(agency_per_customer, on='numero_compte', how='left')
        journey_agency['cohort_month'] = journey_agency['first_quote_date'].dt.to_period('M')
        journey_agency['conv_week'] = np.where(
            journey_agency['decision_days'] == 0, 0,
            np.ceil(journey_agency['decision_days'] / 7).astype(int)
        )

        return journey_agency

    def plot(self):
        for seg, product in self.MAIN_SEGMENT_LABELS.items():
            # Filter to this product's diagonal segment
            prod_df = self.journey[
                (self.journey['segment'] == seg) &
                (self.journey['cohort_month'] >= pd.Period('2024-01', 'M'))
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
                for year in self.YEARS:
                    year_df = agency_df[agency_df['cohort_month'].dt.year == year]
                    if year_df.empty:
                        continue

                    month_curves = get_cohort_conversion_curves(year_df, self.max_weeks, self.end_month)
                    if not month_curves:
                        continue

                    n_coh = len(month_curves)
                    plot_median_band(ax, month_curves, self.YEARS_COLORS[year], f'{year} (n={n_coh} months)')

                total_n = len(agency_df)
                ax.set_title(f'{agency}\n(n={total_n})', fontsize=8, fontweight='bold')
                ax.set_xlim(0, self.max_weeks)
                ax.set_ylim(0, 80)
                ax.set_xticks(range(0, self.max_weeks + 1, 4))
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
            plt.savefig(f'{self.OUTPUT_DIR}/cohort_curves_agency_{fname}.png', dpi=150, bbox_inches='tight')
            plt.show()
            print(f"Saved: {self.OUTPUT_DIR}/cohort_curves_agency_{fname}.png — {len(valid_agencies)} agencies plotted")


def plot_agency_cohorts(df: pd.DataFrame) -> None:
    AgencyCohorts(df).plot()
