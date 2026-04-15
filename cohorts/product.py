from datetime import date
import pandas as pd
from util.quarter import last_n_quarters_label, week_in_quarter


class ProductCohorts:
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
        self.quarters_to_plot = last_n_quarters_label(self.QUARTERS_TO_SHOW, date(2026, 3, 31))
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
        #
        # # ToDo
        # journey['product'] = journey['first_product'].map({
        #     'BOILER_GAS': 'Boiler',
        #     'STOVE': 'Stove',
        #     'AIR_CONDITIONER': 'AC',
        #     'HEAT_PUMP': 'Heat Pump'
        # })

        # Summary
        print(journey['segment'].value_counts())
        print(f"\nTotal customers: {len(journey):,}")
        print(f"Multi-product journeys: {(journey['first_product'] != journey['last_product']).sum():,}")

        return journey
    #
    # @classmethod
    # def get_journey_agency(cls, df: pd.DataFrame) -> pd.DataFrame:
    #     # Add agency to journey from raw quotes
    #     agency_per_customer = (
    #         df.sort_values('dt_creation_devis')
    #         .groupby('numero_compte')['nom_agence']
    #         .first()
    #         .reset_index()
    #         .rename(columns={'nom_agence': 'main_agency'})
    #     )
    #     journey = cls.get_journey(df)
    #     journey_agency = journey.merge(agency_per_customer, on='numero_compte', how='left')
    #     journey_agency['cohort_month'] = journey_agency['first_quote_date'].dt.to_period('M')
    #     journey_agency['conv_week'] = np.where(
    #         journey_agency['decision_days'] == 0, 0,
    #         np.ceil(journey_agency['decision_days'] / 7).astype(int)
    #     )
    #
    #     return journey_agency
    #
    # @classmethod
    # def get_journey_agency_process(cls, df: pd.DataFrame) -> pd.DataFrame:
    #     journey_agency = cls.get_journey_agency(df)
    #
    #     # Add process flag to journey_agency
    #     # Get dominant process flag per customer (max = if any quote was new process)
    #     process_per_customer = (
    #         df.groupby('numero_compte')['fg_nouveau_process_relance_devis']
    #         .max()
    #         .reset_index()
    #         .rename(columns={'fg_nouveau_process_relance_devis': 'new_process'})
    #     )
    #     journey_agency_process = journey_agency.merge(process_per_customer, on='numero_compte', how='left')
    #
    #     return journey_agency_process
