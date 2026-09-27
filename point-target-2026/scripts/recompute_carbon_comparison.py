"""Reproduce the carbon densities and equivalent volume increment in the manuscript.

The area is inferred from rounded values in the original Canyon i-Tree report;
it is not a measured polygon area. This script does not rerun i-Tree Canopy or
estimate uncertainty in its ecosystem-service coefficients.

Run: python scripts/recompute_carbon_comparison.py
"""

from __future__ import annotations


# Canyon i-Tree report: totals and areal coefficient for Tree/Shrub cover.
CARBON_STORAGE_T_C = 10_422.69
ANNUAL_SEQUESTRATION_T_C = 257.69
SEQUESTRATION_COEFFICIENT_T_C_PER_KM2_PER_YEAR = 190.000

# Güner and Çömez (2017), afforested Pinus nigra stands. The factors turn
# equivalent stem volume into above- and below-ground carbon mass.
WOOD_DENSITY_T_PER_M3 = 0.408
ABOVEGROUND_BIOMASS_EXPANSION = 1.516
ROOT_TO_SHOOT_RATIO = 0.179
CARBON_FRACTION = 0.5386


def main() -> None:
    tree_area_km2 = (
        ANNUAL_SEQUESTRATION_T_C
        / SEQUESTRATION_COEFFICIENT_T_C_PER_KM2_PER_YEAR
    )
    tree_area_ha = 100.0 * tree_area_km2
    storage_per_ha = CARBON_STORAGE_T_C / tree_area_ha
    sequestration_per_ha = ANNUAL_SEQUESTRATION_T_C / tree_area_ha
    carbon_per_stem_volume = (
        WOOD_DENSITY_T_PER_M3
        * ABOVEGROUND_BIOMASS_EXPANSION
        * (1.0 + ROOT_TO_SHOOT_RATIO)
        * CARBON_FRACTION
    )
    equivalent_volume_increment = sequestration_per_ha / carbon_per_stem_volume

    print(f"Implied Tree/Shrub area: {tree_area_ha:.3f} ha")
    print(f"Carbon storage density: {storage_per_ha:.3f} t C ha^-1")
    print(f"Annual sequestration density: {sequestration_per_ha:.3f} t C ha^-1 yr^-1")
    print(
        "Equivalent stem-volume increment: "
        f"{equivalent_volume_increment:.3f} m^3 ha^-1 yr^-1"
    )


if __name__ == "__main__":
    main()
