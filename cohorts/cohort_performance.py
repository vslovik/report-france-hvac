import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import pandas as pd

from cohorts.year import YearCohorts
from util.quarter import last_n_quarters_label


class WeeklyCohorts(YearCohorts):
    def __init__(self, df: pd.DataFrame):
        self.journey = self.get_journey(df)
        self.switchers = self.get_switchers(self.journey)
        self.quarters_to_plot = last_n_quarters_label(self.QUARTERS_TO_SHOW, self.LAST_DATE)
        self.quarters_colors = dict(zip(self.quarters_to_plot, self.QUARTERS_COLORS))

    # Helper: assign week-within-quarter
    @classmethod
    def week_in_quarter(cls, date_series):
        quarter_start = date_series.dt.to_period('Q').dt.start_time
        return ((date_series - quarter_start) / pd.Timedelta(weeks=1)).astype(int) + 1

    @classmethod
    def get_switchers(cls, journey: pd.DataFrame) -> pd.DataFrame:
        switchers = journey[journey['first_product'] != journey['last_product']].copy()

        switcher_counts = switchers['segment'].value_counts()
        meaningful = switcher_counts[switcher_counts > 50].index.tolist()

        # Build weekly cohorts per switcher segment
        switchers['cohort_week'] = switchers['first_quote_date'].dt.to_period('W').dt.start_time
        switchers['cohort_month'] = switchers['first_quote_date'].dt.to_period('M').dt.start_time
        switchers['week_in_q'] = cls.week_in_quarter(switchers['first_quote_date'])
        switchers['quarter_label'] = (
            switchers['first_quote_date'].dt.year.astype(str)
            + ' Q' + switchers['first_quote_date'].dt.quarter.astype(str)
        )

        return switchers[switchers['segment'].isin(meaningful)].copy()

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

        cohort_seg = cohort_seg.sort_values(['segment', 'cohort_week'])
        cohort_seg['conv_roll4'] = (
            cohort_seg.groupby('segment')['conversion_rate']
            .transform(lambda x: x.rolling(4, center=True, min_periods=2).mean())
        )
        cohort_seg['days_roll4'] = (
            cohort_seg.groupby('segment')['avg_decision_days']
            .transform(lambda x: x.rolling(4, center=True, min_periods=2).mean())
        )

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
                ax.scatter(complete['cohort_week'], complete[metric], s=12, alpha=0.3, color=color)
                ax.plot(complete['cohort_week'], complete[roll], color=color, linewidth=2, label=label)
                ax.plot(incompl['cohort_week'], incompl[roll],
                        color=color, linewidth=1.5, linestyle='--', alpha=0.6)

        axes[0].set_title('Conversion Rate (4-week rolling avg)', fontsize=11, loc='left')
        axes[0].set_ylabel('Conversion Rate')
        axes[0].yaxis.set_major_formatter(mtick.PercentFormatter())
        axes[0].legend(fontsize=9)
        axes[0].grid(True, axis='y', alpha=0.3)
        axes[0].tick_params(labelbottom=False)

        axes[1].set_title('Avg Decision Days (4-week rolling avg)', fontsize=11, loc='left')
        axes[1].set_ylabel('Days to Convert')
        axes[1].legend(fontsize=9)
        axes[1].grid(True, axis='y', alpha=0.3)
        axes[1].tick_params(axis='x', rotation=30)

        for ax in axes:
            ax.axvspan(cutoff, self.journey['cohort_week'].max(), alpha=0.07, color='orange')
            ax.text(cutoff, ax.get_ylim()[1] * 0.97, '  ⚠ incomplete',
                    fontsize=7.5, color='darkorange', va='top')

        plt.tight_layout()
        plt.savefig(f'{self.OUTPUT_DIR}/cohort_curves_by_segment.png', dpi=150, bbox_inches='tight')
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

        cohort_sw_m = cohort_sw_m.sort_values(['segment', 'cohort_month'])
        cohort_sw_m['conv_roll3'] = (
            cohort_sw_m.groupby('segment')['conversion_rate']
            .transform(lambda x: x.rolling(3, center=True, min_periods=2).mean())
        )
        cohort_sw_m['days_roll3'] = (
            cohort_sw_m.groupby('segment')['avg_decision_days']
            .transform(lambda x: x.rolling(3, center=True, min_periods=2).mean())
        )

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
                ax.scatter(complete['cohort_month'], complete[metric], s=25, alpha=0.35, color=color)
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
            ax.axvspan(cutoff_m, self.switchers['cohort_month'].max(), alpha=0.07, color='orange')
            ax.text(cutoff_m, ax.get_ylim()[1] * 0.97, '  ⚠ incomplete',
                    fontsize=7.5, color='darkorange', va='top')

        plt.tight_layout()
        plt.savefig(f'{self.OUTPUT_DIR}/cohort_curves_top_switchers.png', dpi=150, bbox_inches='tight')
        plt.show()

    def plot_quarters_report(self):
        for d in [self.journey, self.switchers]:
            d['quarter_label'] = (
                d['first_quote_date'].dt.year.astype(str)
                + ' Q' + d['first_quote_date'].dt.quarter.astype(str)
            )

        diag_q = (
            self.journey[
                self.journey['segment'].isin(self.MAIN_SEGMENTS)
                & self.journey['quarter_label'].isin(self.quarters_to_plot)
            ]
            .groupby(['segment', 'quarter_label'])
            .agg(total=('numero_compte', 'count'),
                 converted=('converted', 'sum'),
                 avg_decision_days=('decision_days', 'mean'))
            .reset_index()
        )
        diag_q['conversion_rate'] = diag_q['converted'] / diag_q['total'] * 100

        sw_q = (
            self.switchers[
                self.switchers['segment'].isin(self.TOP_SWITCHERS)
                & self.switchers['quarter_label'].isin(self.quarters_to_plot)
            ]
            .groupby(['segment', 'quarter_label'])
            .agg(total=('numero_compte', 'count'),
                 converted=('converted', 'sum'),
                 avg_decision_days=('decision_days', 'mean'))
            .reset_index()
        )
        sw_q['conversion_rate'] = sw_q['converted'] / sw_q['total'] * 100

        fig, axes = plt.subplots(2, 2, figsize=(18, 11))
        fig.suptitle('Quarterly Comparison: 2025 Q1–Q4 vs 2026 Q1', fontsize=14, fontweight='bold')

        partial_q = self.quarters_to_plot[-1]
        partial_idx = len(self.quarters_to_plot) - 1

        def plot_quarterly(ax, data, segments, colors, labels, metric, ylabel, title):
            ax.axvspan(partial_idx - 0.5, partial_idx + 0.5, alpha=0.08, color='orange')
            for seg in segments:
                d = data[data['segment'] == seg].set_index('quarter_label').reindex(self.quarters_to_plot)
                color = colors[seg]
                label = labels[seg]
                ax.plot(self.quarters_to_plot, d[metric].values, marker='o', linewidth=2.2,
                        markersize=7, color=color, label=label)
                val = d[metric].iloc[-1]
                if not pd.isna(val):
                    fmt = f'{val:.0f}%' if 'rate' in metric else f'{val:.0f}d'
                    ax.annotate(fmt, xy=(partial_idx, val), xytext=(partial_idx + 0.05, val),
                                fontsize=7.5, color=color, va='center')
            ax.set_title(title, fontsize=10, fontweight='bold', loc='left')
            ax.set_ylabel(ylabel)
            if 'rate' in metric:
                ax.yaxis.set_major_formatter(mtick.PercentFormatter())
            ax.tick_params(axis='x', rotation=30)
            ax.legend(fontsize=8)
            ax.grid(True, axis='y', alpha=0.3)
            ax.text(partial_idx - 0.3, ax.get_ylim()[1] * 0.97, '⚠ partial',
                    fontsize=7.5, color='darkorange', va='top')

        plot_quarterly(axes[0, 0], diag_q, self.MAIN_SEGMENTS, self.MAIN_SEGMENT_COLORS,
                       self.MAIN_SEGMENT_LABELS, 'conversion_rate', 'Conversion Rate',
                       'Diagonal — Conversion Rate')
        plot_quarterly(axes[1, 0], diag_q, self.MAIN_SEGMENTS, self.MAIN_SEGMENT_COLORS,
                       self.MAIN_SEGMENT_LABELS, 'avg_decision_days', 'Avg Decision Days',
                       'Diagonal — Decision Days')
        plot_quarterly(axes[0, 1], sw_q, self.TOP_SWITCHERS, self.TOP_SWITCHER_COLORS,
                       {s: s.replace('_', ' ') for s in self.TOP_SWITCHERS},
                       'conversion_rate', 'Conversion Rate', 'Switchers — Conversion Rate')
        plot_quarterly(axes[1, 1], sw_q, self.TOP_SWITCHERS, self.TOP_SWITCHER_COLORS,
                       {s: s.replace('_', ' ') for s in self.TOP_SWITCHERS},
                       'avg_decision_days', 'Avg Decision Days', 'Switchers — Decision Days')

        plt.tight_layout()
        plt.savefig(f'{self.OUTPUT_DIR}/quarterly_comparison.png', dpi=150, bbox_inches='tight')
        plt.show()

    def build_intra_cohorts(self, df, segments, freq):
        """Build weekly (stayers) or bi-weekly (switchers) within-quarter cohorts."""
        filtered = df[df['segment'].isin(segments) & df['quarter_label'].isin(self.quarters_to_plot)]
        if freq == 'M':
            filtered = filtered.copy()
            filtered['week_in_q'] = ((filtered['week_in_q'] - 1) // 2) + 1

        return (
            filtered
            .groupby(['segment', 'quarter_label', 'week_in_q'])
            .agg(total=('numero_compte', 'count'), converted=('converted', 'sum'))
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
                y = qd['conversion_rate'].rolling(2, min_periods=1).mean()
                ls = '--' if q == self.quarters_to_plot[-1] else '-'
                ax.plot(qd['week_in_q'], y, marker='o', linewidth=2,
                        markersize=5, color=self.quarters_colors[q], linestyle=ls, label=q)

            ax.set_title(label, fontweight='bold', fontsize=10)
            ax.set_xlabel(f'{freq_label} within quarter')
            ax.set_ylabel('Conversion Rate')
            ax.yaxis.set_major_formatter(mtick.PercentFormatter())
            ax.legend(fontsize=8)
            ax.grid(True, axis='y', alpha=0.3)

        for j in range(i + 1, len(axes)):
            axes[j].set_visible(False)

        plt.tight_layout()
        return fig

    def plot_intra_quarters(self):
        diag_intra = self.build_intra_cohorts(self.journey, self.MAIN_SEGMENTS, freq='W')
        sw_intra = self.build_intra_cohorts(self.switchers, self.TOP_SWITCHERS, freq='M')

        fig1 = self.plot_intra_quarter(
            diag_intra, self.MAIN_SEGMENTS, self.MAIN_SEGMENT_LABELS,
            title_prefix='Stayers', freq_label='Week'
        )
        fig1.savefig(f'{self.OUTPUT_DIR}/intra_quarter_stayers.png', dpi=150, bbox_inches='tight')

        fig2 = self.plot_intra_quarter(
            sw_intra, self.TOP_SWITCHERS,
            {s: s.replace('_', ' ') for s in self.TOP_SWITCHERS},
            title_prefix='Switchers', freq_label='Bi-week'
        )
        fig2.savefig(f'{self.OUTPUT_DIR}/intra_quarter_switchers.png', dpi=150, bbox_inches='tight')
        plt.show()

    def plot_quarter_x_product(self, data, segments, labels, colors, title_prefix, freq_label, ncols=3):
        nrows = len(self.quarters_to_plot) // ncols + len(self.quarters_to_plot) % ncols - 1
        fig, axes = plt.subplots(nrows, ncols, figsize=(18, 4 * nrows), sharey=False)
        fig.suptitle(f'{title_prefix} — Conversion Rate by Product Within Quarter',
                     fontsize=13, fontweight='bold')
        axes = axes.flatten()

        for i, q in enumerate(self.quarters_to_plot):
            ax = axes[i]
            ls = '--' if q == self.quarters_to_plot[-1] else '-'

            for seg in segments:
                d = data[(data['segment'] == seg) & (data['quarter_label'] == q)].sort_values('week_in_q')
                if d.empty:
                    continue
                y = d['conversion_rate'].rolling(2, min_periods=1).mean()
                ax.plot(d['week_in_q'], y, marker='o', linewidth=2,
                        markersize=5, color=colors[seg], linestyle=ls,
                        label=labels[seg])

            partial_suffix = '  ⚠ partial' if q == self.quarters_to_plot[-1] else ''
            ax.set_title(f'{q}{partial_suffix}', fontweight='bold', fontsize=10)
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

        fig1 = self.plot_quarter_x_product(
            diag_intra, self.MAIN_SEGMENTS, self.MAIN_SEGMENT_LABELS, self.MAIN_SEGMENT_COLORS,
            title_prefix='Stayers', freq_label='Week'
        )
        fig1.savefig(f'{self.OUTPUT_DIR}/quarter_x_product_stayers.png', dpi=150, bbox_inches='tight')

        fig2 = self.plot_quarter_x_product(
            sw_intra, self.TOP_SWITCHERS,
            {s: s.replace('_', ' ') for s in self.TOP_SWITCHERS},
            self.TOP_SWITCHER_COLORS,
            title_prefix='Switchers', freq_label='Bi-week'
        )
        fig2.savefig(f'{self.OUTPUT_DIR}/quarter_x_product_switchers.png', dpi=150, bbox_inches='tight')
        plt.show()
