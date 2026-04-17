import pandas as pd
import matplotlib.pyplot as plt

from cohorts.cohorts import Cohorts


class QuotePipeline:

    OUTPUT_DIR = 'pipeline_data'

    MAIN_SEGMENTS = ['Boiler → Boiler', 'Stove → Stove', 'AC → AC', 'HP → HP']
    MAIN_SEGMENTS_COLORS = {
        'Boiler → Boiler': 'steelblue',
        'Stove → Stove':   'tomato',
        'AC → AC':         'mediumseagreen',
        'HP → HP':         'darkorange',
    }

    # Rows in descending window size — 12-month kept to let team self-retire it
    THRESHOLDS = {
        '12-month window': 365,
        '6-month window':  180,
        '90-day window':    90,
        '60-day window':    60,
    }

    # Column definitions: (title_suffix, quoter_filter)
    # None filter = combined (all quoter types)
    COLUMNS = [
        ('Single-quoter', 'Single-quoter'),
        ('Multi-quoter',  'Multi-quoter'),
        ('Combined',       None),
    ]

    def __init__(self, df_clean: pd.DataFrame, start_date='2024-03-31', end_date=None):
        self.df_quotes = df_clean.copy()
        self.df_quotes['product'] = self.df_quotes[
            'regroup_famille_equipement_produit_principal'
        ].map(Cohorts.map_product)
        self.start_date = start_date
        self.end_date   = end_date if end_date else Cohorts.LAST_DATE.strftime('%Y-%m-%d')

    # ── Pipeline builder for a single threshold ───────────────────────────────
    def _build_pipeline(self, snapshots, snap_labels, days):
        records = []
        for snap_date, snap_label in zip(snapshots, snap_labels):
            # Window filter for eligibility
            snap_quotes = self.df_quotes[
                self.df_quotes['dt_creation_devis'] <= snap_date
            ].copy()
            if days is not None:
                snap_quotes = snap_quotes[
                    snap_quotes['dt_creation_devis'] >= snap_date - pd.Timedelta(days=days)
                ]

            # Non-converted customers within the window
            converted_by_snap = snap_quotes.groupby('numero_compte')['fg_devis_accepte'].max()
            non_conv = converted_by_snap[converted_by_snap == 0].index

            # Full history to determine first→last product journey
            all_quotes_to_snap = self.df_quotes[
                (self.df_quotes['dt_creation_devis'] <= snap_date) &
                (self.df_quotes['numero_compte'].isin(non_conv))
            ]

            customer_snap = all_quotes_to_snap.groupby('numero_compte').agg(
                first_product=('product',      'first'),
                last_product =('product',      'last'),
                n_quotes     =('id_devis',     'count')
            ).reset_index()

            customer_snap['segment']     = (
                customer_snap['first_product'] + ' → ' + customer_snap['last_product']
            )
            customer_snap['quoter_type'] = customer_snap['n_quotes'].apply(
                lambda x: 'Single-quoter' if x == 1 else 'Multi-quoter'
            )
            customer_snap['snap_label']  = snap_label
            records.append(customer_snap)

        return pd.concat(records, ignore_index=True)

    # ── Aggregate pipeline counts ─────────────────────────────────────────────
    @staticmethod
    def _aggregate(pipeline, snap_labels, seg, qtype_filter):
        if qtype_filter is not None:
            filtered = pipeline[pipeline['quoter_type'] == qtype_filter]
        else:
            filtered = pipeline  # combined

        agg = (
            filtered[filtered['segment'] == seg]
            .groupby('snap_label')
            .size()
            .reset_index(name='n_customers')
        )
        return agg.set_index('snap_label').reindex(snap_labels)['n_customers']

    # ── Axis decorator ────────────────────────────────────────────────────────
    @staticmethod
    def _decorate_ax(ax, title, snap_labels, partial_idx):
        ax.set_title(title, fontweight='bold', fontsize=10)
        ax.set_ylabel('Customers in pipeline')
        ax.set_xlabel('Quarter end')
        ax.tick_params(axis='x', rotation=30)
        ax.legend(fontsize=8)
        ax.grid(True, axis='y', alpha=0.3)
        ymax = ax.get_ylim()[1]
        ax.axvspan(partial_idx - 0.5, partial_idx + 0.5, alpha=0.08, color='orange')
        ax.text(partial_idx - 0.4, ymax * 0.97, '⚠ partial',
                fontsize=7.5, color='darkorange', va='top')

    # ── Main plot ─────────────────────────────────────────────────────────────
    def plot(self):
        snapshots   = pd.date_range(self.start_date, self.end_date, freq='QE')
        snap_labels = [
            d.strftime('%Y Q') + str((d.month - 1) // 3 + 1)
            for d in snapshots
        ]
        partial_idx = len(snap_labels) - 1

        print("Snapshot dates:", [s.strftime('%Y-%m-%d') for s in snapshots])

        n_rows = len(self.THRESHOLDS)
        n_cols = len(self.COLUMNS)

        fig, axes = plt.subplots(
            n_rows, n_cols,
            figsize=(7 * n_cols, 5 * n_rows)
        )
        fig.suptitle(
            'Quote Pipeline Backlog — Threshold Comparison\n(Diagonal segments only)',
            fontsize=14, fontweight='bold'
        )

        for row, (thresh_label, days) in enumerate(self.THRESHOLDS.items()):

            # Build pipeline once per threshold — reuse across columns
            pipeline = self._build_pipeline(snapshots, snap_labels, days)

            for col, (col_suffix, qtype_filter) in enumerate(self.COLUMNS):
                ax = axes[row, col]

                for seg in self.MAIN_SEGMENTS:
                    values = self._aggregate(pipeline, snap_labels, seg, qtype_filter)
                    if values.isna().all():
                        continue
                    ax.plot(
                        snap_labels, values.values,
                        marker='o', linewidth=2.2, markersize=6,
                        color=self.MAIN_SEGMENTS_COLORS.get(seg, 'black'),
                        label=seg
                    )

                self._decorate_ax(
                    ax,
                    title=f'{thresh_label} — {col_suffix}',
                    snap_labels=snap_labels,
                    partial_idx=partial_idx
                )

        plt.tight_layout()
        plt.savefig(
            f'{self.OUTPUT_DIR}/pipeline_threshold_comparison.png',
            dpi=150, bbox_inches='tight'
        )
        plt.show()


def plot_quote_pipeline(df_clean, start_date='2024-03-31', end_date=None):
    QuotePipeline(df_clean, start_date, end_date).plot()