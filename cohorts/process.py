import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd

from cohorts.agency import AgencyCohorts
from util.cohort import get_cohort_conversion_curves
from util.plot import plot_median_band


class AgencyProcessCohorts(AgencyCohorts):
    class AgencyPlot:

        def __init__(self, ax, df, agency_name: str, new_process_adoption_month: int, max_weeks: int, start_month: str, end_month: str):
            self.ax = ax
            self.df = df
            self.agency_name = agency_name
            self.new_process_adoption_month = new_process_adoption_month
            self.max_weeks = max_weeks
            self.start_month = start_month
            self.end_month = end_month

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

        def get_process(self, process_df, is_new_process):
            return self.ProcessPlot(
                self.ax,
                process_df,
                is_new_process,
                self.max_weeks,
                self.start_month,
                self.end_month
            )

        def plot(self):
            for is_new_process in [0, 1]:
                process_df = self.df[self.df['new_process'] == is_new_process]
                if len(process_df) < 10:
                    continue
                try:
                    process_plot = self.get_process(process_df, is_new_process)
                    process_plot.plot()
                    if is_new_process == 1 and pd.notna(self.new_process_adoption_month):
                        process_plot.plot_adoption_month(self.new_process_adoption_month)
                except ValueError:
                    continue
            total_n = len(self.df)
            self.ax.set_title(f'{self.agency_name}\n(n={total_n})', fontsize=8, fontweight='bold')
            self.ax.set_xlim(0, self.max_weeks)
            self.ax.set_ylim(0, 80)
            self.ax.set_xticks(range(0, self.max_weeks + 1, 4))
            self.ax.yaxis.set_major_formatter(mtick.PercentFormatter())
            self.ax.grid(True, alpha=0.3)
            self.ax.legend(fontsize=7, loc='lower right')

    MAX_WEEKS = 24
    MIN_CUSTOMERS = 50  # minimum per agency×product to plot
    START_MONTH = '2024-01'
    END_MONTH = '2026-03'
    OUTPUT_DIR = "pipeline_data"

    def __init__(self, df: pd.DataFrame):
        super().__init__(df)
        self.journey = self.get_journey(df)
        self.new_process = df.groupby('nom_agence').agg(
            first_new_process=('dt_creation_devis',
                               lambda x: x[df.loc[x.index, 'fg_nouveau_process_relance_devis'] == 1].min()),
        ).reset_index()

    @classmethod
    def get_journey(cls, df: pd.DataFrame) -> pd.DataFrame:
        journey_agency = super().get_journey(df)

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

    def get_agency(self, ax, agency_df, agency, new_process_adoption_month):
        return self.AgencyPlot(
            ax,
            agency_df,
            agency,
            new_process_adoption_month,
            self.MAX_WEEKS,
            self.START_MONTH,
            self.END_MONTH
        )

    def plot(self):
        for seg, product in self.MAIN_SEGMENT_LABELS.items():
            prod_df = self.journey[
                (self.journey['segment'] == seg) &
                (self.journey['cohort_month'] >= pd.Period(self.START_MONTH, 'M'))
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
                new_process_adoption_month = \
                self.new_process[self.new_process['nom_agence'] == agency]['first_new_process'].values[0]
                self.get_agency(ax, agency_df, agency, new_process_adoption_month).plot()

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
    AgencyProcessCohorts(df).plot()
