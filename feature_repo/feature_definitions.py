import os
from datetime import timedelta
from feast import Entity, Field, FeatureView, FileSource, ValueType
from feast.types import Float32, Int64, String

# Entities
card_base_id = Entity(
    name="card_base_id",
    join_keys=["card_base_id"],
    value_type=ValueType.STRING,
    description="Universal card entity identifier for rolling velocity aggregations"
)

cardholder_uid = Entity(
    name="cardholder_uid",
    join_keys=["cardholder_uid"],
    value_type=ValueType.STRING,
    description="Strict cardholder identity identifier with collision-safe null salting"
)

# Parquet file backing stores
current_dir = os.path.dirname(os.path.abspath(__file__))
card_base_parquet = os.path.abspath(os.path.join(current_dir, "..", "data", "features", "card_base_features.parquet")).replace('\\', '/')

card_base_source = FileSource(
    path=card_base_parquet,
    timestamp_field="event_timestamp",
    created_timestamp_column="created_timestamp",
)

card_velocity_fv = FeatureView(
    name="card_velocity_features",
    entities=[card_base_id],
    ttl=timedelta(days=30),
    schema=[
        Field(name="tx_count_5m", dtype=Int64),
        Field(name="tx_count_1h", dtype=Int64),
        Field(name="amt_sum_24h", dtype=Float32),
    ],
    online=True,
    source=card_base_source,
)
