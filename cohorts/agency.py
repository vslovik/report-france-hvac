import numpy as np
import pandas as pd
from cohorts.product import ProductCohorts


class AgencyCohorts(ProductCohorts):
    def __init__(self, df: pd.DataFrame):
        super().__init__(df)
        self.journey = self.get_journey(df)

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
