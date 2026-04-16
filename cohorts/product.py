import numpy as np
import pandas as pd

from cohorts.year import YearCohorts
from util.quarter import week_in_quarter

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick


class ProductCohorts(YearCohorts):
    def __init__(self, df: pd.DataFrame, max_weeks=24, start_month='2024-01', end_month='2026-03'):
        super().__init__(df, max_weeks, start_month, end_month)

    def plot(self):

        cutoff_month = pd.Period('2025-12', 'M')

        # Build curves per segment × cohort month
        segments_to_plot = self.MAIN_SEGMENTS + self.TOP_SWITCHERS

        cohorts_seg = self.journey[
            (self.journey['cohort_month'] >= pd.Period(self.start_month, 'M')) &
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
            for w in range(self.max_weeks + 1):
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

        # One figure per segment, 3 year panels
        for seg in segments_to_plot:
            fig, axes = plt.subplots(3, 1, figsize=(16, 15), sharey=True)
            fig.suptitle(f'Cohort Conversion Curves — {self.SEGMENT_LABELS[seg]}',
                         fontsize=13, fontweight='bold')

            for ax, year in zip(axes, self.YEARS):
                year_months = [m for m in all_months if m.year == year]
                cmap_year = plt.cm.get_cmap('turbo', max(len(year_months), 1))

                for i, month in enumerate(year_months):
                    d = curves_seg_df[
                        (curves_seg_df['cohort'] == str(month)) &
                        (curves_seg_df['segment'] == seg)
                        ]
                    if d.empty:
                        continue
                    months_since = (pd.Period(self.end_month, 'M') - month).n
                    max_w = min(self.max_weeks, months_since * 4)
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
                ax.set_xlim(0, self.max_weeks)
                ax.set_ylim(0, 100)
                ax.set_xticks(range(0, self.max_weeks + 1, 2))
                ax.grid(True, alpha=0.3)
                ax.legend(fontsize=8, ncol=len(year_months), loc='lower right')

            axes[-1].set_xlabel('Weeks from first quote', fontsize=10)
            plt.tight_layout()
            fname = seg.lower().replace(' ', '_').replace('→', 'to').replace('__', '_')
            plt.savefig(f'{self.OUTPUT_DIR}/monthly_cohort_curves_{fname}_strict.png', dpi=150, bbox_inches='tight')
            plt.show()

        for seg, label in self.MAIN_SEGMENT_LABELS.items():
            fig, axes = plt.subplots(3, 1, figsize=(16, 15), sharey=True)
            fig.suptitle(f'Cohort Conversion Curves — {label} (strict: {seg})',
                         fontsize=13, fontweight='bold')

            for ax, year in zip(axes, self.YEARS):
                year_months = [m for m in all_months if m.year == year]
                cmap_year = plt.cm.get_cmap('turbo', max(len(year_months), 1))

                for i, month in enumerate(year_months):
                    d = curves_seg_df[
                        (curves_seg_df['cohort'] == str(month)) &
                        (curves_seg_df['segment'] == seg)
                        ]
                    if d.empty:
                        continue
                    months_since = (pd.Period(self.end_month, 'M') - month).n
                    max_w = min(self.max_weeks, months_since * 4)
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
                ax.set_xlim(0, self.max_weeks)
                ax.set_ylim(0, 80)
                ax.set_xticks(range(0, self.max_weeks + 1, 2))
                ax.grid(True, alpha=0.3)
                ax.legend(fontsize=8, ncol=len(year_months), loc='lower right')

            axes[-1].set_xlabel('Weeks from first quote', fontsize=10)
            plt.tight_layout()
            fname = label.lower().replace(' ', '_')
            plt.savefig(f'{self.OUTPUT_DIR}/monthly_cohort_curves_{fname}_strict.png', dpi=150, bbox_inches='tight')
            plt.show()

        fig, axes = plt.subplots(3, 4, figsize=(24, 15), sharey=True, sharex=True)
        fig.suptitle('Cohort Conversion Curves — All Products × All Years (strict: first = last product)',
                     fontsize=14, fontweight='bold')

        for col, (seg, label) in enumerate(self.MAIN_SEGMENT_LABELS.items()):
            for row, year in enumerate(self.YEARS):
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
                    max_w = min(self.max_weeks, months_since * 4)
                    d = d[d['week'] <= max_w]
                    ls = '--' if month > cutoff_month else '-'
                    alpha = 0.6 if month > cutoff_month else 0.9
                    color = cmap_year(i / max(len(year_months) - 1, 1))

                    ax.plot(d['week'], d['cumulative_pct'],
                            color=color, linewidth=1.5, linestyle=ls, alpha=alpha)

                if row == 0:
                    ax.set_title(label, fontweight='bold', fontsize=11,
                                 color=list(self.MAIN_SEGMENT_COLORS.values())[col])
                if col == 0:
                    ax.set_ylabel(f'{year}\nCumulative % converted', fontsize=9)

                ax.yaxis.set_major_formatter(mtick.PercentFormatter())
                ax.set_xlim(0, self.max_weeks)
                ax.set_ylim(0, 80)
                ax.set_xticks(range(0, self.max_weeks + 1, 4))
                ax.grid(True, alpha=0.3)

        for col in range(4):
            axes[-1, col].set_xlabel('Weeks from first quote', fontsize=9)

        plt.tight_layout()
        plt.savefig(f'{self.OUTPUT_DIR}/cohort_curves_grid_strict.png', dpi=150, bbox_inches='tight')
        plt.show()


def plot_product_cohorts(df: pd.DataFrame) -> None:
    ProductCohorts(df).plot()