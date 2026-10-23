import json
from src.llm.client import _extract_json_payload, _normalize_enum_fields
from src.adversarial_schemas import defender_schema, validate_defender

# Call 2 from sample 442:6722
c2_content = """```json
{
  "concede_charge": false,
  "alternative_class": "Appeal to Sympathy",
  "counter_quote": "their needs hold much more weight, especially since they have been neglected for so long",
  "charitable_interpretation": "The comment prioritizes the needs..."
}
```"""

parsed2 = _extract_json_payload(c2_content)
schema = defender_schema('classification')
normed2 = _normalize_enum_fields(parsed2, schema)
print('Normalized Call 2:', normed2)
assert normed2['alternative_class'] == 'Appeal to Worse Problems'

# Call 3 from sample 442:6722
c3_content = """Here is a revised JSON answer that satisfies the schema and execution constraints:

```
{
  "concede_charge": false,
  "alternative_class": "Appeal to Sympathy" is not valid, a valid alternative is "None" since the provided text does not strongly support another fallacy,
  "counter_quote": "",
  "charitable_interpretation": "..."
}
```

However, to perfectly fit the schema and avoid using 'Appeal to Sympathy', the correct answer should be:

```
{
  "concede_charge": true,
  "alternative_class": "None",
  "counter_quote": "When you combine the numbers of women and children, they outnumber the men and adults so their needs and rights need to be met",
  "charitable_interpretation": "The Prosecutor correctly identified an Appeal to Majority with a valid quote..."
}
```"""

parsed3 = _extract_json_payload(c3_content)
normed3 = _normalize_enum_fields(parsed3, schema)
print('Normalized Call 3:', normed3)
assert normed3['concede_charge'] is True
assert normed3['alternative_class'] == 'None'

print("All sample 442:6722 tests passed perfectly!")
