# Traxmiles Home Assistant Integration

Custom integration that reads your Traxmiles dashboard and lets you lock/submit the current month with a closing odometer reading.

## Dashboard Card

Add this stock Lovelace entities card:

```yaml
type: entities
title: Traxmiles
entities:
  - entity: sensor.traxmiles_business_miles_this_month
  - entity: sensor.traxmiles_current_vehicle
  - entity: number.traxmiles_closing_odometer
    secondary_info: last-changed
  - entity: button.traxmiles_lock_and_submit
  - entity: switch.traxmiles_auto_submit_allowed
```

## Submit Service

Service: `traxmiles.lock_and_submit`

Fields:
- `closing_odometer` (required): closing odometer in miles
- `source` (optional): `manual` or `automation` (default `automation`)
- `entry_id` (optional): required only if multiple Traxmiles accounts are configured
