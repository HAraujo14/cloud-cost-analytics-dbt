select source_line_id
from {{ ref('int_cost_lines') }}
where
    not is_synthetic
    or dataset_label <> '{{ var("dataset_label", "synthetic-finops-portfolio") }}'
