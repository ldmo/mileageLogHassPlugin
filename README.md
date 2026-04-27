# Traxmiles Home Assistant Integration

Custom integration that reads your Traxmiles dashboard and lets you lock/submit the current month with a closing odometer reading.

## Dashboard Card (paste-and-go)

This is a stock Lovelace card — no custom card plugin required. Paste it into a dashboard via *Edit dashboard -> Add Card -> Manual*.

```yaml
type: vertical-stack
cards:
  - type: glance
    title: Traxmiles
    columns: 4
    entities:
      - entity: sensor.traxmiles_plugin_current_vehicle
        name: Vehicle
      - entity: sensor.traxmiles_plugin_open_record_month
        name: Month
      - entity: sensor.traxmiles_plugin_business_miles_this_month
        name: This Month
      - entity: sensor.traxmiles_plugin_business_miles_tax_year
        name: Tax Year
      - entity: sensor.traxmiles_plugin_opening_odometer
        name: Opening
      - entity: binary_sensor.traxmiles_plugin_record_locked
        name: Locked

  - type: entities
    title: Lock & Submit Month
    state_color: true
    entities:
      - entity: number.traxmiles_plugin_closing_odometer
        name: Closing odometer (mi)
        secondary_info: last-changed
      - entity: switch.traxmiles_plugin_auto_submit_allowed
        name: Allow auto-submit
      - type: button
        name: Lock & Submit
        icon: mdi:lock-check
        tap_action:
          action: call-service
          service: button.press
          target:
            entity_id: button.traxmiles_plugin_lock_and_submit
```

If a sensor entity ID is different on your install (HA may suffix duplicates with `_2` etc.), edit each `entity:` value using HA’s entity picker in the card editor.

## Submit Service

Service: `traxmiles.lock_and_submit`

Fields:
- `closing_odometer` (required): closing odometer in miles
- `source` (optional): `manual` or `automation` (default `automation`)
- `entry_id` (optional): required only if multiple Traxmiles accounts are configured

## Auto-submit gating

When calling the service from an automation (`source: automation`), the integration requires `switch.auto_submit_allowed` to be **on**, otherwise the call is rejected. Pressing the button entity always uses `source: manual` and bypasses the gate.
