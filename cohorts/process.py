from datetime import date

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd

from util.cohort import get_cohort_conversion_curves
from util.plot import plot_median_band
from util.quarter import last_n_quarters_label


class ProcessCohorts:

    class ProcessPlot:
        LABELS = {
            0: 'Old process',
            1: 'New process (TechEasy)'
        }
        COLORS = {
            0: 'steelblue',
            1: 'tomato'
        }

        def __init__(self, ax, df: pd.DataFrame, is_new: int, max_weeks: int, start_month: str, end_month: str):
            self.ax = ax
            self.df = df
            self.is_new = is_new
            self.max_weeks = max_weeks
            self.start_month = start_month
            self.end_month = end_month

        def plot(self):
            color = self.COLORS[self.is_new]
            label = f'{self.LABELS[self.is_new]} (n={len(self.df)})'
            month_curves = get_cohort_conversion_curves(self.df, self.max_weeks, self.end_month)
            if not month_curves:
                raise ValueError("No month curves to plot")
            plot_median_band(self.ax, month_curves, color, label)

        def plot_adoption_month(self, month: int):
            if pd.notna(month):
                adoption_period = pd.Period(month, 'M')
                months_since_start = (adoption_period - pd.Period(self.start_month, 'M')).n
                approx_week = months_since_start * 4
                if 0 < approx_week < self.max_weeks:
                    self.ax.axvline(approx_week, color='grey', linewidth=1,
                               linestyle=':', alpha=0.7, label='TechEasy adoption')

    MAIN_SEGMENT_LABELS = {
        'BOILER_GAS → BOILER_GAS': 'Boiler',
        'STOVE → STOVE': 'Stove',
        'AIR_CONDITIONER → AIR_CONDITIONER': 'AC',
        'HEAT_PUMP → HEAT_PUMP': 'Heat Pump'
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

    START_MONTH = '2024-01'
    END_MONTH = '2026-03'
    OUTPUT_DIR = "pipeline_data"

    def __init__(self, df: pd.DataFrame):
        self.journey = self.get_journey(df)
        self.journey_agency = self.get_journey_agency(df)
        self.journey_agency_process = self.get_journey_agency_process(df)
        self.new_process = df.groupby('nom_agence').agg(
            first_new_process=('dt_creation_devis',
                               lambda x: x[df.loc[x.index, 'fg_nouveau_process_relance_devis'] == 1].min()),
        ).reset_index()

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

    def plot(self):
        for seg, product in self.MAIN_SEGMENT_LABELS.items():
            prod_df = self.journey_agency_process[
                (self.journey_agency_process['segment'] == seg) &
                (self.journey_agency_process['cohort_month'] >= pd.Period(self.START_MONTH, 'M'))
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
                agency_df = prod_df[prod_df['main_agency'] == agency]
                new_process_adoption_month = self.new_process[self.new_process['nom_agence'] == agency]['first_new_process'].values[0]
                for is_new_process in [0, 1]:
                    process_df = agency_df[agency_df['new_process'] == is_new_process]
                    if len(process_df) < 10:
                        continue
                    try:
                        process_plot = self.ProcessPlot(ax, process_df, is_new_process, self.MAX_WEEKS, self.START_MONTH, self.END_MONTH)
                        process_plot.plot()
                        if is_new_process == 1 and pd.notna(new_process_adoption_month):
                            process_plot.plot_adoption_month(new_process_adoption_month)
                    except ValueError:
                        continue
                total_n = len(agency_df)
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
            print(f"Saved: cohort_curves_agency_{fname}_process.png")

            plt.show()


def plot_process_cohorts(df: pd.DataFrame) -> None:
    ProcessCohorts(df).plot()
