"""
verify_sensors.py - Complete verification of all 108 assets and their sensors.

Run this after creating all sensors to confirm:
- Every asset has the expected number of sensors
- Each sensor produces a valid reading
- Sensor IDs follow the naming convention
- No errors occur during reading generation
"""

import sys
from datetime import datetime

# Import city and sensor modules
from simulator.city.assets import ASSETS, AssetType
from simulator.sensors.pressure import create_pressure_sensors
from simulator.sensors.flow import create_flow_sensors
from simulator.sensors.equipment import create_equipment_sensors
from simulator.sensors.water_quality import create_water_quality_sensors


# ----------------------------------------------------------------------
# Expected sensor counts per asset type
# ----------------------------------------------------------------------
EXPECTED_SENSOR_COUNTS = {
    AssetType.TREATMENT_FACILITY: 4,   # Flow (from flow.py), pH, Turbidity, Water Temp (from water_quality.py)
    AssetType.RESERVOIR: 4,            # Level, Water Temp, pH, Turbidity (all from water_quality.py)
    AssetType.PUMP_STATION: 6,         # Pressure, Flow, Temp, Vibration, Power, Status
    AssetType.PIPELINE: 2,             # Pressure, Flow
    AssetType.VALVE: 3,                # Pressure, Flow, Position
}

# Expected sensor ID suffixes for each asset type
EXPECTED_SUFFIXES = {
    AssetType.TREATMENT_FACILITY: ["-FLOW", "-PH", "-TURBIDITY", "-WATER-TEMP"],
    AssetType.RESERVOIR: ["-LEVEL", "-WATER-TEMP", "-PH", "-TURBIDITY"],
    AssetType.PUMP_STATION: ["-PRESSURE", "-FLOW", "-TEMPERATURE", "-VIBRATION", "-POWER", "-EQUIPMENT-STATUS"],
    AssetType.PIPELINE: ["-PRESSURE", "-FLOW"],
    AssetType.VALVE: ["-PRESSURE", "-FLOW", "-POSITION"],
}


def create_all_sensors():
    """Call all create_*_sensors functions to attach sensors to assets."""
    print("Creating pressure sensors...")
    pressure_sensors = create_pressure_sensors()
    print(f"  Created {len(pressure_sensors)} pressure sensors")

    print("Creating flow sensors...")
    flow_sensors = create_flow_sensors()
    print(f"  Created {len(flow_sensors)} flow sensors")

    print("Creating equipment sensors...")
    equipment_sensors = create_equipment_sensors()
    print(f"  Created {len(equipment_sensors)} equipment sensors")

    print("Creating water quality sensors...")
    water_quality_sensors = create_water_quality_sensors()
    print(f"  Created {len(water_quality_sensors)} water quality sensors")

    total = len(pressure_sensors) + len(flow_sensors) + len(equipment_sensors) + len(water_quality_sensors)
    print(f"\nTotal sensors created: {total}")
    return total


def verify_asset_sensors():
    """Check each asset for correct sensor count and IDs."""
    print("\n" + "=" * 80)
    print("VERIFYING SENSOR ATTACHMENTS")
    print("=" * 80)

    all_ok = True
    asset_count = len(ASSETS)
    print(f"Total assets: {asset_count}\n")

    for asset_id, asset in ASSETS.items():
        try:
            asset_type = AssetType(asset.asset_type)
        except ValueError:
            print(f"❌ {asset_id}: Unknown asset type '{asset.asset_type}'")
            all_ok = False
            continue

        expected_count = EXPECTED_SENSOR_COUNTS.get(asset_type, 0)
        actual_count = len(asset.sensors)

        if actual_count != expected_count:
            print(f"❌ {asset_id} ({asset_type}): Expected {expected_count} sensors, got {actual_count}")
            all_ok = False
        else:
            # Check sensor ID suffixes
            sensor_ids = [s.sensor_id for s in asset.sensors]
            expected_suffixes = EXPECTED_SUFFIXES.get(asset_type, [])
            found_suffixes = []
            for sid in sensor_ids:
                # extract suffix after asset_id
                if sid.startswith(asset_id):
                    suffix = sid[len(asset_id):]
                    found_suffixes.append(suffix)
                else:
                    print(f"⚠️ {asset_id}: Sensor ID '{sid}' does not start with asset ID")
                    all_ok = False

            # Check that all expected suffixes are present
            missing = [suf for suf in expected_suffixes if suf not in found_suffixes]
            extra = [suf for suf in found_suffixes if suf not in expected_suffixes]
            if missing:
                print(f"❌ {asset_id}: Missing sensors: {missing}")
                all_ok = False
            if extra:
                print(f"⚠️ {asset_id}: Extra sensors: {extra}")
                # Not necessarily an error, but we note it

            # If everything is correct, print a success message (only for non-verbose)
            if not missing and not extra and actual_count == expected_count:
                # We'll skip printing every asset to keep output clean; we'll count successes later.
                pass

    if all_ok:
        print("\n✅ All assets have the expected sensors attached.")
    else:
        print("\n❌ Some assets have incorrect sensor attachments. Fix the issues above.")

    return all_ok


def verify_readings():
    """Generate a reading from every sensor and check for valid data."""
    print("\n" + "=" * 80)
    print("VERIFYING SENSOR READINGS")
    print("=" * 80)

    all_ok = True
    total_sensors = sum(len(asset.sensors) for asset in ASSETS.values())
    print(f"Total sensors: {total_sensors}\n")

    failures = 0
    success_count = 0

    for asset_id, asset in ASSETS.items():
        for sensor in asset.sensors:
            try:
                reading = sensor.read()
                # Basic validation
                required_fields = ["sensor_id", "asset_id", "parameter", "value", "unit", "timestamp"]
                for field in required_fields:
                    if field not in reading:
                        print(f"❌ {sensor.sensor_id}: Missing field '{field}'")
                        all_ok = False
                        failures += 1
                        break
                else:
                    # Check timestamp format (ISO)
                    try:
                        datetime.fromisoformat(reading["timestamp"])
                    except ValueError:
                        print(f"❌ {sensor.sensor_id}: Invalid timestamp format '{reading['timestamp']}'")
                        all_ok = False
                        failures += 1
                        continue

                    # Check that value is not None
                    if reading["value"] is None:
                        print(f"❌ {sensor.sensor_id}: Value is None")
                        all_ok = False
                        failures += 1
                        continue

                    success_count += 1

            except Exception as e:
                print(f"❌ {sensor.sensor_id}: Exception during read: {e}")
                all_ok = False
                failures += 1

    print(f"\nReadings generated successfully: {success_count}/{total_sensors}")
    if failures:
        print(f"❌ {failures} sensors failed to produce valid readings.")
    else:
        print("✅ All sensors produced valid readings.")

    return all_ok


def main():
    print("=" * 80)
    print("AquaShield AI - Complete Sensor Verification")
    print("=" * 80)

    # Step 1: Create all sensors (attach to assets)
    create_all_sensors()

    # Step 2: Verify attachments
    attachments_ok = verify_asset_sensors()

    # Step 3: Verify readings
    readings_ok = verify_readings()

    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)

    if attachments_ok and readings_ok:
        print("\n✅ PASS: All sensors are correctly attached and producing valid readings.")
        print("   Virtual sensor layer is fully operational.")
    else:
        print("\n❌ FAIL: Some issues were detected. Please review the output above.")
        sys.exit(1)

    # Optional: Display some statistics
    print("\nSensor counts by type:")
    from collections import Counter
    type_counter = Counter()
    for asset in ASSETS.values():
        for sensor in asset.sensors:
            type_counter[sensor.__class__.__name__] += 1
    for class_name, count in sorted(type_counter.items()):
        print(f"  {class_name}: {count}")

    print("\nVerification complete at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


if __name__ == "__main__":
    main()